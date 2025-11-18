# MCPM Task Registration & Integration Analysis Report

## Executive Summary

The MCPM repository is a **Python-only** Model Context Protocol (MCP) server implementation with **no Node.js/JavaScript components**. The task registration system is centralized in `mcp_backend.py` using the MCP library's Python bindings.

### Key Findings:
- **Total Built-in Tasks**: 9 tools (not 4)
- **Registration Pattern**: Decorator-based (@server.list_tools(), @server.call_tool())
- **JSON-RPC Compliance**: ✅ Full MCP 2.0 support via mcp library
- **Auto-discovery**: ❌ No plugin system (static tools only)
- **Caching**: ✅ LRU memory pruning with access tracking
- **Parallel Execution**: ✅ Full asyncio support
- **Performance Optimization**: ✅ Implemented (P0-P2 fixes)

---

## 1. TASK REGISTRATION ARCHITECTURE

### 1.1 Registration Mechanism (Python)

**Location**: `/home/user/MCPM/mcp_backend.py` (lines 857-893)

**Registration Pattern**:
```python
@self.server.list_tools()
async def list_tools():
    return [
        Tool(name="...", description="...", inputSchema={...}),
        ...
    ]

@self.server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle all tool calls with a dispatcher pattern"""
    if name == "tool_name":
        # Tool implementation
    ...
```

**Key Architecture Points**:
- Centralized registration in `FGDMCPServer.__init__()` and `_setup_handlers()`
- Decorator-based registration using MCP library decorators
- Single dispatcher function for all tools (pattern matching on name)
- No separate configuration files for task definitions
- Tasks are hardcoded in the server implementation

### 1.2 Server Initialization Flow

1. **FGDMCPServer.__init__()** (line 514-546):
   - Loads config from YAML
   - Initializes memory store (MemoryStore)
   - Initializes LLM backend (LLMBackend)
   - Calls `_setup_handlers()` to register tools

2. **_setup_handlers()** (line 856):
   - Registers tools via `@self.server.list_tools()`
   - Registers dispatcher via `@self.server.call_tool()`

3. **run()** (line 1276-1348):
   - Starts approval monitor task
   - Connects to MCP protocol handler
   - Handles JSON-RPC validation errors

---

## 2. COMPLETE LIST OF AVAILABLE TASKS/TOOLS

### Task Inventory Table

| # | Tool Name | Description | Input Schema | Output Format | Status |
|---|-----------|-------------|--------------|---------------|--------|
| 1 | **list_directory** | Browse files (gitignore aware) | `path: string` | JSON with file metadata | ✅ Active |
| 2 | **read_file** | Read file contents with metadata | `filepath: string` | JSON {content, meta} | ✅ Active |
| 3 | **write_file** | Write/create files with backup | `filepath, content: strings` | TextContent with verification | ✅ Active |
| 4 | **edit_file** | Edit with diff preview & approval | `filepath, old_text, new_text, confirm: bool` | JSON with diff preview | ✅ Active |
| 5 | **git_diff** | Show uncommitted changes | `files: string[]` (optional) | Unified diff format | ✅ Active |
| 6 | **git_commit** | Commit to git | `message: string` | TextContent with commit hash | ✅ Active |
| 7 | **git_log** | View commit history | `limit: integer` | TextContent with log lines | ✅ Active |
| 8 | **llm_query** | Query LLM with context injection | `prompt: string` | TextContent with LLM response | ✅ Active |
| 9 | **create_directory** | Create directory with parents | `path: string` | TextContent with status (P2-FIX) | ✅ Active |

### Task Details by Category

#### File System Operations (4 tools)
1. **list_directory** (lines 900-958)
   - Path: relative to watch_dir
   - Features: gitignore filtering, hidden file filtering
   - Output: JSON with file count, filter counts
   - Errors: Non-existent path, permission denied

2. **read_file** (lines 960-976)
   - Max size: 250KB
   - Output: {content, meta: {size_kb, modified, lines}}
   - Memory context: Added to memory.context

