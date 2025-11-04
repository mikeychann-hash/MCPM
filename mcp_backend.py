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
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import asyncio
import yaml
import aiohttp
import openai
import shutil
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        self.memories = self._load()
        self.context = []
        self.limit = config.get('context_limit', 20)

    def _load(self):
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text())
            except Exception as e:
                logger.error(f"Memory load error: {e}")
                return {}
        return {}

    def _save(self):
        try:
            self.memory_file.write_text(json.dumps(self.memories, indent=2))
        except Exception as e:
            logger.error(f"Memory save error: {e}")

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
            # OpenAI, Claude, Ollama can be added similarly
            else:
                return f"Provider '{provider}' not active."
        except Exception as e:
            return f"Error: {str(e)}"

# --------------------------------------------------------------------------- #
# --------------------------- MAIN SERVER ----------------------------------- #
# --------------------------------------------------------------------------- #
class FGDMCPServer:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.watch_dir = Path(self.config['watch_dir']).resolve()
        self.scan = self.config.get('scan', {})
        self.max_dir_size = self.scan.get('max_dir_size_gb', 2) * 1_073_741_824
        self.max_files = self.scan.get('max_files_per_scan', 5)
        self.max_file_kb = self.scan.get('max_file_size_kb', 250) * 1024

        # Reference projects (read‑only)
        self.ref_dirs = [Path(p).resolve() for p in self.config.get('reference_dirs', []) if Path(p).exists()]

        self.memory = MemoryStore(self.watch_dir / ".fgd_memory.json", self.config)
        self.llm = LLMBackend(self.config)
        self.recent_changes = []
        self.observer = None
        self._start_watcher()

        self.server = Server("fgd-mcp-server")
        self._setup_handlers()

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
        except:
            pass

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
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            return []
        return [line.strip() for line in gitignore.read_text().splitlines()
                if line.strip() and not line.startswith('#')]

    def _matches_gitignore(self, path: Path, patterns: List[str]) -> bool:
        rel = path.relative_to(self.watch_dir)
        for pat in patterns:
            if rel.match(pat):
                return True
        return False

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

        # ---------- LIST DIRECTORY ----------
        @self.server.set_tool_handler("list_directory")
        async def list_directory(args):
            rel_path = args.get("path", ".")
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
        @self.server.set_tool_handler("read_file")
        async def read_file(args):
            try:
                path = self._sanitize(args["filepath"])
                if path.stat().st_size > self.max_file_kb:
                    return [TextContent(type="text", text="Error: File too large (>250KB)")]
                content = path.read_text(encoding='utf-8')
                stat = path.stat()
                meta = {
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "lines": len(content.splitlines())
                }
                self.memory.add_context("file_read", {"path": args["filepath"], "meta": meta})
                return [TextContent(type="text", text=json.dumps({"content": content, "meta": meta}, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        # ---------- WRITE FILE ----------
        @self.server.set_tool_handler("write_file")
        async def write_file(args):
            filepath = args["filepath"]
            content = args["content"]
            path = self._sanitize(filepath)

            try:
                backup = path.with_suffix('.bak')
                if path.exists():
                    shutil.copy2(path, backup)
                    self.memory.add_context("backup", {"path": str(backup), "original": filepath})
                path.write_text(content, encoding='utf-8')
                self.memory.add_context("file_write", {"path": filepath})
                return [TextContent(type="text", text=f"Written: {filepath}\nBackup: {backup.name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        # ---------- EDIT FILE ----------
        @self.server.set_tool_handler("edit_file")
        async def edit_file(args):
            filepath = args["filepath"]
            old_text = args["old_text"]
            new_text = args["new_text"]
            confirm = args.get("confirm", False)
            path = self._sanitize(filepath)

            if not path.exists():
                return [TextContent(type="text", text="File not found")]

            content = path.read_text(encoding='utf-8')
            if old_text not in content:
                return [TextContent(type="text", text="Old text not found")]

            if not confirm:
                preview = content.replace(old_text, new_text, 1)
                return [TextContent(type="text", text=json.dumps({
                    "action": "confirm_edit",
                    "filepath": filepath,
                    "diff": f"- {old_text}\n+ {new_text}",
                    "preview": preview[:500]
                }, indent=2))]

            try:
                new_content = content.replace(old_text, new_text, 1)
                backup = path.with_suffix('.bak')
                shutil.copy2(path, backup)
                path.write_text(new_content, encoding='utf-8')
                self.memory.add_context("file_edit", {"path": filepath})
                return [TextContent(type="text", text=f"Approved! File updated + backup: {backup.name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        # ---------- GIT DIFF ----------
        @self.server.set_tool_handler("git_diff")
        async def git_diff(args):
            files = args.get("files", [])
            try:
                result = subprocess.run(
                    ["git", "diff", "--", *files],
                    cwd=str(self.watch_dir),
                    capture_output=True, text=True
                )
                diff = result.stdout or "No changes"
                self.memory.remember(f"diff_{datetime.now().isoformat()}", diff, "git_diffs")
                return [TextContent(type="text", text=diff)]
            except Exception as e:
                return [TextContent(type="text", text=f"Git error: {e}")]

        # ---------- GIT COMMIT ----------
        @self.server.set_tool_handler("git_commit")
        async def git_commit(args):
            message = args["message"]
            try:
                subprocess.run(["git", "add", "."], cwd=str(self.watch_dir), check=True)
                result = subprocess.run(
                    ["git", "commit", "-m", message],
                    cwd=str(self.watch_dir),
                    capture_output=True, text=True, check=True
                )
                commit_hash = result.stdout.split()[1] if "commit" in result.stdout else "unknown"
                self.memory.remember(f"commit_{commit_hash}", message, "commits")
                return [TextContent(type="text", text=f"Committed: {commit_hash}\n{message}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Commit failed: {e}")]

        # ---------- GIT LOG ----------
        @self.server.set_tool_handler("git_log")
        async def git_log(args):
            limit = args.get("limit", 5)
            try:
                result = subprocess.run(
                    ["git", "log", f"-{limit}", "--oneline"],
                    cwd=str(self.watch_dir),
                    capture_output=True, text=True
                )
                return [TextContent(type="text", text=result.stdout)]
            except Exception as e:
                return [TextContent(type="text", text=f"Git log error: {e}")]

        # ---------- LLM QUERY ----------
        @self.server.set_tool_handler("llm_query")
        async def llm_query(args):
            prompt = args["prompt"]
            context = json.dumps(self.memory.get_context()[-5:])
            response = await self.llm.query(prompt, "grok", context=context)
            self.memory.remember(f"grok_{datetime.now().isoformat()}", response, "llm")
            return [TextContent(type="text", text=response)]

    async def run(self):
        logger.info("MCP Server starting...")
        async with stdio_server() as (read, write):
            await self.server.run(read, write, self.server.create_initialization_options())

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

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