#!/usr/bin/env python3
"""
FGD Stack MCP Server – Production-Ready with Complete LLM Support

Features:
- Pydantic config validation
- Complete Claude API support
- Rate limiting for LLM queries
- Graceful shutdown handling
- Comprehensive type hints
- Hardened path security
- Detailed error messages
"""

import os
import json
import logging
import signal
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Awaitable, List, Optional
from collections import deque

import yaml
import aiohttp
from pydantic import BaseModel, Field, validator
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== PYDANTIC MODELS ====================

class ScanConfig(BaseModel):
    """Configuration for file scanning limits."""
    max_dir_size_gb: int = Field(default=2, ge=1, le=10)
    max_files_per_scan: int = Field(default=5, ge=1, le=100)
    max_file_size_kb: int = Field(default=250, ge=1, le=10000)


class ProviderConfig(BaseModel):
    """Configuration for individual LLM provider."""
    model: str
    base_url: str


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""
    default_provider: str = Field(default="grok")
    providers: Dict[str, ProviderConfig]

    @validator('default_provider')
    def validate_default_provider(cls, v):
        """Ensure default provider is grok for reliability."""
        if v not in ['grok', 'openai', 'claude', 'ollama']:
            logger.warning(f"Invalid default_provider '{v}', falling back to 'grok'")
            return 'grok'
        return v