3. **write_file** (lines 978-1043)
   - Parent directory auto-creation
   - Backup creation (.bak suffix)
   - Content verification
   - Atomic write pattern: temp file → rename
   - Memory context: Saved with resolved path

4. **create_directory** (lines 1202-1229) [P2-FIX]
   - Creates with parents (mkdir -p equivalent)
   - Idempotent (succeeds if exists as dir)

#### File Editing (1 tool)
5. **edit_file** (lines 1045-1120)
   - Two modes: preview (confirm=false) or apply (confirm=true)
   - Preview mode: Saves pending edit to `.fgd_pending_edit.json`
   - Apply mode: Creates backup, applies edit, cleans up pending file
   - Memory context: Tracks approved edits with resolved path

#### Git Operations (3 tools)
6. **git_diff** (lines 1122-1141)
   - Requires valid git repo
   - Uses subprocess with 30s timeout
   - Output: Unified diff or "No changes"
   - Memory: Stored as `diff_{timestamp}` in git_diffs category

7. **git_commit** (lines 1143-1179)
   - Message required (non-empty validation)
   - Auto-stages all changes (git add .)
   - Output: Commit hash + message
   - Memory: Stored as `commit_{hash}` in commits category

8. **git_log** (lines 1181-1199)
   - Limit parameter (default: 5)
   - Output: --oneline format
   - Uses: `git log -N --oneline`

#### LLM Integration (1 tool)
9. **llm_query** (lines 1231-1270)
   - Injects MCP status context
   - Adds recent activity context
   - Uses configured default provider
   - Output: Direct LLM response text
   - Memory: Stores as `chat_{uuid}` + `{provider}_{timestamp}`
   - UUID-based keys prevent timestamp collisions (P1-FIX)

---

## 3. AUTO-DISCOVERY & PLUGIN DETECTION MECHANISMS

### Current Status: ❌ **NOT IMPLEMENTED**

**Auto-Discovery Analysis**:
- **Tool registration**: Static, hardcoded in list_tools() function
- **Configuration loading**: YAML-based (config.example.yaml, fgd_config.yaml)
- **Plugin system**: Not present
- **Dynamic loading**: Not supported
- **Tool metadata discovery**: Manual via list_tools() decorator

### What EXISTS:
✅ LLM Provider Discovery (lines 275-309)
```python
# Dynamic configuration normalization for Grok provider
def _normalize_provider_config(self) -> None:
    """Patch known-bad legacy provider settings at runtime."""
    # Upgrades grok-beta → grok-3
    # Sets defaults for missing model/base_url
```

### What's MISSING:
- No filesystem scanning for plugins
- No dynamic tool registration
- No plugin interface/contracts
- No tool marketplace/repository
- No version management for tools

---

## 4. TASK MAPPING: NODE.JS ↔ PYTHON

### Finding: **NO NODE.JS IMPLEMENTATION**

**File Search Results**:
```
❌ No .js files found
❌ No .ts files found  
❌ No package.json found
✅ Python-only implementation
```

**Architecture**:
```
claude_bridge.py (CLI wrapper)
    ↓
subprocess call to python mcp_backend.py
    ↓
FGDMCPServer (Python MCP server)
    ↓
Tool execution
```

**Integration Points**:
- `claude_bridge.py` (lines 13-32): Subprocess wrapper
  - Calls `python mcp_backend.py --tool <tool_name>`
  - Maps CLI commands to tool calls
  - Returns stdout/stderr

- `server.py` (FastAPI wrapper):
  - REST API endpoints wrapping MCP server
  - No direct Node.js binding

---

## 5. JSON-RPC COMPLIANCE

### Compliance Status: ✅ **FULL MCP 2.0 COMPLIANCE**

**Implementation Details**:

1. **Protocol Support** (lines 1289-1310):
```python
async with stdio_server() as (read, write):
    await self.server.run(
        read, write, 
        self.server.create_initialization_options()
    )
```

2. **Error Handling** (lines 1295-1320):
```python
except ValidationError as e:
    # Pydantic validation errors from malformed JSON-RPC messages
    logger.error("JSON-RPC VALIDATION ERROR")
    
except json.JSONDecodeError as e:
    # JSON parsing errors
    logger.error("JSON DECODE ERROR")
```

