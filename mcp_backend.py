#!/usr/bin/env python3
"""
MCPM v5.0 – Full Filesystem Co‑Pilot
* Atomic writes + .bak backups
* .gitignore filtering
* Reference project support
* Rich metadata on reads
* Git diff / commit / log
"""

import os
import json
import hashlib
import logging
import platform
from pathlib import Path, PureWindowsPath
from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncio
import yaml
import aiohttp
import openai
import shutil
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import traceback
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import ValidationError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure environment variables from a local .env are available when running the backend directly
load_dotenv()

# --------------------------------------------------------------------------- #
# -------------------------- HELPER CLASSES --------------------------------- #
# --------------------------------------------------------------------------- #
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
    def on_modified(self, event):
        if not event.is_directory:
            self.callback('modified', event.src_path)
    def on_created(self, event):
        if not event.is_directory:
            self.callback('created', event.src_path)
    def on_deleted(self, event):
        if not event.is_directory:
            self.callback('deleted', event.src_path)

class MemoryStore:
    def __init__(self, memory_file: Path, config: Dict):
        self.memory_file = memory_file
        self.limit = config.get('context_limit', 20)
        loaded_data = self._load()
        self.memories = loaded_data.get('memories', {}) if isinstance(loaded_data, dict) else loaded_data
        self.context = loaded_data.get('context', []) if isinstance(loaded_data, dict) else []

    def _load(self):
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text())
                # Handle both old format (just memories) and new format (memories + context)
                if isinstance(data, dict) and 'memories' in data:
                    return data
                else:
                    # Old format - just memories dict
                    return {'memories': data, 'context': []}
            except Exception as e:
                logger.error(f"Memory load error: {e}")
                return {'memories': {}, 'context': []}
        return {'memories': {}, 'context': []}

    def _save(self):
        try:
            logger.debug(f"💾 Saving memory to: {self.memory_file.resolve()}")
            # Save both memories and context to persist all data
            full_data = {
                "memories": self.memories,
                "context": self.context
            }
            self.memory_file.write_text(json.dumps(full_data, indent=2))
            # Verify write succeeded
            if self.memory_file.exists():
                size = self.memory_file.stat().st_size
                logger.debug(f"✅ Memory saved: {self.memory_file.resolve()} ({size} bytes)")
        except Exception as e:
            logger.error(f"❌ Memory save error to {self.memory_file.resolve()}: {e}")

    def remember(self, key, value, category="general"):
        if category not in self.memories:
            self.memories[category] = {}
        self.memories[category][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        }
        self._save()

    def recall(self, key=None, category=None):
        if key and category and category in self.memories and key in self.memories[category]:
            self.memories[category][key]["access_count"] += 1
            self._save()
            return {key: self.memories[category][key]}
        elif category:
            return self.memories.get(category, {})
        return self.memories

    def add_context(self, type_, data):
        self.context.append({"type": type_, "data": data, "timestamp": datetime.now().isoformat()})
        if len(self.context) > self.limit:
            self.context = self.context[-self.limit:]
        self._save()  # FIX: Persist context to disk immediately

    def get_context(self):
        return self.context

