#!/usr/bin/env python3
"""
FGD Stack MCP Server – FULLY WORKING, GROK-ONLY
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
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# CORRECT MCP IMPORTS
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MEMORY STORE ====================
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

# ==================== LLM BACKEND ====================
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
                            text = await r.text()
                            return f"Grok API Error {r.status}: {text}"
                        resp = await r.json()
                        return resp['choices'][0]['message']['content']

            # Other providers (disabled unless key exists)
            else:
                return f"Provider '{provider}' not active. Only Grok is enabled."

        except Exception as e:
            return f"Error: {str(e)}"

# ==================== FILE WATCHER ====================
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

# ==================== MAIN SERVER ====================
class FGDMCPServer:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.watch_dir = Path(self.config['watch_dir']).resolve()
        self.scan = self.config.get('scan', {})
        self.max_dir_size = self.scan.get('max_dir_size_gb', 2) * 1_073_741_824
        self.max_files = self.scan.get('max_files_per_scan', 5)
        self.max_file_kb = self.scan.get('max_file_size_kb', 250) * 1024

        self.memory = MemoryStore(self.watch_dir / ".fgd_memory.json", self.config)
        self.llm = LLMBackend(self.config)
        self.recent_changes = []
        self.observer = None
        self._start_watcher()

        self.server = Server("fgd-mcp-server")
        self._setup_handlers()

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

    def _sanitize(self, rel):
        p = (self.watch_dir / rel).resolve()
        if not str(p).startswith(str(self.watch_dir)):
            raise ValueError("Path traversal blocked")
        return p

    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(name="read_file", description="Read file", inputSchema={"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}),
                Tool(name="llm_query", description="Ask Grok", inputSchema={"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}),
            ]

        @self.server.set_tool_handler("read_file")
        async def read_file(args):
            try:
                path = self._sanitize(args["filepath"])
                if path.stat().st_size > self.max_file_kb:
                    return [TextContent(type="text", text="Error: File too large (>250KB)")]
                content = path.read_text(encoding='utf-8')
                self.memory.add_context("file_read", {"path": args["filepath"]})
                return [TextContent(type="text", text=content)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

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

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "fgd_config.yaml"
    server = FGDMCPServer(config_path)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        server.stop()