3. **Tool Definition Schema** (lines 860-892):
- Follows JSON Schema Draft 7
- inputSchema required for all tools
- type: "object" for all tools
- properties: individual parameter definitions
- required: list of mandatory parameters

**Expected JSON-RPC Format**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {
      "filepath": "example.txt"
    }
  },
  "id": 1
}
```

**Response Format**:
```json
{
  "jsonrpc": "2.0",
  "result": [
    {
      "type": "text",
      "text": "file contents..."
    }
  ],
  "id": 1
}
```

---

## 6. TASK OUTPUT STRUCTURE & VALIDATION

### Output Format Standard

**All Tools Return**: `List[TextContent]` (line 46: `from mcp.types import Tool, TextContent`)

```python
TextContent(type="text", text="output string")
```

### Output Validation Mechanisms

#### 1. **File Write Verification** (lines 1003-1026)
```python
# P2-FIX (MCP-CONN): Comprehensive verification
if path.exists():
    size = path.stat().st_size
    # Verify content matches
    actual_content = path.read_text(encoding='utf-8')
    if actual_content == content:
        logger.info(f"✅ Write verified: {path.resolve()} ({size} bytes)")
    else:
        logger.error(f"❌ Write failed: Content mismatch")
```

#### 2. **Directory Listing Validation** (lines 906-912)
```python
# P2-FIX (MCP-CONN): Check if path exists before processing
if not path.exists():
    return [TextContent(type="text", text=f"Error: Directory does not exist")]
if not path.is_dir():
    return [TextContent(type="text", text=f"Error: Not a directory")]
```

#### 3. **Git Command Validation** (lines 1154-1162)
```python
# Check if there are changes to commit
status_result = subprocess.run(["git", "status", "--porcelain"])
if not status_result.stdout.strip():
    return [TextContent(type="text", text="No changes to commit")]
```

#### 4. **Size Limit Validation** (lines 964-965)
```python
if path.stat().st_size > self.max_file_kb:
    return [TextContent(type="text", text="Error: File too large (>250KB)")]
```

### Output Structure by Tool

| Tool | Output Type | Structure | Example |
|------|-------------|-----------|---------|
| list_directory | JSON | `{path, files[], file_count, filtered_count, ...}` | Lines 939-951 |
| read_file | JSON | `{content, meta: {size_kb, modified, lines}}` | Line 974 |
| write_file | TextContent | Multi-line summary | Lines 1016-1020 |
| edit_file | JSON | `{action, filepath, diff, preview, message}` | Lines 1083-1089 |
| git_diff | TextContent | Raw diff output | Line 1138 |
| git_commit | TextContent | "Committed: {hash}\n{message}" | Line 1173 |
| git_log | TextContent | Git oneline format | Line 1196 |
| llm_query | TextContent | Direct response text | Line 1270 |
| create_directory | TextContent | Status message | Lines 1214, 1222 |

---

## 7. TASK CONFIGURATION & METADATA

### Configuration Sources

#### 1. **YAML Configuration** (`config.example.yaml`)
```yaml
watch_dir: "./your-project-directory"
context_limit: 20
scan:
  max_dir_size_gb: 2
  max_files_per_scan: 5
  max_file_size_kb: 250
reference_dirs:
  - "/path/to/docs"
llm:
  default_provider: "grok"
  providers:
    grok:
      model: "grok-3"
      base_url: "https://api.x.ai/v1"
