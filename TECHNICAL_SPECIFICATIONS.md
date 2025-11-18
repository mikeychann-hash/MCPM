# MCPM Task Integration - Technical Specifications

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ PyQt6 GUI        │  │ FastAPI REST API │  │ CLI Bridge   │  │
│  │ (gui_main_pro)   │  │ (server.py)      │  │ (claude_     │  │
│  │                  │  │                  │  │  bridge.py)  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────┘  │
└───────────┼──────────────────────┼──────────────────────┼────────┘
            │                      │                      │
            └──────────────────────┼──────────────────────┘
                                   │
                    ┌──────────────▼─────────────┐
                    │  PROTOCOL LAYER            │
                    │  JSON-RPC 2.0 / MCP 2.0    │
                    │  (mcp.server)              │
                    └──────────────┬─────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────┐
│                    MCP SERVER LAYER                             │
│                  (FGDMCPServer in mcp_backend.py)               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  TOOL REGISTRY (via @decorators)                    │    │
│  │  ┌────────────────────────────────────────────────┐ │    │
│  │  │ @self.server.list_tools()                      │ │    │
│  │  │ async def list_tools(): -> List[Tool]          │ │    │
│  │  └────────────────────────────────────────────────┘ │    │
│  │  ┌────────────────────────────────────────────────┐ │    │
│  │  │ @self.server.call_tool()                       │ │    │
│  │  │ async def call_tool(name, arguments)           │ │    │
│  │  │   -> List[TextContent]                         │ │    │
│  │  └────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  TOOL DISPATCHER (Single Entry Point)                       │
│  ├─ if name == "list_directory" -> 900-958                 │
│  ├─ if name == "read_file" -> 960-976                      │
│  ├─ if name == "write_file" -> 978-1043                    │
│  ├─ if name == "edit_file" -> 1045-1120                    │
│  ├─ if name == "git_diff" -> 1122-1141                     │
│  ├─ if name == "git_commit" -> 1143-1179                   │
│  ├─ if name == "git_log" -> 1181-1199                      │
│  ├─ if name == "create_directory" -> 1202-1229             │
│  └─ if name == "llm_query" -> 1231-1270                    │
│                                                               │
│  ┌─────────────────┬──────────────┬────────────────────┐   │
│  │  MEMORY STORE   │ FILE WATCHER │ LLM BACKEND        │   │
│  │ (MemoryStore)   │ (Watchdog)   │ (LLMBackend)       │   │
│  ├─────────────────┼──────────────┼────────────────────┤   │
│  │ • LRU Pruning   │ • Monitor FS │ • Grok (X.AI)      │   │
│  │ • File Locking  │ • Change     │ • OpenAI           │   │
│  │ • Atomic Writes │   Detection  │ • Claude           │   │
│  │ • Access Count  │ • Context    │ • Ollama           │   │
│  │ • Categories    │   Updates    │ • Retry Logic      │   │
│  │ • Persistence   │ • Approval   │ • Timeout Config   │   │
│  └─────────────────┴──────────────┴────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
            │                    │                │
            ▼                    ▼                ▼
    ┌──────────────┐     ┌──────────────┐  ┌──────────────┐
    │ FILE SYSTEM  │     │ GIT REPO     │  │ LLM APIs     │
    │ (watch_dir)  │     │ (.git)       │  │ (async HTTP) │
    └──────────────┘     └──────────────┘  └──────────────┘
```

## Tool Execution Flow

```
CLIENT REQUEST (JSON-RPC 2.0)
    │
    ▼
MCP Library Validation
    │
    ├─ JSON Schema Validation ✅
    ├─ Method Routing ✅
    └─ Parameter Type Checking ✅
    │
    ▼