class ServerConfig(BaseModel):
    """Main server configuration with validation."""
    watch_dir: str
    memory_file: str = Field(default=".fgd_memory.json")
    log_file: str = Field(default="fgd_server.log")
    context_limit: int = Field(default=20, ge=5, le=100)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    llm: LLMConfig

    @validator('watch_dir')
    def validate_watch_dir(cls, v):
        """Validate watch directory exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"watch_dir does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"watch_dir is not a directory: {v}")
        return str(path.resolve())


# ==================== RATE LIMITER ====================

class RateLimiter:
    """Token bucket rate limiter for LLM queries."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()

    async def acquire(self) -> bool:
        """
        Attempt to acquire permission for a request.

        Returns:
            True if request is allowed, False if rate limited
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Remove old requests outside the window
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

        # Check if we're at the limit
        if len(self.requests) >= self.max_requests:
            return False

        # Add this request
        self.requests.append(now)
        return True

    def get_wait_time(self) -> float:
        """
        Get time to wait before next request is allowed.

        Returns:
            Seconds to wait, or 0 if request would be allowed now
        """
        if len(self.requests) < self.max_requests:
            return 0.0

        oldest = self.requests[0]
        cutoff = oldest + timedelta(seconds=self.window_seconds)
        wait = (cutoff - datetime.now()).total_seconds()
        return max(0.0, wait)


# ==================== MEMORY STORE ====================

class MemoryStore:
    """Persistent memory storage with categorization and access tracking."""

    def __init__(self, memory_file: Path, config: ServerConfig):
        """
        Initialize memory store.

        Args:
            memory_file: Path to JSON memory file
            config: Server configuration
        """
        self.memory_file = memory_file
        self.memories: Dict[str, Dict[str, Any]] = self._load()
        self.context: List[Dict[str, Any]] = []
        self.limit = config.context_limit

    def _load(self) -> Dict[str, Dict[str, Any]]:
        """
        Load memories from disk.

        Returns:
            Dictionary of categorized memories
        """
        if self.memory_file.exists():
            try:
                content = self.memory_file.read_text(encoding='utf-8')
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse memory file: {e}")
                return {}
            except IOError as e:
                logger.error(f"Failed to read memory file: {e}")
                return {}
        return {}

    def _save(self) -> None:
        """Save memories to disk."""
        try:
            self.memory_file.write_text(
                json.dumps(self.memories, indent=2),
                encoding='utf-8'
            )
        except IOError as e:
            logger.error(f"Failed to save memory file: {e}")

    def remember(self, key: str, value: Any, category: str = "general") -> None:
        """
        Store a memory.

        Args:
            key: Memory key
            value: Memory value (must be JSON serializable)
            category: Memory category for organization
        """
        if category not in self.memories:
            self.memories[category] = {}

        self.memories[category][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        }
        self._save()
        logger.debug(f"Stored memory: category={category}, key={key}")

    def recall(
        self,
        key: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve memories.

        Args:
            key: Specific memory key (optional)
            category: Memory category (optional)

        Returns:
            Matching memories
        """
        if key and category:
            if category in self.memories and key in self.memories[category]:
                self.memories[category][key]["access_count"] += 1
                self._save()
                return {key: self.memories[category][key]}
            return {}
        elif category:
            return self.memories.get(category, {})
        return self.memories

    def add_context(self, type_: str, data: Any) -> None:
        """
        Add item to rolling context window.

        Args:
            type_: Context type (e.g., 'file_change', 'file_read')
            data: Context data
        """
        self.context.append({
            "type": type_,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

        # Maintain rolling window
        if len(self.context) > self.limit:
            self.context = self.context[-self.limit:]

    def get_context(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent context items.

        Args:
            count: Number of recent items to return

        Returns:
            List of recent context items
        """
        return self.context[-count:] if self.context else []


# ==================== LLM BACKEND ====================

class LLMBackend:
    """Multi-provider LLM backend with complete API support."""

    def __init__(self, config: ServerConfig, rate_limiter: RateLimiter):
        """
        Initialize LLM backend.

        Args:
            config: Server configuration
            rate_limiter: Rate limiter instance
        """
        self.config = config.llm
        self.default = config.llm.default_provider
        self.rate_limiter = rate_limiter
        self.timeout = aiohttp.ClientTimeout(total=60)

    async def query(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        context: str = ""
    ) -> str:
        """
        Query an LLM provider with rate limiting.

        Args:
            prompt: User prompt
            provider: LLM provider name (defaults to config)
            model: Model name override (optional)
            context: Additional context to prepend

        Returns:
            LLM response text
        """
        # Check rate limit
        if not await self.rate_limiter.acquire():
            wait_time = self.rate_limiter.get_wait_time()
            return f"Error: Rate limit exceeded. Please wait {wait_time:.1f} seconds."

        provider = provider or self.default
        conf = self.config.providers.get(provider)

        if not conf:
            return f"Error: Provider '{provider}' not configured"

        # Build full prompt with context
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        model = model or conf.model
        base_url = conf.base_url

        try:
            if provider == "grok":
                return await self._query_grok(base_url, model, full_prompt)
            elif provider == "openai":
                return await self._query_openai(base_url, model, full_prompt)
            elif provider == "claude":
                return await self._query_claude(base_url, model, full_prompt)
            elif provider == "ollama":
                return await self._query_ollama(base_url, model, full_prompt)
            else:
                return f"Error: Provider '{provider}' not implemented"
        except asyncio.TimeoutError:
            logger.error(f"{provider} request timed out")
            return f"Error: {provider} request timed out after 60 seconds"
        except Exception as e:
            logger.error(f"{provider} query failed: {e}", exc_info=True)
            return f"Error: {provider} query failed: {str(e)}"

    async def _query_grok(self, base_url: str, model: str, prompt: str) -> str:
        """Query Grok (X.AI) API."""
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            return "Error: XAI_API_KEY environment variable not set"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{base_url}/chat/completions",
                json=data,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return f"Grok API Error {response.status}: {error_text}"

                result = await response.json()
                return result['choices'][0]['message']['content']

    async def _query_openai(self, base_url: str, model: str, prompt: str) -> str:
        """Query OpenAI API."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Error: OPENAI_API_KEY environment variable not set"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{base_url}/chat/completions",
                json=data,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return f"OpenAI API Error {response.status}: {error_text}"

                result = await response.json()
                return result['choices'][0]['message']['content']

    async def _query_claude(self, base_url: str, model: str, prompt: str) -> str:
        """Query Claude (Anthropic) API."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "Error: ANTHROPIC_API_KEY environment variable not set"

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{base_url}/messages",
                json=data,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return f"Claude API Error {response.status}: {error_text}"

                result = await response.json()
                # Claude API returns content in a different format
                return result['content'][0]['text']

    async def _query_ollama(self, base_url: str, model: str, prompt: str) -> str:
        """Query Ollama (local) API."""
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{base_url}/chat/completions",
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"Ollama API Error {response.status}: {error_text}"

                    result = await response.json()
                    return result['choices'][0]['message']['content']
        except aiohttp.ClientConnectorError:
            return "Error: Cannot connect to Ollama. Ensure Ollama is running at http://localhost:11434"


# ==================== FILE WATCHER ====================

class FileChangeHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, callback: Callable[[str, str], None]):
        """
        Initialize handler.

        Args:
            callback: Function to call on file changes (event_type, path)
        """
        super().__init__()
        self.callback = callback

    def on_modified(self, event):
        """Handle file modification."""
        if not event.is_directory:
            self.callback('modified', event.src_path)

    def on_created(self, event):
        """Handle file creation."""
        if not event.is_directory:
            self.callback('created', event.src_path)

    def on_deleted(self, event):
        """Handle file deletion."""
        if not event.is_directory:
            self.callback('deleted', event.src_path)


# ==================== MAIN SERVER ====================

class FGDMCPServer:
    """Main MCP server with production-ready features."""

    def __init__(self, config_path: str):
        """
        Initialize MCP server.

        Args:
            config_path: Path to YAML configuration file
        """
        # Load and validate config
        with open(config_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        self.config = ServerConfig(**config_dict)
        self.watch_dir = Path(self.config.watch_dir).resolve()

        # Initialize components
        self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
        self.memory = MemoryStore(
            self.watch_dir / self.config.memory_file,
            self.config
        )
        self.llm = LLMBackend(self.config, self.rate_limiter)
        self.recent_changes: List[Dict[str, Any]] = []
        self.observer: Optional[Observer] = None

        # Setup logging
        self.log_file = self._resolve_log_file()
        self._ensure_log_handler()
        logger.info(f"FGD MCP Server initialized - Logging to {self.log_file}")
        logger.info(f"Watching directory: {self.watch_dir}")
        logger.info(f"Default LLM provider: {self.config.llm.default_provider}")

        # Start file watcher
        self._start_watcher()

        # Initialize MCP server
        self.server = Server("fgd-mcp-server")
        self._setup_handlers()

        # Setup shutdown handlers
        self._setup_shutdown_handlers()

    def _resolve_log_file(self) -> Path:
        """
        Resolve log file path.

        Returns:
            Absolute path to log file
        """
        configured = self.config.log_file
        candidate = Path(configured)

        if not candidate.is_absolute():
            candidate = (self.watch_dir / candidate).resolve()

        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def _ensure_log_handler(self) -> None:
        """Ensure file logging handler is configured."""
        # Check if handler already exists
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                if Path(handler.baseFilename) == self.log_file:
                    return

        # Add file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)

    def _start_watcher(self) -> None:
        """Start file system watcher."""
        try:
            handler = FileChangeHandler(self._on_file_change)
            self.observer = Observer()
            self.observer.schedule(handler, str(self.watch_dir), recursive=True)
            self.observer.start()
            logger.info("File watcher started successfully")
        except Exception as e:
            logger.warning(f"File watcher failed to start: {e}")
            self.observer = None

    def _on_file_change(self, event_type: str, path: str) -> None:
        """
        Handle file system change events.

        Args:
            event_type: Type of event (created, modified, deleted)
            path: Absolute path to changed file
        """
        try:
            path_obj = Path(path)
            rel_path = str(path_obj.relative_to(self.watch_dir))

            change_record = {
                "type": event_type,
                "path": rel_path,
                "timestamp": datetime.now().isoformat()
            }

            self.recent_changes.append(change_record)

            # Keep only last 50 changes
            if len(self.recent_changes) > 50:
                self.recent_changes = self.recent_changes[-50:]

            # Add to context
            self.memory.add_context("file_change", {
                "type": event_type,
                "path": rel_path
            })

            logger.debug(f"File {event_type}: {rel_path}")
        except ValueError:
            # Path is outside watch directory, ignore
            pass
        except Exception as e:
            logger.error(f"Error processing file change: {e}")

    def _sanitize_path(self, relative_path: str) -> Path:
        """
        Sanitize and validate a relative path.

        Args:
            relative_path: User-provided relative path

        Returns:
            Validated absolute Path object

        Raises:
            ValueError: If path is invalid or outside watch directory
        """
        # Normalize the path to prevent traversal attacks
        normalized = os.path.normpath(relative_path)

        # Check for path traversal attempts
        if normalized.startswith('..') or os.path.isabs(normalized):
            raise ValueError(
                f"Invalid path '{relative_path}': "
                "Path must be relative and within watch directory"
            )

        # Resolve full path
        full_path = (self.watch_dir / normalized).resolve()

        # Ensure path is within watch directory
        try:
            full_path.relative_to(self.watch_dir)
        except ValueError:
            raise ValueError(
                f"Path traversal blocked: '{relative_path}' "
                f"resolves outside watch directory"
            )

        return full_path

    def _setup_shutdown_handlers(self) -> None:
        """Setup graceful shutdown signal handlers."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _setup_handlers(self) -> None:
        """Setup MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available MCP tools."""
            return [
                Tool(
                    name="read_file",
                    description="Read contents of a file in the watched directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Relative path to file"
                            }
                        },
                        "required": ["filepath"],
                    },
                ),
                Tool(
                    name="list_files",
                    description="List files matching a glob pattern",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern (e.g., '**/*.py')",
                                "default": "**/*"
                            }
                        },
                    },
                ),
                Tool(
                    name="search_in_files",
                    description="Search for text across files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Text to search for"
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern for files to search",
                                "default": "**/*"
                            }
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="llm_query",
                    description="Query an LLM with automatic context injection (defaults to Grok)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Prompt for the LLM"
                            },
                            "provider": {
                                "type": "string",
                                "description": "LLM provider (grok, openai, claude, ollama)",
                                "default": "grok",
                                "enum": ["grok", "openai", "claude", "ollama"]
                            }
                        },
                        "required": ["prompt"],
                    },
                ),
                Tool(
                    name="remember",
                    description="Store information in persistent memory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "Memory key"
                            },
                            "value": {
                                "type": "string",
                                "description": "Memory value"
                            },
                            "category": {
                                "type": "string",
                                "description": "Memory category",
                                "default": "general"
                            }
                        },
                        "required": ["key", "value"],
                    },
                ),
                Tool(
                    name="recall",
                    description="Retrieve stored memories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "Specific memory key (optional)"
                            },
                            "category": {
                                "type": "string",
                                "description": "Memory category (optional)"
                            }
                        },
                    },
                ),
                Tool(
                    name="get_recent_changes",
                    description="Get list of recent file changes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "Number of changes to return",
                                "default": 10
                            }
                        },
                    },
                ),
            ]

        async def handle_read_file(args: Dict[str, Any]) -> List[TextContent]:
            """Handle read_file tool."""
            try:
                filepath = args.get("filepath")
                if not filepath:
                    return [TextContent(
                        type="text",
                        text="Error: Missing required argument 'filepath'"
                    )]

                path = self._sanitize_path(filepath)

                if not path.exists():
                    return [TextContent(
                        type="text",
                        text=f"Error: File not found: {filepath}"
                    )]

                if not path.is_file():
                    return [TextContent(
                        type="text",
                        text=f"Error: Path is not a file: {filepath}"
                    )]

                # Check file size
                max_bytes = self.config.scan.max_file_size_kb * 1024
                file_size = path.stat().st_size

                if file_size > max_bytes:
                    return [TextContent(
                        type="text",
                        text=f"Error: File too large ({file_size} bytes, limit {max_bytes} bytes)"
                    )]

                # Read file
                content = path.read_text(encoding='utf-8')
                self.memory.add_context("file_read", {"path": filepath})

                return [TextContent(type="text", text=content)]

            except ValueError as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            except UnicodeDecodeError:
                return [TextContent(
                    type="text",
                    text=f"Error: File is not valid UTF-8 text: {filepath}"
                )]
            except IOError as e:
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to read file '{filepath}': {str(e)}"
                )]
            except Exception as e:
                logger.error(f"Unexpected error in read_file: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: Unexpected error reading file: {str(e)}"
                )]

        async def handle_list_files(args: Dict[str, Any]) -> List[TextContent]:
            """Handle list_files tool."""
            try:
                pattern = args.get("pattern", "**/*")
                max_files = self.config.scan.max_files_per_scan

                files = []
                for path in self.watch_dir.glob(pattern):
                    if not path.is_file():
                        continue

                    try:
                        rel_path = path.relative_to(self.watch_dir)
                        files.append(str(rel_path))
                    except ValueError:
                        # Path outside watch directory, skip
                        continue

                    if len(files) >= max_files:
                        break

                result = {
                    "files": files,
                    "count": len(files),
                    "truncated": len(files) >= max_files
                }

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            except Exception as e:
                logger.error(f"Error in list_files: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to list files: {str(e)}"
                )]

        async def handle_search_in_files(args: Dict[str, Any]) -> List[TextContent]:
            """Handle search_in_files tool."""
            try:
                query = args.get("query")
                if not query:
                    return [TextContent(
                        type="text",
                        text="Error: Missing required argument 'query'"
                    )]

                pattern = args.get("pattern", "**/*")
                max_files = self.config.scan.max_files_per_scan
                max_bytes = self.config.scan.max_file_size_kb * 1024

                matches = []
                files_searched = 0

                for path in self.watch_dir.glob(pattern):
                    if files_searched >= max_files:
                        break

                    if not path.is_file():
                        continue

                    try:
                        # Skip files that are too large
                        if path.stat().st_size > max_bytes:
                            continue

                        content = path.read_text(encoding='utf-8').lower()
                        if query.lower() in content:
                            rel_path = path.relative_to(self.watch_dir)
                            matches.append({"filepath": str(rel_path)})

                        files_searched += 1

                    except (UnicodeDecodeError, IOError):
                        # Skip files that can't be read
                        continue
                    except ValueError:
                        # Path outside watch directory
                        continue

                result = {
                    "query": query,
                    "matches": matches,
                    "files_searched": files_searched,
                    "truncated": files_searched >= max_files
                }

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            except Exception as e:
                logger.error(f"Error in search_in_files: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to search files: {str(e)}"
                )]

        async def handle_llm_query(args: Dict[str, Any]) -> List[TextContent]:
            """Handle llm_query tool."""
            try:
                prompt = args.get("prompt")
                if not prompt:
                    return [TextContent(
                        type="text",
                        text="Error: Missing required argument 'prompt'"
                    )]

                # Default to grok for reliability
                provider = args.get("provider", "grok")

                # Get recent context
                context = json.dumps(self.memory.get_context(5), indent=2)

                # Query LLM
                response = await self.llm.query(prompt, provider, context=context)

                # Store response in memory
                timestamp = datetime.now().isoformat()
                self.memory.remember(
                    f"{provider}_{timestamp}",
                    response,
                    "llm"
                )

                return [TextContent(type="text", text=response)]

            except Exception as e:
                logger.error(f"Error in llm_query: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: LLM query failed: {str(e)}"
                )]

        async def handle_remember(args: Dict[str, Any]) -> List[TextContent]:
            """Handle remember tool."""
            try:
                key = args.get("key")
                value = args.get("value")

                if not key or value is None:
                    return [TextContent(
                        type="text",
                        text="Error: Missing required arguments 'key' or 'value'"
                    )]

                category = args.get("category", "general")
                self.memory.remember(key, value, category)

                return [TextContent(
                    type="text",
                    text=f"Successfully stored memory: category={category}, key={key}"
                )]

            except Exception as e:
                logger.error(f"Error in remember: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to store memory: {str(e)}"
                )]

        async def handle_recall(args: Dict[str, Any]) -> List[TextContent]:
            """Handle recall tool."""
            try:
                key = args.get("key")
                category = args.get("category")

                data = self.memory.recall(key, category)

                return [TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            except Exception as e:
                logger.error(f"Error in recall: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to recall memory: {str(e)}"
                )]

        async def handle_get_recent_changes(args: Dict[str, Any]) -> List[TextContent]:
            """Handle get_recent_changes tool."""
            try:
                count = args.get("count", 10)
                changes = self.recent_changes[-count:] if self.recent_changes else []

                result = {
                    "changes": changes,
                    "count": len(changes)
                }

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            except Exception as e:
                logger.error(f"Error in get_recent_changes: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to get recent changes: {str(e)}"
                )]

        # Register tool handlers
        tool_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[List[TextContent]]]] = {
            "read_file": handle_read_file,
            "list_files": handle_list_files,
            "search_in_files": handle_search_in_files,
            "llm_query": handle_llm_query,
            "remember": handle_remember,
            "recall": handle_recall,
            "get_recent_changes": handle_get_recent_changes,
        }

        @self.server.call_tool()
        async def handle_tool_call(
            tool_name: str,
            arguments: Optional[Dict[str, Any]]
        ) -> List[TextContent]:
            """Route tool calls to appropriate handlers."""
            handler = tool_handlers.get(tool_name)

            if not handler:
                return [TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{tool_name}'"
                )]

            return await handler(arguments or {})

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("MCP Server starting...")
        try:
            async with stdio_server() as (read, write):
                await self.server.run(
                    read,
                    write,
                    self.server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the server and cleanup resources."""
        logger.info("Shutting down MCP server...")

        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping file watcher: {e}")
            finally:
                self.observer = None

        logger.info("MCP server stopped")


# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "fgd_config.yaml"

    try:
        server = FGDMCPServer(config_path)
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