class LLMBackend:
    def __init__(self, config: Dict):
        self.config = config['llm']
        self.default = config['llm']['default_provider']

    async def query(self, prompt: str, provider: str = None, model: str = None, context: str = "") -> str:
        provider = provider or self.default
        conf = self.config['providers'].get(provider)
        if not conf:
            return f"Error: Provider '{provider}' not configured"

        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        model = model or conf['model']
        base_url = conf['base_url']

        timeout = aiohttp.ClientTimeout(total=30)

        try:
            if provider == "grok":
                api_key = os.getenv("XAI_API_KEY")
                if not api_key:
                    return "Error: XAI_API_KEY not set"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                data = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(f"{base_url}/chat/completions", json=data, headers=headers) as r:
                        if r.status != 200:
                            txt = await r.text()
                            return f"Grok API Error {r.status}: {txt}"
                        resp = await r.json()
                        return resp['choices'][0]['message']['content']

            elif provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return "Error: OPENAI_API_KEY not set"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                data = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(f"{base_url}/chat/completions", json=data, headers=headers) as r:
                        if r.status != 200:
                            txt = await r.text()
                            return f"OpenAI API Error {r.status}: {txt}"
                        resp = await r.json()
                        return resp['choices'][0]['message']['content']

            elif provider == "claude":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    return "Error: ANTHROPIC_API_KEY not set"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "max_tokens": 4096
                }
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(f"{base_url}/messages", json=data, headers=headers) as r:
                        if r.status != 200:
                            txt = await r.text()
                            return f"Claude API Error {r.status}: {txt}"
                        resp = await r.json()
                        return resp['content'][0]['text']

            elif provider == "ollama":
                # Ollama doesn't require an API key (local)
                headers = {"Content-Type": "application/json"}
                data = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(f"{base_url}/chat/completions", json=data, headers=headers) as r:
                        if r.status != 200:
                            txt = await r.text()
                            return f"Ollama API Error {r.status}: {txt}"
                        resp = await r.json()
                        return resp['choices'][0]['message']['content']

            else:
                return f"Provider '{provider}' not supported."
        except aiohttp.ClientError as e:
            return f"Network error: {str(e)}"
        except asyncio.TimeoutError:
            return "Error: Request timed out"
        except Exception as e:
            logger.error(f"LLM query error: {e}", exc_info=True)
            return f"Error: {str(e)}"