FGDMCPServer.call_tool(name, arguments)
    │
    ├─ Input Validation
    │  ├─ Path Sanitization (../../../ traversal check)
    │  ├─ Size Limits (250KB for files)
    │  ├─ Directory Checks (exists? is_dir?)
    │  └─ Git Repo Checks (if git_* tools)
    │
    ├─ Tool Execution (1 of 9)
    │  ├─ List Directory
    │  │  ├─ Apply gitignore patterns
    │  │  ├─ Filter hidden files
    │  │  └─ Return metadata
    │  │
    │  ├─ Read File
    │  │  ├─ Check size limit
    │  │  ├─ Read content
    │  │  └─ Add memory context
    │  │
    │  ├─ Write File
    │  │  ├─ Create parent dirs
    │  │  ├─ Make backup
    │  │  ├─ Write atomically (temp + rename)
    │  │  ├─ Verify content
    │  │  └─ Add memory context
    │  │
    │  ├─ Edit File (2-step)
    │  │  ├─ Preview mode (unsaved)
    │  │  │  └─ Save pending edit file
    │  │  │
    │  │  └─ Apply mode (confirmed)
    │  │     ├─ Create backup
    │  │     ├─ Apply change
    │  │     └─ Cleanup pending
    │  │
    │  ├─ Git Diff
    │  │  ├─ Check git availability
    │  │  └─ Run subprocess (timeout: 30s)
    │  │
    │  ├─ Git Commit
    │  │  ├─ Validate message non-empty
    │  │  ├─ git add .
    │  │  ├─ git commit -m
    │  │  └─ Save to memory
    │  │
    │  ├─ Git Log
    │  │  └─ git log -N --oneline
    │  │
    │  ├─ Create Directory
    │  │  └─ mkdir -p (idempotent)
    │  │
    │  └─ LLM Query
    │     ├─ Inject context (MCP status + recent activity)
    │     ├─ Call configured provider
    │     │  ├─ Grok: POST {base_url}/chat/completions
    │     │  ├─ OpenAI: POST {base_url}/chat/completions
    │     │  ├─ Claude: POST {base_url}/messages
    │     │  └─ Ollama: POST {base_url}/chat/completions
    │     ├─ Retry with backoff (3x: 2s, 4s, 8s)
    │     ├─ Per-provider timeout (default 30s)
    │     └─ Save to memory (UUID key)
    │
    ├─ Output Validation
    │  ├─ Format: List[TextContent]
    │  ├─ Size validation
    │  └─ Error message validation
    │
    └─ Memory Update
       ├─ Add context event
       ├─ Save conversation
       └─ Prune if needed

Response: List[TextContent]
    │
    ▼
MCP Library → JSON-RPC Response
    │
    ▼
CLIENT (GUI / API / CLI)
```

## Configuration Loading Sequence

```
1. FGDMCPServer.__init__(config_path)
   ├─ Load YAML config
   │  └─ config.example.yaml or custom path
   │
   ├─ Validate paths
   │  ├─ watch_dir must exist and be directory
   │  ├─ No Windows paths on non-Windows OS
   │  └─ Directory must be readable & writable
   │
   ├─ Prepare watch_dir
   │  ├─ Create if doesn't exist
   │  └─ Check permissions
   │
   ├─ Initialize MemoryStore
   │  ├─ Load .fgd_memory.json
   │  ├─ Set context_limit (default: 20)
   │  ├─ Set max_memory_entries (default: 1000)
   │  └─ Prune on startup
   │
   ├─ Initialize LLMBackend
   │  ├─ Load provider configs
   │  ├─ Set default_provider (from config)
   │  └─ Normalize bad configs at runtime:
   │     ├─ grok-beta → grok-3
   │     └─ Missing model/base_url → defaults
   │
   ├─ Load environment variables
   │  ├─ XAI_API_KEY (for Grok)
   │  ├─ OPENAI_API_KEY (for OpenAI)
   │  └─ ANTHROPIC_API_KEY (for Claude)
   │
   └─ Setup handlers
      ├─ Register list_tools()
      └─ Register call_tool() dispatcher

2. FGDMCPServer.run()
   ├─ Validate Grok API key if default
   ├─ Start file watcher
   ├─ Start approval monitor background task
   ├─ Connect to MCP protocol
   │  └─ stdio_server() for pipe communication
   │
   └─ Handle JSON-RPC messages until shutdown