```

#### 2. **Environment Variables**
- `XAI_API_KEY`: Grok authentication
- `OPENAI_API_KEY`: OpenAI authentication
- `ANTHROPIC_API_KEY`: Claude authentication
- `API_HOST`, `API_PORT`: FastAPI server config
- `CORS_ORIGINS`: CORS policy

#### 3. **Memory Configuration** (lines 132-135)
```python
self.limit = config.get('context_limit', 20)
self.max_memory_entries = config.get('max_memory_entries', 1000)
```

#### 4. **Scan Limits** (lines 523-525)
```python
self.max_dir_size = self.scan.get('max_dir_size_gb', 2) * 1_073_741_824
self.max_files = self.scan.get('max_files_per_scan', 5)
self.max_file_kb = self.scan.get('max_file_size_kb', 250) * 1024
```

### Tool Input Schema Validation

**Example: edit_file** (lines 870-877)
```python
Tool(name="edit_file", description="Edit with diff preview", inputSchema={
    "type": "object", 
    "properties": {
        "filepath": {"type": "string"},
        "old_text": {"type": "string"},
        "new_text": {"type": "string"},
        "confirm": {"type": "boolean", "default": False}
    }, 
    "required": ["filepath", "old_text", "new_text"]
})
```

**Required vs Optional Parameters**:
- **Always required**: name, filepath (or path)
- **Optional with defaults**: 
  - `path` in list_directory (default: ".")
  - `limit` in git_log (default: 5)
  - `confirm` in edit_file (default: False)
  - `files` in git_diff (default: [])

---

## 8. CACHING, BATCHING & PARALLEL EXECUTION

### 8.1 Caching Mechanisms

#### **Memory Store LRU Cache** (lines 230-270)
```python
def _prune_if_needed(self):
    """Prune old memory entries if size exceeds limit (P2 FIX: MEMORY-5)."""
    # Implements LRU: least accessed and oldest entries removed first
    # Max entries: 1000 (configurable)
    # Tracks: access_count + timestamp
    
    all_entries.sort(key=lambda x: (x['access_count'], x['timestamp']))
    # Remove least recently used entries
```

**Features**:
- Access count tracking (line 210)
- Timestamp-based aging
- Automatic pruning on startup + before save
- Bounded memory growth

#### **No Built-in Tool Cache**
- Each tool call executes fresh (no caching)
- File read operations not cached
- Directory listings not cached

### 8.2 Batching Mechanisms

#### **Pending Edit Batching** (lines 1060-1089)
```python
if not confirm:
    # Save for later approval
    pending_edit_file = self._save_pending_edit(pending_edit_data)
    # User approves via GUI
    # Auto-apply monitor processes it (lines 626-691)
```

#### **No Task Batching**
- Tools execute individually
- No batch tool endpoint
- No transaction support

### 8.3 Parallel Execution

#### **Full Asyncio Support**
```python
# All handlers are async
@self.server.list_tools()
async def list_tools():

@self.server.call_tool()
async def call_tool(name: str, arguments: dict):

async def query(self, prompt, provider, context):

async def _approval_monitor_loop(self):
```

#### **Concurrent Operations**:
1. **Main server** (line 1294): MCP protocol handler
2. **Approval monitor** (line 1285): Background task checking for approvals
3. **LLM queries** (lines 427-498): Async HTTP requests with retry logic

#### **Timeouts & Backoff** (lines 382-396)
```python
async def _retry_request(self, func, max_retries=3, initial_delay=2):
    for attempt in range(max_retries):
        try:
            return await func()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            delay = initial_delay * (2 ** attempt)  # Exponential backoff
            await asyncio.sleep(delay)
