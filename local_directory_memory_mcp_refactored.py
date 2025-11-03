#!/usr/bin/env python3
"""
FGD Stack MCP Server – File + Memory + LLM (Grok & ChatGPT only)
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable, Awaitable, Any
import asyncio
import yaml
import aiohttp
from openai import OpenAI

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            except:
                return {}
        return {}

    def _save(self):
        try:
            self.memory_file.write_text(json.dumps(self.memories, indent=2))
        except Exception as e:
            logger.error(f"Memory save failed: {e}")

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
    def __init__(self, config):
        self.config = config['llm']
        self.default = config['llm']['default_provider']

    async def query(self, prompt: str, provider: str = None, model: str = None, context: str = "") -> str:
        provider = provider or self.default
        conf = self.config['providers'].get(provider)
        if not conf:
            return f"Error: Provider '{provider}' not configured"
        model = model or conf['model']
        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        try:
            if provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return "Error: OPENAI_API_KEY not set"
                client = OpenAI(api_key=api_key)
                resp = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                return resp.choices[0].message.content
            elif provider == "grok":
                api_key = os.getenv('XAI_API_KEY')
                if not api_key:
                    return "Error: XAI_API_KEY not set"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{conf['base_url']}/chat/completions", json=data, headers=headers) as r:
                        if r.status != 200:
                            text = await r.text()
                            return f"Grok API Error {r.status}: {text}"
                        resp = await r.json()
                        return resp['choices'][0]['message']['content']
            else:
                return f"Error: Provider '{provider}' not supported"
        except Exception as e:
            return f"Error: {str(e)}"

class FGDMCPServer:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.watch_dir = Path(self.config['watch_dir']).resolve()
        self.scan = self.config.get('scan', {})
        self.max_dir_size = self.scan.get('max_dir_size_gb', 2) * 1_073_741_824
        self.max_files = self.scan.get('max_files_per_scan', 5)
        self.max_file_bytes = self.scan.get('max_file_size_kb', 250) * 1024

        self.memory = MemoryStore(self.watch_dir / ".fgd_memory.json", self.config)
        self.llm = LLMBackend(self.config)
        self.recent_changes = []
        self.log_file = self._resolve_log_file()
        self._ensure_log_handler()
        logger.info("Logging to %s", self.log_file)

        self.server = Server("fgd-mcp-server")
        self._setup_tools()

    def _resolve_log_file(self) -> Path:
        configured = self.config.get('log_file')
        if configured:
            candidate = Path(configured)
            if not candidate.is_absolute():
                candidate = (self.watch_dir / candidate).resolve()
        else:
            candidate = (self.watch_dir / "fgd_server.log").resolve()
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def _ensure_log_handler(self) -> None:
        existing = [
            h for h in logger.handlers
            if isinstance(h, logging.FileHandler) and Path(getattr(h, 'baseFilename', '')) == self.log_file
        ]
        if existing:
            return
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

    def _sanitize(self, p):
        norm = os.path.normpath(p)
        if norm.startswith('..') or os.path.isabs(norm):
            raise ValueError("Invalid path")
        return self.watch_dir / norm

    def _hash(self, path):
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""

    def _check_dir_size(self):
        total = sum(f.stat().st_size for f in self.watch_dir.rglob('*') if f.is_file())
        return total <= self.max_dir_size

    def _setup_tools(self):
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="list_files",
                    description="List files",
                    inputSchema={
                        "type": "object",
                        "properties": {"pattern": {"type": "string", "default": "**/*"}},
                    },
                ),
                Tool(
                    name="read_file",
                    description="Read file",
                    inputSchema={
                        "type": "object",
                        "properties": {"filepath": {"type": "string"}},
                        "required": ["filepath"],
                    },
                ),
                Tool(
                    name="search_in_files",
                    description="Search text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "pattern": {"type": "string", "default": "**/*"},
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="llm_query",
                    description="Ask LLM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "provider": {
                                "type": "string",
                                "enum": ["grok", "openai"],
                                "default": "grok",
                            },
                        },
                        "required": ["prompt"],
                    },
                ),
                Tool(
                    name="remember",
                    description="Store memory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string"},
                            "category": {"type": "string", "default": "general"},
                        },
                        "required": ["key", "value"],
                    },
                ),
                Tool(
                    name="recall",
                    description="Recall memory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "category": {"type": "string"},
                        },
                    },
                ),
            ]

        async def handle_list_files(args):
            pattern = args.get("pattern", "**/*")
            files = []
            for p in self.watch_dir.glob(pattern):
                if not p.is_file():
                    continue
                files.append(str(p.relative_to(self.watch_dir)))
                if len(files) >= self.max_files:
                    break
            return [TextContent(type="text", text=json.dumps({"files": files}, indent=2))]

        async def handle_read_file(args):
            try:
                filepath = args.get("filepath")
                if not filepath:
                    return [TextContent(type="text", text="Error: Missing 'filepath' argument")]
                path = self._sanitize(filepath)
                if path.stat().st_size > self.max_file_bytes:
                    limit_kb = self.max_file_bytes // 1024
                    return [TextContent(type="text", text=f"Error: File too large (>{limit_kb} KB)")]
                content = path.read_text(encoding='utf-8')
                self.memory.add_context("file_read", {"path": filepath})
                return [TextContent(type="text", text=json.dumps({"content": content}, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        async def handle_search_in_files(args):
            if not self._check_dir_size():
                return [TextContent(type="text", text="Error: Directory exceeds 2 GB")]
            query = args.get("query")
            if not query:
                return [TextContent(type="text", text="Error: Missing 'query' argument")]
            pattern = args.get("pattern", "**/*")
            matches = []
            count = 0
            for p in self.watch_dir.glob(pattern):
                if count >= self.max_files or not p.is_file() or p.stat().st_size > self.max_file_bytes:
                    continue
                try:
                    content = p.read_text(encoding='utf-8').lower()
                    if query.lower() in content:
                        matches.append({"filepath": str(p.relative_to(self.watch_dir))})
                    count += 1
                except Exception:
                    continue
            return [TextContent(type="text", text=json.dumps({"matches": matches}, indent=2))]

        async def handle_llm_query(args):
            prompt = args.get("prompt")
            if not prompt:
                return [TextContent(type="text", text="Error: Missing 'prompt' argument")]
            provider = args.get("provider", "grok")
            context = json.dumps(self.memory.get_context()[-5:])
            response = await self.llm.query(prompt, provider, context=context)
            self.memory.remember(f"llm_{datetime.now().isoformat()}", response, "llm")
            return [TextContent(type="text", text=json.dumps({"response": response}, indent=2))]

        async def handle_remember(args):
            key = args.get("key")
            value = args.get("value")
            if not key or value is None:
                return [TextContent(type="text", text="Error: Missing 'key' or 'value' argument")]
            self.memory.remember(key, value, args.get("category", "general"))
            return [TextContent(type="text", text="Saved to memory")]

        async def handle_recall(args):
            data = self.memory.recall(args.get("key"), args.get("category"))
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        tool_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[List[TextContent]]]] = {
            "list_files": handle_list_files,
            "read_file": handle_read_file,
            "search_in_files": handle_search_in_files,
            "llm_query": handle_llm_query,
            "remember": handle_remember,
            "recall": handle_recall,
        }

        @self.server.call_tool()
        async def handle_tool_call(tool_name, arguments):
            handler = tool_handlers.get(tool_name)
            if not handler:
                return [TextContent(type="text", text=f"Error: Unknown tool '{tool_name}'")]
            return await handler(arguments or {})

    async def run(self):
        async with stdio_server() as (read, write):
            await self.server.run(read, write, self.server.create_initialization_options())

if __name__ == "__main__":
    import sys
    config = sys.argv[1] if len(sys.argv) > 1 else "fgd_config.yaml"
    server = FGDMCPServer(config)
    asyncio.run(server.run())