```

## Memory Storage Format

```json
{
  "memories": {
    "conversations": {
      "chat_550e8400-e29b-41d4-a716-446655440000": {
        "value": {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "prompt": "Explain this code",
          "response": "This code...",
          "provider": "grok",
          "timestamp": "2025-11-18T10:30:00.123456",
          "context_used": 5
        },
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 3
      }
    },
    "llm": {
      "grok_2025-11-18T10:30:00.123456": {
        "value": "This code implements...",
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 1
      }
    },
    "git_diffs": {
      "diff_2025-11-18T10:30:00.123456": {
        "value": "--- a/file.txt\n+++ b/file.txt\n@@ -1,3 +1,3 @@...",
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 1
      }
    },
    "commits": {
      "commit_a1b2c3d": {
        "value": "Fix: Handle missing paths",
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 2
      }
    },
    "file_change": {
      "change_1": {
        "value": {"type": "modified", "path": "src/main.py"},
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 1
      }
    },
    "file_read": {
      "read_file_path": {
        "value": {
          "path": "src/main.py",
          "meta": {"size_kb": 12.5, "modified": "...", "lines": 234}
        },
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 8
      }
    },
    "file_write": {
      "write_file_path": {
        "value": {
          "path": "src/config.py",
          "resolved_path": "/full/path/src/config.py",
          "size": 3456,
          "verified": true
        },
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 1
      }
    },
    "backup": {
      "backup_1": {
        "value": {
          "path": "/full/path/src/config.py.bak",
          "original": "src/config.py"
        },
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 1
      }
    },
    "file_edit": {
      "edit_1": {
        "value": {
          "path": "src/main.py",
          "approved": true,
          "resolved_path": "/full/path/src/main.py"
        },
        "timestamp": "2025-11-18T10:30:00.123456",
        "access_count": 1
      }
    }
  },
  "context": [
    {
      "type": "file_change",
      "data": {"type": "modified", "path": "src/main.py"},
      "timestamp": "2025-11-18T10:30:00.123456"
    },
    {
      "type": "file_read",
      "data": {"path": "src/config.py", "meta": {...}},
      "timestamp": "2025-11-18T10:30:01.234567"
    }
  ]
}
```

## LRU Pruning Algorithm

```python
def _prune_if_needed(self):
    """
    Implements LRU pruning when memory exceeds limit.
    
    Step 1: Count total entries across all categories
    Step 2: If under limit, return early
    Step 3: Collect all entries with metadata
    Step 4: Sort by (access_count, timestamp) ascending
           - Entries with lower access_count first
           - Among same access_count, older ones first
    Step 5: Remove entries until under limit
    Step 6: Cleanup empty categories
    
    Time Complexity: O(n log n) where n = total entries
    Space Complexity: O(n)
    
    Triggers: On startup, before save
    Max Entries: 1000 (configurable)
    """
```

## JSON-RPC Request/Response Examples

### Request Format
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {
      "filepath": "README.md"
    }
  },
  "id": 1
}
```

### Success Response
```json
{
  "jsonrpc": "2.0",
  "result": [
    {
      "type": "text",
      "text": "{\"content\": \"# Project\\n...\", \"meta\": {\"size_kb\": 12.5, \"modified\": \"2025-11-18T10:30:00\", \"lines\": 150}}"
    }
  ],
  "id": 1
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "detail": "filepath is required"
    }
  },
  "id": 1
}
```

## Async Execution Model

```
┌─────────────────────────────────────────────────────┐
│ Main Event Loop (asyncio.run)                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Task 1: MCP Server (stdio_server)                 │
│  ├─ Listen for JSON-RPC messages                   │
│  ├─ Parse and validate                             │
│  ├─ Dispatch to tool handler                       │
│  └─ Send response (non-blocking)                   │
│     │                                              │
│     ├─ await file I/O                             │
│     ├─ await subprocess calls                     │
│     ├─ await HTTP requests (LLM APIs)             │
│     └─ await memory operations                    │
│                                                     │
│  Task 2: Approval Monitor (background)             │
│  ├─ Every 2 seconds:                               │
│  │  ├─ Check for .fgd_approval.json               │
│  │  ├─ Read approval status                        │
│  │  └─ Apply edits if approved                     │
│  │                                                 │
│  └─ Handle cancellation gracefully                 │
│                                                     │
│  Task 3: File Watcher (background)                │
│  ├─ Monitor watch_dir for changes                 │
│  ├─ Capture events (create, modify, delete)       │
│  └─ Add to context (non-blocking)                 │
│                                                     │
└─────────────────────────────────────────────────────┘

Concurrency Model:
- All handlers are async (can yield control)
- Multiple tools can execute concurrently
- I/O operations never block event loop
- Memory updates are atomic (FileLock)
```

## Error Handling Hierarchy