```

**Retry Strategy**:
- Max retries: 3
- Initial delay: 2 seconds
- Backoff: 2s → 4s → 8s
- Applies to: Grok, OpenAI, Claude, Ollama

#### **Per-Provider Timeouts** (lines 408-410)
```python
timeout_seconds = conf.get('timeout', 30)  # Default 30s
timeout = aiohttp.ClientTimeout(total=timeout_seconds)
```

---

## 9. INTEGRATION ISSUES & MISALIGNMENTS

### P0 (Critical) Issues: ✅ FIXED

| Issue | Status | Fix |
|-------|--------|-----|
| Silent write failures | ✅ FIXED | Exceptions now raised (line 202) |
| Race conditions | ✅ FIXED | File locking (fcntl/msvcrt) with 10s timeout |
| Unsafe permissions | ✅ FIXED | 600 mode (owner read/write only) |
| Non-atomic writes | ✅ FIXED | Temp file + rename pattern |

### P1 (High) Issues: ✅ FIXED

| Issue | Status | Fix |
|-------|--------|-----|
| UUID chat key collisions | ✅ FIXED | UUID instead of timestamp (line 1253) |
| Hardcoded provider | ✅ FIXED | Uses configured default_provider (line 1247) |
| Memory leaks | ✅ FIXED | Timer cleanup in GUI |

### P2 (Medium) Opportunities

| Issue | Status | Impact | Difficulty |
|-------|--------|--------|------------|
| **No plugin system** | ❌ MISSING | Limited extensibility | Medium |
| **No tool caching** | ❌ MISSING | Redundant file reads | Low |
| **No batch endpoint** | ❌ MISSING | Can't execute multiple tools atomically | Medium |
| **No rate limiting on MCP** | ⚠️ PARTIAL | Only REST API has limits | Medium |
| **No tool deprecation** | ❌ MISSING | Hard to evolve tools | Medium |

### Detected Misalignments

#### 1. **File Path Validation** (RISK: Medium)
- **Issue**: watch_dir on Windows path checked on non-Windows OS (line 554-569)
- **Impact**: Fails fast with clear error
- **Status**: ✅ Handled correctly

#### 2. **Git Availability** (RISK: Low)
- **Issue**: git_* tools fail gracefully if git not installed
- **Impact**: Error messages provide context
- **Status**: ✅ Good error handling

#### 3. **LLM Provider Mismatch** (RISK: Medium)
- **Issue**: Provider config can be incomplete
- **Fix**: _normalize_provider_config() at lines 281-308
- **Status**: ✅ Fixed with runtime healing

---

## 10. OUTPUT VALIDATION & STRUCTURE COMPLIANCE

### Validation Coverage

#### **Input Validation**:
✅ filepath/path validation (path traversal prevention, line 716)
✅ File size validation (250KB limit, line 964)
✅ Directory existence checks (lines 906-912)
✅ Git repo validation (lines 766-788)
✅ Parameter type checking (JSON schema validation via mcp library)
⚠️ Partial: No deep schema validation for complex types

#### **Output Validation**:
✅ File write verification (content match, lines 1008-1009)
✅ Directory creation verification (line 1221)
✅ Git command success validation (lines 1161, 1168)
⚠️ Partial: No JSON schema validation on outputs
⚠️ Partial: No size limits on output TextContent

### Compliance Issues

| Aspect | Status | Severity | Example |
|--------|--------|----------|---------|
| **JSON-RPC envelope** | ✅ MCP lib handles | - | Handled by mcp.server |
| **Tool schema compliance** | ✅ Manual definition | - | Lines 860-892 |
| **Error response format** | ⚠️ Inconsistent | Low | Some tools return JSON, others text |
| **Content type consistency** | ⚠️ Mixed | Low | TextContent vs JSON strings |
| **Null value handling** | ⚠️ Not standardized | Low | Some tools may return None |

**Recommendation**: Standardize output structure:
```python
# Current (inconsistent):
TextContent(type="text", text="content")  # Some tools
TextContent(type="text", text=json.dumps({...}))  # Others

# Proposed (consistent):
TextContent(type="text", text=json.dumps({
    "success": bool,
    "data": Any,
    "error": Optional[str],
    "meta": Optional[dict]
}))
```

---

## 11. PERFORMANCE OPTIMIZATION OPPORTUNITIES

### Current Optimizations (Implemented)

| Optimization | Impact | Status |
|--------------|--------|--------|
| **Lazy tree loading** | 20-50x faster for 1000+ files | ✅ GUI |
| **Incremental log reading** | 95%+ CPU reduction | ✅ GUI |
| **Memory LRU pruning** | Bounded growth (max 1000 entries) | ✅ Backend |
| **Async execution** | Non-blocking I/O | ✅ Backend |
| **Retry with backoff** | Improved reliability | ✅ LLM |
| **Per-provider timeouts** | Customizable reliability | ✅ Config |

### P2 Opportunities

#### 1. **Tool Response Caching** (Medium Impact)
```python
@functools.lru_cache(maxsize=100)
def _get_gitignore_patterns(self, root: Path):
    # Currently recalculated every list_directory call
    # Cache patterns for 5 minutes
