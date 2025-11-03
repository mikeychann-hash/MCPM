#!/usr/bin/env python3
"""
FGD Stack MCP Server – File + Memory + LLM (Grok & ChatGPT only)
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import asyncio
import yaml
import aiohttp
import openai

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
        conf = self.config['providers'][provider]
        model = model or conf['model']
        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        try:
            if provider == "openai":
                client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                resp = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                return resp.choices[0].message.content
            elif provider == "grok":
                headers = {
                    "Authorization": f"Bearer {os.getenv('XAI_API_KEY')}",
                    "Content-Type": "application/json"
                }
                data = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{conf['base_url']}/chat/completions", json=data, headers=headers) as r:
                        resp = await r.json()
                        return resp['choices'][0]['message']['content']
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
        self.max_file_kb = self.scan.get('max_file_size_kb', 250) * 1024

        self.memory = MemoryStore(self.watch_dir / ".fgd_memory.json", self.config)
        self.llm = LLMBackend(self.config)
        self.file_cache = {}
        self.recent_changes = []

        self.server = Server("fgd-mcp-server")
        self._setup_tools()

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
                Tool(name="list_files", description="List files", inputSchema={
                    "type": "object", "properties": {"pattern": {"type": "string", "default": "**/*"}}
                }),
                Tool(name="read_file", description="Read file", inputSchema={
                    "type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]
                }),
                Tool(name="search_in_files", description="Search text", inputSchema={
                    "type": "object", "properties": {"query": {"type": "string"}, "pattern": {"type": "string", "default": "**/*"}},
                    "required": ["query"]
                }),
                Tool(name="llm_query", description="Ask LLM", inputSchema={
                    "type": "object", "properties": {
                        "prompt": {"type": "string"},
                        "provider": {"type": "string", "enum": ["grok", "openai"], "default": "grok"}
                    }, "required": ["prompt"]
                }),
                Tool(name="remember", description="Store memory", inputSchema={
                    "type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}, "category": {"type": "string", "default": "general"}},
                    "required": ["key", "value"]
                }),
                Tool(name="recall", description="Recall memory", inputSchema={
                    "type": "object", "properties": {"key": {"type": "string"}, "category": {"type": "string"}}
                })
            ]

        @self.server.set_tool_handler("read_file")
        async def read_file(args):
            try:
                path = self._sanitize(args["filepath"])
                if path.stat().st_size > self.max_file_kb:
                    return [TextContent(type="text", text="Error: File too large")]
                content = path.read_text(encoding='utf-8')
                self.memory.add_context("file_read", {"path": args["filepath"]})
                return [TextContent(type="text", text=json.dumps({"content": content}, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        @self.server.set_tool_handler("search_in_files")
        async def search_in_files(args):
            if not self._check_dir_size():
                return [TextContent(type="text", text="Error: Directory exceeds 2 GB")]
            query = args["query"].lower()
            pattern = args.get("pattern", "**/*")
            matches = []
            count = 0
            for p in self.watch_dir.glob(pattern):
                if count >= self.max_files or not p.is_file() or p.stat().st_size > self.max_file_kb:
                    continue
                try:
                    content = p.read_text(encoding='utf-8').lower()
                    if query in content:
                        matches.append({"filepath": str(p.relative_to(self.watch_dir))})
                    count += 1
                except:
                    continue
            return [TextContent(type="text", text=json.dumps({"matches": matches}, indent=2))]

        @self.server.set_tool_handler("llm_query")
        async def llm_query(args):
            prompt = args["prompt"]
            provider = args.get("provider", "grok")
            context = json.dumps(self.memory.get_context()[-5:])
            response = await self.llm.query(prompt, provider, context=context)
            self.memory.remember(f"llm_{datetime.now().isoformat()}", response, "llm")
            return [TextContent(type="text", text=json.dumps({"response": response}, indent=2))]

        @self.server.set_tool_handler("remember")
        async def remember(args):
            self.memory.remember(args["key"], args["value"], args.get("category", "general"))
            return [TextContent(type="text", text="Saved to memory")]

        @self.server.set_tool_handler("recall")
        async def recall(args):
            data = self.memory.recall(args.get("key"), args.get("category"))
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

    async def run(self):
        async with stdio_server() as (read, write):
            await self.server.run(read, write, self.server.create_initialization_options())

if __name__ == "__main__":
    import sys
    config = sys.argv[1] if len(sys.argv) > 1 else "fgd_config.yaml"
    server = FGDMCPServer(config)
    asyncio.run(server.run())