```
1. Validation Layer
   ├─ JSON Schema Validation (MCP library)
   └─ Parameter Type Checking

2. Path Validation Layer
   ├─ Path traversal prevention
   ├─ Directory existence checks
   └─ Permission validation

3. Execution Layer
   ├─ File system errors (caught as OSError)
   ├─ Git availability errors
   └─ LLM API errors (with retry)

4. Output Layer
   ├─ Content verification
   ├─ Size validation
   └─ Format validation

Error Response Format:
TextContent(type="text", text="Error: <message>")

Special Cases:
- Silent failures converted to exceptions (P0-FIX)
- Detailed context provided for debugging
- Stack traces logged but not sent to client
```

## Tool Registration Pattern

```python
# 1. Define tool in list_tools()
Tool(
    name="tool_name",
    description="What it does",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
            "param2": {"type": "integer", "default": 5}
        },
        "required": ["param1"]  # param2 is optional
    }
)

# 2. Implement handler in call_tool()
if name == "tool_name":
    param1 = arguments["param1"]
    param2 = arguments.get("param2", 5)  # Use default if not provided
    
    # Implementation
    result = do_something(param1, param2)
    
    # Return as TextContent
    return [TextContent(type="text", text=result)]

# 3. Tool is automatically discoverable via MCP protocol
```

## File Locking Pattern

```python
with FileLock(file_path, timeout=10):
    # This block has exclusive access to file_path
    # Works on Windows (msvcrt) and Unix (fcntl)
    # Timeout prevents deadlocks
    # Raises TimeoutError if lock unavailable
    
    data = json.loads(file_path.read_text())
    data['key'] = 'value'
    file_path.write_text(json.dumps(data))
    # Lock automatically released on exit
```

## Atomic Write Pattern

```python
# Current (SAFE):
temp_file = path.with_suffix('.tmp')
temp_file.write_text(content)  # Write to temp first
temp_file.replace(path)         # Atomic rename
# If crash happens during rename, temp file remains
# (allows recovery, not corrupted original)

# Advantages:
- If write interrupted, original file intact
- No partial writes to original file
- Cross-platform (Windows + Unix)
```

## Caching Strategy Recommendation

```python
# IMPLEMENTED: Memory Store LRU Cache
- Per-memory-entry access count tracking
- Automatic pruning when exceeding limit
- Timestamp-based aging
- Bounded memory growth

# RECOMMENDED: Tool Response Cache
Cache Layer:
├─ gitignore_patterns_cache
│  ├─ Key: watch_dir path
│  ├─ TTL: 5 minutes
│  └─ Invalidate: on list_directory or edit_file
│
├─ directory_listing_cache
│  ├─ Key: directory path
│  ├─ TTL: 2 seconds
│  └─ Invalidate: on any file change event
│
└─ git_status_cache
   ├─ Key: watch_dir
   ├─ TTL: 1 second
   └─ Invalidate: on write_file or edit_file
```

## Retry Logic with Exponential Backoff

```python
# Configuration:
- Max retries: 3
- Initial delay: 2 seconds
- Backoff multiplier: 2

# Delays:
Attempt 1: immediate
Attempt 2: wait 2s, then retry
Attempt 3: wait 4s, then retry
Attempt 4: wait 8s, then retry (final attempt)
Attempt 5+: give up, raise error

# Retries apply to:
- Grok API calls
- OpenAI API calls
- Claude API calls
- Ollama API calls
- NOT applied to: subprocess calls, file I/O
```

## Performance Characteristics

```
Tool                    Avg Time    P95 Time    P99 Time    Bottleneck
─────────────────────────────────────────────────────────────────────
list_directory         5-50ms      100ms       500ms       Disk I/O
read_file              1-10ms      50ms        200ms       File size
write_file             10-100ms    200ms       500ms       Disk sync
edit_file (preview)    5-50ms      100ms       200ms       JSON parsing
edit_file (apply)      10-100ms    200ms       500ms       Atomic rename
git_diff               50-500ms    1s          2s          Subprocess
git_commit             100-500ms   1s          2s          Subprocess
git_log                50-200ms    500ms       1s          Subprocess
llm_query              500ms-5s    10s         30s         Network I/O

Caching Impact (if implemented):
- Repeated list_directory: 50x faster (cache hit)
- Repeated gitignore parse: 100x faster
- Directory listing: 20x faster with incremental updates
```