```
**Expected Benefit**: 2-3x faster directory listing for repeated operations

#### 2. **Directory Traversal Optimization** (Low Impact)
```python
# Current: path.iterdir() + filtering
# Proposed: Use os.scandir() + generator pattern
# Benefit: Lower memory for large directories
```

#### 3. **Parallel Git Operations** (Low Impact)
```python
# Current: Sequential subprocess calls
# Proposed: asyncio.gather() for independent git ops
# Benefit: Marginal (git I/O-bound, not CPU-bound)
```

#### 4. **Memory Serialization** (Medium Impact)
```python
# Current: JSON.dumps entire file on every save
# Proposed: Incremental writes + append-only log
# Benefit: Reduced disk I/O for large memory stores
```

#### 5. **LLM Response Streaming** (Medium Impact)
```python
# Current: Full response buffered then returned
# Proposed: Stream response chunks to client
# Benefit: Better UX for long responses
```

#### 6. **File Read Caching** (High Impact - if safe)
```python
# Current: No caching (always reads from disk)
# Proposed: TTL-based cache with file watcher invalidation
# Risk: Inconsistent state if file modified externally
# Status: NOT RECOMMENDED for this use case
```

---

## 12. RECOMMENDATIONS

### Immediate (P0) Actions
None - Critical issues already fixed.

### High Priority (P1) Actions

1. **Implement Tool Versioning** (Low effort, high value)
   - Add version field to Tool metadata
   - Deprecate old tool versions gracefully
   - Document breaking changes

2. **Standardize Output Format** (Medium effort, high value)
   - All tools return consistent JSON structure
   - Enables better client-side error handling
   - Improves API contract clarity

3. **Add Rate Limiting to MCP** (Medium effort, medium value)
   - Per-tool rate limits
   - Per-client token bucket
   - Prevents resource exhaustion

### Medium Priority (P2) Actions

1. **Plugin Architecture** (High effort, medium value)
   - Dynamic tool registration from modules
   - Tool marketplace/registry
   - Enables community extensions

2. **Tool Caching Layer** (Low-medium effort, high value)
   - Cache gitignore patterns
   - Cache directory listings (with TTL)
   - Improves performance for repeated operations

3. **Batch Tool Endpoint** (Medium effort, low-medium value)
   - Execute multiple tools in single RPC call
   - Atomic transactions for related operations
   - Reduces round-trips

4. **Output Schema Validation** (Medium effort, medium value)
   - Define JSON schema for each tool output
   - Validate before returning
   - Prevents silent data corruption

5. **Tool Instrumentation** (Low effort, medium value)
   - Execution time metrics per tool
   - Call frequency analytics
   - Performance bottleneck identification

### Documentation Improvements

1. **Tool Reference Guide**: Document each tool with examples
2. **Plugin Development Guide**: How to extend with custom tools
3. **Performance Tuning Guide**: Config optimization tips
4. **Troubleshooting Guide**: Common issues and solutions

---

## 13. SUMMARY TABLE

| Aspect | Status | Score | Notes |
|--------|--------|-------|-------|
| **Tool Count** | 9 available | 8/10 | Good coverage, no specialized tools |
| **Registration** | Centralized, static | 7/10 | Simple but not extensible |
| **JSON-RPC Compliance** | Full via MCP lib | 10/10 | Production-ready |
| **Error Handling** | Comprehensive | 9/10 | Good validation, some edge cases |
| **Output Validation** | Partial | 6/10 | Needs standardization |
| **Performance** | Good (optimized) | 8/10 | Memory & CPU optimized |
| **Caching** | Partial (memory only) | 6/10 | Could add tool caching |
| **Parallel Execution** | Full async | 9/10 | Excellent async support |
| **Documentation** | Good (README) | 7/10 | Could expand with examples |
| **Extensibility** | Limited (no plugins) | 4/10 | Major limitation |
| **Overall** | Production-Ready | **7.4/10** | Stable, needs plugin system |