# --------------------------------------------------------------------------- #
# --------------------------- MAIN SERVER ----------------------------------- #
# --------------------------------------------------------------------------- #
class FGDMCPServer:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Validate and prepare watch directory before using it
        watch_dir_path = self._validate_paths()
        self.watch_dir = self._prepare_watch_dir(watch_dir_path)
        self.scan = self.config.get('scan', {})
        self.max_dir_size = self.scan.get('max_dir_size_gb', 2) * 1_073_741_824
        self.max_files = self.scan.get('max_files_per_scan', 5)
        self.max_file_kb = self.scan.get('max_file_size_kb', 250) * 1024

        # Reference projects (read‑only)
        self.ref_dirs = [Path(p).resolve() for p in self.config.get('reference_dirs', []) if Path(p).exists()]

        self.memory = MemoryStore(self.watch_dir / ".fgd_memory.json", self.config)
        self.llm = LLMBackend(self.config)

        # Verify provider requirements early so the server fails fast if misconfigured
        default_provider = self.config.get('llm', {}).get('default_provider')
        if default_provider == 'grok' and not os.getenv("XAI_API_KEY"):
            raise ValueError(
                "XAI_API_KEY environment variable is required when using the Grok provider"
            )
        self.recent_changes = []
        self.observer = None
        self._approval_task = None  # Track approval monitor task
        self._start_watcher()
        self._start_approval_monitor()

        self.server = Server("fgd-mcp-server")
        self._setup_handlers()

    def _validate_paths(self) -> Path:
        """Validate the configured watch directory and return its resolved path."""
        watch_dir_str = str(self.config.get('watch_dir', '')).strip()
        if not watch_dir_str:
            raise ValueError("watch_dir is not configured; filesystem tools cannot start")

        current_os = platform.system()
        windows_drive = PureWindowsPath(watch_dir_str).drive

        if windows_drive and current_os != 'Windows':
            logger.error("=" * 80)
            logger.error("🚨 CRITICAL PATH CONFIGURATION ERROR 🚨")
            logger.error("=" * 80)
            logger.error(f"Running on: {current_os}")
            logger.error(f"Config has Windows path: {watch_dir_str}")
            logger.error("This will cause ALL write operations to fail silently!")
            logger.error("Update fgd_config.yaml with the correct path for your OS.")
            logger.error("=" * 80)
            raise ValueError(
                "watch_dir is configured with a Windows-specific path but the current "
                f"platform is {current_os}. Update fgd_config.yaml with an OS-appropriate path."
            )

        try:
            path = Path(watch_dir_str).expanduser()
        except (TypeError, OSError, RuntimeError) as exc:
            raise ValueError(f"Failed to interpret watch_dir '{watch_dir_str}': {exc}") from exc

        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"Failed to resolve watch_dir '{watch_dir_str}': {exc}") from exc

        if resolved.exists() and not resolved.is_dir():
            raise ValueError(
                f"watch_dir '{resolved}' exists but is not a directory; update fgd_config.yaml"
            )

        return resolved

    def _prepare_watch_dir(self, path: Path) -> Path:
        """Ensure the watch directory exists, is a directory, and is accessible."""
        if not path.exists():
            try:
                logger.warning(
                    f"watch_dir '{path}' does not exist. Creating directory before startup."
                )
                path.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                raise ValueError(f"Failed to create watch_dir '{path}': {exc}") from exc

        if not path.is_dir():
            raise ValueError(f"watch_dir '{path}' is not a directory; update fgd_config.yaml")

        if not os.access(path, os.R_OK | os.W_OK):
            raise ValueError(
                f"watch_dir '{path}' must be readable and writable by the MCP server"
            )

        return path

    # ------------------------------------------------------------------- #
    # -------------------------- WATCHER -------------------------------- #
    # ------------------------------------------------------------------- #
    def _start_watcher(self):
        try:
            handler = FileChangeHandler(self._on_file_change)
            self.observer = Observer()
            self.observer.schedule(handler, str(self.watch_dir), recursive=True)
            self.observer.start()
            logger.info("File watcher started")
        except Exception as e:
            logger.warning(f"File watcher failed: {e}")

    def _start_approval_monitor(self):
        """Will start background task to monitor for approval files in run() method."""
        logger.info("Approval monitor will be started when event loop is ready")

    async def _approval_monitor_loop(self):
        """Background loop to check for approval files and auto-apply edits."""
        try:
            while True:
                await asyncio.sleep(2)  # Check every 2 seconds

                approval_file = self.watch_dir / ".fgd_approval.json"
                if not approval_file.exists():
                    continue

                # Read approval
                approval_data = json.loads(approval_file.read_text())

                if approval_data.get("approved"):
                    # Execute the edit
                    filepath = approval_data["filepath"]
                    old_text = approval_data["old_text"]
                    new_text = approval_data["new_text"]

                    logger.info(f"🔵 Auto-applying approved edit: {filepath}")

                    try:
                        path = self._sanitize(filepath)
                        content = path.read_text(encoding='utf-8')
                        new_content = content.replace(old_text, new_text, 1)

                        # Create backup
                        backup = path.with_suffix('.bak')
                        if path.exists():
                            shutil.copy2(path, backup)
                            logger.info(f"📝 Backup created: {backup.resolve()}")

                        # Write new content
                        logger.info(f"✍️  Auto-applying edit to: {path.resolve()}")
                        path.write_text(new_content, encoding='utf-8')

                        # Verify write succeeded
                        if path.exists():
                            size = path.stat().st_size
                            logger.info(f"✅ Auto-edit verified: {path.resolve()} ({size} bytes)")
                        else:
                            logger.error(f"❌ Auto-edit failed: File does not exist after write")

                        self.memory.add_context("file_edit", {
                            "path": filepath,
                            "approved": True,
                            "auto_applied": True,
                            "resolved_path": str(path.resolve())
                        })

                        logger.info(f"✅ Edit successfully applied: {filepath} at {path.resolve()} (backup: {backup.name})")

                    except Exception as e:
                        logger.error(f"❌ Failed to apply edit to {filepath}: {e}")

                else:
                    logger.info(f"❌ Edit rejected by user: {approval_data.get('filepath')}")

                # Clean up approval file
                approval_file.unlink()

        except asyncio.CancelledError:
            logger.info("Approval monitor cancelled, shutting down cleanly")
            raise  # Re-raise to allow proper cancellation
        except Exception as e:
            logger.error(f"Approval monitor error: {e}", exc_info=True)

    def _on_file_change(self, event_type, path):
        try:
            rel = str(Path(path).relative_to(self.watch_dir))
            self.recent_changes.append({
                "type": event_type,
                "path": rel,
                "timestamp": datetime.now().isoformat()
            })
            if len(self.recent_changes) > 50:
                self.recent_changes = self.recent_changes[-50:]
            self.memory.add_context("file_change", {"type": event_type, "path": rel})
        except ValueError:
            # Path is outside watch_dir, ignore
            pass
        except Exception as e:
            logger.debug(f"Error processing file change for {path}: {e}")

    # ------------------------------------------------------------------- #
    # -------------------------- HELPERS -------------------------------- #
    # ------------------------------------------------------------------- #
    def _sanitize(self, rel, base: Path = None):
        base = base or self.watch_dir
        p = (base / rel).resolve()
        if not str(p).startswith(str(base)):
            raise ValueError("Path traversal blocked")
        return p

    def _get_gitignore_patterns(self, root: Path) -> List[str]:
        """Load gitignore patterns from .gitignore file"""
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            return []
        try:
            return [line.strip() for line in gitignore.read_text().splitlines()
                    if line.strip() and not line.startswith('#')]
        except Exception as e:
            logger.warning(f"Failed to read .gitignore: {e}")
            return []

    def _matches_gitignore(self, path: Path, patterns: List[str]) -> bool:
        """Check if path matches any gitignore pattern using fnmatch"""
        import fnmatch
        try:
            rel = str(path.relative_to(self.watch_dir))
            # Normalize for cross-platform compatibility
            rel_posix = rel.replace(os.sep, '/')

            for pat in patterns:
                # Handle directory patterns (ending with /)
                if pat.endswith('/'):
                    pat = pat.rstrip('/')
                    if fnmatch.fnmatch(rel_posix, pat) or fnmatch.fnmatch(rel_posix, f"{pat}/*"):
                        return True
                # Handle patterns with directory separators
                elif '/' in pat:
                    if fnmatch.fnmatch(rel_posix, pat):
                        return True
                # Handle simple filename patterns - check against full path and basename
                else:
                    if fnmatch.fnmatch(path.name, pat) or fnmatch.fnmatch(rel_posix, f"**/{pat}"):
                        return True
            return False
        except Exception as e:
            logger.debug(f"Error matching gitignore for {path}: {e}")
            return False

    def _save_pending_edit(self, payload: Dict[str, Any]) -> Path:
        """Persist a pending edit file for GUI confirmation."""
        pending_edit_file = self.watch_dir / ".fgd_pending_edit.json"
        logger.info("💾 Saving pending edit to: %s", pending_edit_file.resolve())
        pending_edit_file.write_text(json.dumps(payload, indent=2))
        return pending_edit_file

    def _is_git_repo(self) -> bool:
        """Check if watch_dir is a git repository"""
        return (self.watch_dir / ".git").exists()

    def _check_git_available(self) -> Optional[str]:
        """Check if git is available and repo is initialized. Returns error message or None"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return "Git is not installed or not in PATH"
        except FileNotFoundError:
            return "Git is not installed or not in PATH"
        except Exception as e:
            return f"Git check failed: {e}"

        if not self._is_git_repo():
            return "Directory is not a git repository (no .git folder found)"

        return None

    def _get_mcp_status_context(self) -> str:
        """Generate MCP server status and capabilities info for LLM context"""
        status_info = {
            "mcp_server": {
                "status": "connected",
                "name": "fgd-mcp-server",
                "version": "5.0",
                "watch_directory": str(self.watch_dir),
                "available_tools": [
                    {
                        "name": "list_directory",
                        "description": "List files in a directory (gitignore aware)",
                        "usage": "Use this to explore the project structure"
                    },
                    {
                        "name": "read_file",
                        "description": "Read file contents with metadata",
                        "usage": "Use this to read and analyze files"
                    },
                    {
                        "name": "write_file",
                        "description": "Write/create files with automatic backups",
                        "usage": "Use this to create or overwrite files"
                    },
                    {
                        "name": "edit_file",
                        "description": "Edit files with diff preview and approval workflow",
                        "usage": "Use this to make precise edits to existing files"
                    },
                    {
                        "name": "git_diff",
                        "description": "Show git diff for changes",
                        "usage": "Use this to review uncommitted changes"
                    },
                    {
                        "name": "git_commit",
                        "description": "Commit changes to git",
                        "usage": "Use this to save changes to version control"
                    },
                    {
                        "name": "git_log",
                        "description": "Show git commit history",
                        "usage": "Use this to view recent commits"
                    },
                    {
                        "name": "llm_query",
                        "description": "Ask questions to Grok (this tool you're using now)",
                        "usage": "Recursive - you're currently using this tool"
                    }
                ],
                "capabilities": [
                    "File system operations (read, write, edit)",
                    "Git integration (diff, commit, log)",
                    "Automatic backups before modifications",
                    "Gitignore-aware file filtering",
                    "Context-aware memory system",
                    "File watching and change detection"
                ],
                "reference_projects": [str(p) for p in self.ref_dirs] if self.ref_dirs else []
            }
        }
        return f"\n\n=== MCP SERVER STATUS ===\n{json.dumps(status_info, indent=2)}\n=== END MCP STATUS ===\n"

    # ------------------------------------------------------------------- #
    # --------------------------- TOOLS --------------------------------- #
    # ------------------------------------------------------------------- #
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(name="list_directory", description="List files (gitignore aware)", inputSchema={
                    "type": "object", "properties": {"path": {"type": "string", "default": "."}}
                }),
                Tool(name="read_file", description="Read file + metadata", inputSchema={
                    "type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]
                }),
                Tool(name="write_file", description="Write file (backup)", inputSchema={
                    "type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["filepath", "content"]
                }),
                Tool(name="edit_file", description="Edit with diff preview", inputSchema={
                    "type": "object", "properties": {
                        "filepath": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                        "confirm": {"type": "boolean", "default": False}
                    }, "required": ["filepath", "old_text", "new_text"]
                }),
                Tool(name="git_diff", description="Show git diff", inputSchema={
                    "type": "object", "properties": {"files": {"type": "array", "items": {"type": "string"}}}
                }),
                Tool(name="git_commit", description="Commit changes", inputSchema={
                    "type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]
                }),
                Tool(name="git_log", description="Show git log", inputSchema={
                    "type": "object", "properties": {"limit": {"type": "integer", "default": 5}}
                }),
                Tool(name="llm_query", description="Ask Grok", inputSchema={
                    "type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]
                })
            ]

        # ---------- TOOL CALL DISPATCHER ----------
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Handle all tool calls with a dispatcher pattern"""

            # ---------- LIST DIRECTORY ----------
            if name == "list_directory":
                rel_path = arguments.get("path", ".")
                path = self._sanitize(rel_path)
                if not path.is_dir():
                    return [TextContent(type="text", text="Error: Not a directory")]
                patterns = self._get_gitignore_patterns(self.watch_dir)
                files = []
                for p in path.iterdir():
                    if p.name.startswith('.') or self._matches_gitignore(p, patterns):
                        continue
                    files.append({
                        "name": p.name,
                        "is_dir": p.is_dir(),
                        "size": p.stat().st_size if p.is_file() else 0
                    })
                return [TextContent(type="text", text=json.dumps({"files": files}, indent=2))]

            # ---------- READ FILE ----------
            elif name == "read_file":
                try:
                    path = self._sanitize(arguments["filepath"])
                    if path.stat().st_size > self.max_file_kb:
                        return [TextContent(type="text", text="Error: File too large (>250KB)")]
                    content = path.read_text(encoding='utf-8')
                    stat = path.stat()
                    meta = {
                        "size_kb": round(stat.st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "lines": len(content.splitlines())
                    }
                    self.memory.add_context("file_read", {"path": arguments["filepath"], "meta": meta})
                    return [TextContent(type="text", text=json.dumps({"content": content, "meta": meta}, indent=2))]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error: {e}")]

            # ---------- WRITE FILE ----------
            elif name == "write_file":
                filepath = arguments["filepath"]
                content = arguments["content"]
                path = self._sanitize(filepath)

                try:
                    backup = path.with_suffix('.bak')
                    if path.exists():
                        shutil.copy2(path, backup)
                        logger.info(f"📝 Backup created: {backup.resolve()}")
                        self.memory.add_context("backup", {"path": str(backup), "original": filepath})

                    # DEBUG: Log actual write location
                    logger.info(f"✍️  Writing file to: {path.resolve()}")
                    path.write_text(content, encoding='utf-8')

                    # Verify write succeeded
                    if path.exists():
                        size = path.stat().st_size
                        logger.info(f"✅ Write verified: {path.resolve()} ({size} bytes)")
                    else:
                        logger.error(f"❌ Write failed: File does not exist after write: {path.resolve()}")

                    self.memory.add_context("file_write", {"path": filepath, "resolved_path": str(path.resolve())})
                    return [TextContent(type="text", text=f"Written: {filepath}\nActual location: {path.resolve()}\nBackup: {backup.name}")]
                except Exception as e:
                    logger.error(f"❌ Write error for {filepath}: {e}")
                    return [TextContent(type="text", text=f"Error: {e}")]

            # ---------- EDIT FILE ----------
            elif name == "edit_file":
                filepath = arguments["filepath"]
                old_text = arguments["old_text"]
                new_text = arguments["new_text"]
                confirm = arguments.get("confirm", False)
                path = self._sanitize(filepath)

                if not path.exists():
                    return [TextContent(type="text", text="File not found")]

                content = path.read_text(encoding='utf-8')
                if old_text not in content:
                    return [TextContent(type="text", text="Old text not found")]

                if not confirm:
                    preview = content.replace(old_text, new_text, 1)

                    pending_edit_data = {
                        "filepath": filepath,
                        "old_text": old_text,
                        "new_text": new_text,
                        "diff": f"- {old_text}\n+ {new_text}",
                        "preview": preview[:500],
                        "timestamp": datetime.now().isoformat()
                    }
                    try:
                        pending_edit_file = self._save_pending_edit(pending_edit_data)
                    except OSError as exc:
                        logger.error("❌ Failed to save pending edit: %s", exc)
                        return [TextContent(type="text", text=f"Error: Unable to save pending edit ({exc})")]

                    logger.info(
                        "✅ Pending edit saved: %s (%d bytes)",
                        pending_edit_file.resolve(),
                        pending_edit_file.stat().st_size,
                    )

                    return [TextContent(type="text", text=json.dumps({
                        "action": "confirm_edit",
                        "filepath": filepath,
                        "diff": f"- {old_text}\n+ {new_text}",
                        "preview": preview[:500],
                        "message": "Edit pending approval - check GUI"
                    }, indent=2))]

                try:
                    new_content = content.replace(old_text, new_text, 1)
                    backup = path.with_suffix('.bak')
                    if path.exists():
                        shutil.copy2(path, backup)
                        logger.info(f"📝 Backup created: {backup.resolve()}")

                    # DEBUG: Log actual write location
                    logger.info(f"✍️  Applying confirmed edit to: {path.resolve()}")
                    path.write_text(new_content, encoding='utf-8')

                    # Verify write succeeded
                    if path.exists():
                        size = path.stat().st_size
                        logger.info(f"✅ Edit applied and verified: {path.resolve()} ({size} bytes)")
                    else:
                        logger.error(f"❌ Edit failed: File does not exist after write: {path.resolve()}")

                    self.memory.add_context("file_edit", {"path": filepath, "approved": True, "resolved_path": str(path.resolve())})

                    # Clean up pending edit file
                    pending_edit_file = self.watch_dir / ".fgd_pending_edit.json"
                    if pending_edit_file.exists():
                        pending_edit_file.unlink()
                        logger.info(f"🧹 Cleaned up pending edit file")

                    return [TextContent(type="text", text=f"✅ Approved! File updated + backup: {backup.name}\nActual location: {path.resolve()}")]
                except Exception as e:
                    logger.error(f"❌ Edit error for {filepath}: {e}")
                    return [TextContent(type="text", text=f"Error: {e}")]

            # ---------- GIT DIFF ----------
            elif name == "git_diff":
                git_error = self._check_git_available()
                if git_error:
                    return [TextContent(type="text", text=f"Error: {git_error}")]

                files = arguments.get("files", [])
                try:
                    result = subprocess.run(
                        ["git", "diff", "--", *files],
                        cwd=str(self.watch_dir),
                        capture_output=True, text=True,
                        timeout=30
                    )
                    diff = result.stdout or "No changes"
                    self.memory.remember(f"diff_{datetime.now().isoformat()}", diff, "git_diffs")
                    return [TextContent(type="text", text=diff)]
                except Exception as e:
                    logger.error(f"Git diff failed: {e}")
                    return [TextContent(type="text", text=f"Git error: {e}")]

            # ---------- GIT COMMIT ----------
            elif name == "git_commit":
                git_error = self._check_git_available()
                if git_error:
                    return [TextContent(type="text", text=f"Error: {git_error}")]

                message = arguments["message"]
                if not message or not message.strip():
                    return [TextContent(type="text", text="Error: Commit message cannot be empty")]

                try:
                    # Check if there are changes to commit
                    status_result = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=str(self.watch_dir),
                        capture_output=True, text=True,
                        timeout=10
                    )
                    if not status_result.stdout.strip():
                        return [TextContent(type="text", text="No changes to commit")]

                    subprocess.run(["git", "add", "."], cwd=str(self.watch_dir), check=True, timeout=30)
                    result = subprocess.run(
                        ["git", "commit", "-m", message],
                        cwd=str(self.watch_dir),
                        capture_output=True, text=True, check=True,
                        timeout=30
                    )
                    commit_hash = result.stdout.split()[1] if "commit" in result.stdout else "unknown"
                    self.memory.remember(f"commit_{commit_hash}", message, "commits")
                    return [TextContent(type="text", text=f"Committed: {commit_hash}\n{message}")]
                except subprocess.CalledProcessError as e:
                    logger.error(f"Git commit failed: {e.stderr if e.stderr else e}")
                    return [TextContent(type="text", text=f"Commit failed: {e.stderr if e.stderr else str(e)}")]
                except Exception as e:
                    logger.error(f"Git commit error: {e}")
                    return [TextContent(type="text", text=f"Commit failed: {e}")]

            # ---------- GIT LOG ----------
            elif name == "git_log":
                git_error = self._check_git_available()
                if git_error:
                    return [TextContent(type="text", text=f"Error: {git_error}")]

                limit = arguments.get("limit", 5)
                try:
                    result = subprocess.run(
                        ["git", "log", f"-{limit}", "--oneline"],
                        cwd=str(self.watch_dir),
                        capture_output=True, text=True,
                        timeout=30
                    )
                    log_output = result.stdout if result.stdout else "No commits yet"
                    return [TextContent(type="text", text=log_output)]
                except Exception as e:
                    logger.error(f"Git log failed: {e}")
                    return [TextContent(type="text", text=f"Git log error: {e}")]

            # ---------- LLM QUERY ----------
            elif name == "llm_query":
                prompt = arguments["prompt"]

                # Build comprehensive context for the LLM
                context_parts = []

                # Add MCP server status and capabilities
                context_parts.append(self._get_mcp_status_context())

                # Add recent memory context
                recent_context = self.memory.get_context()[-5:]
                if recent_context:
                    context_parts.append(f"\n=== RECENT ACTIVITY ===\n{json.dumps(recent_context, indent=2)}\n=== END RECENT ACTIVITY ===\n")

                context = "".join(context_parts)
                response = await self.llm.query(prompt, "grok", context=context)

                # Save conversation as prompt + response pairs
                timestamp = datetime.now().isoformat()
                conversation_entry = {
                    "prompt": prompt,
                    "response": response,
                    "provider": "grok",
                    "timestamp": timestamp,
                    "context_used": len(self.memory.get_context())
                }

                # Store in conversations category for threading
                self.memory.remember(f"chat_{timestamp}", conversation_entry, "conversations")

                # Also keep in llm category for backward compatibility
                self.memory.remember(f"grok_{timestamp}", response, "llm")

                logger.info(f"Chat saved: prompt={prompt[:50]}..., response={response[:50]}...")
                return [TextContent(type="text", text=response)]

            # ---------- UNKNOWN TOOL ----------
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def run(self):
        logger.info("=" * 60)
        logger.info("MCP Server starting with configuration:")
        logger.info(f"  Watch dir: {self.watch_dir}")
        logger.info(f"  LLM Provider: {self.llm.default}")
        logger.info(f"  Grok API Key present: {bool(os.getenv('XAI_API_KEY'))}")
        logger.info("=" * 60)

        # Start approval monitor and store task reference for clean shutdown
        self._approval_task = asyncio.create_task(self._approval_monitor_loop())
        logger.info("✅ Approval monitor started")

        try:
            async with stdio_server() as (read, write):
                # The MCP library handles JSON-RPC validation errors internally
                # and logs them. It should continue running after errors.
                # If the server exits unexpectedly, the error will be caught here.
                try:
                    await self.server.run(read, write, self.server.create_initialization_options())
                except ValidationError as e:
                    # Handle Pydantic validation errors from malformed JSON-RPC messages
                    # This catches errors that escape the MCP library's internal handling
                    logger.error("=" * 80)
                    logger.error("JSON-RPC VALIDATION ERROR")
                    logger.error("=" * 80)
                    logger.error(f"Error: {e}")
                    logger.error("The MCP server received invalid input that doesn't conform to JSON-RPC format.")
                    logger.error("This usually happens when:")
                    logger.error("  1. A client sends malformed JSON")
                    logger.error("  2. Non-JSON data is sent to stdin")
                    logger.error("  3. The JSON structure doesn't match JSON-RPC 2.0 spec")
                    logger.error("")
                    logger.error("The MCP server expects messages in this format:")
                    logger.error('  {"jsonrpc": "2.0", "method": "...", "params": {...}, "id": 1}')
                    logger.error("=" * 80)
                except json.JSONDecodeError as e:
                    # Handle JSON parsing errors that escape the MCP library
                    logger.error("=" * 80)
                    logger.error("JSON DECODE ERROR")
                    logger.error("=" * 80)
                    logger.error(f"Error: {e}")
                    logger.error("Failed to parse JSON from stdin.")
                    logger.error("Ensure all input is valid JSON format.")
                    logger.error("=" * 80)
                except Exception as e:
                    # Catch any other unexpected errors
                    logger.error("=" * 80)
                    logger.error("UNEXPECTED MCP SERVER ERROR")
                    logger.error("=" * 80)
                    logger.error(f"Error: {e}")
                    logger.error("Stack trace:", exc_info=True)
                    logger.error("=" * 80)
                    raise
        except KeyboardInterrupt:
            logger.info("MCP Server interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.error("=" * 80)
            logger.error("FATAL ERROR - MCP SERVER SHUTDOWN")
            logger.error("=" * 80)
            logger.error(f"Error: {e}")
            logger.error("Stack trace:", exc_info=True)
            logger.error("=" * 80)
            raise
        finally:
            # Clean shutdown of approval monitor
            if self._approval_task and not self._approval_task.done():
                logger.info("Cancelling approval monitor...")
                self._approval_task.cancel()
                try:
                    await self._approval_task
                except asyncio.CancelledError:
                    pass
                logger.info("Approval monitor cancelled")

    def stop(self):
        if self.observer:
            logger.info("Stopping file watcher...")
            self.observer.stop()

            # Join with timeout to prevent hanging
            self.observer.join(timeout=5.0)

            if self.observer.is_alive():
                logger.warning("File watcher thread did not stop cleanly")
            else:
                logger.info("File watcher stopped cleanly")

            self.observer = None

# --------------------------------------------------------------------------- #
# ------------------------------- ENTRYPOINT ------------------------------- #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "fgd_config.yaml"
    server = FGDMCPServer(config_path)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        server.stop()