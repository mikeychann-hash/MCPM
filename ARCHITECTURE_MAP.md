# MCPM Architecture Map
## Model Context Protocol Manager v6.0

**Last Updated**: 2025-11-18
**Version**: 6.0.0
**Stack**: Python 3.10+ (Backend, GUI, MCP Server)

---

## Table of Contents
1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Diagram](#component-diagram)
4. [Communication Flow](#communication-flow)
5. [Data Flow](#data-flow)
6. [File Structure](#file-structure)
7. [Technology Stack](#technology-stack)
8. [Deployment Architecture](#deployment-architecture)

---

## System Overview

MCPM is a **Python-based Model Context Protocol (MCP) server** with three operational modes:

1. **GUI Mode** - PyQt6 desktop application with Neo Cyber design
2. **Stdio Mode** - MCP server communicating via stdin/stdout (JSON-RPC 2.0)
3. **REST API Mode** - FastAPI server on port 8456

### Key Features
- 9 built-in MCP tools (file operations, git, LLM integration)
- Multi-LLM support (Grok, OpenAI, Claude, Ollama)
- Real-time file watching and memory persistence
- 2-step approval workflow for file edits
- Cross-platform (Windows, Linux, macOS, Docker)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCPM SYSTEM v6.0                             │
│                                                                      │
│  ┌────────────────┐      ┌──────────────┐      ┌─────────────────┐ │
│  │   PyQt6 GUI    │      │  MCP Backend │      │  FastAPI Server │ │
│  │ gui_main_pro.py│─────▶│mcp_backend.py│◀─────│   server.py     │ │
│  │  (Desktop UI)  │stdio │ (Core Logic) │ HTTP │  (REST Wrapper) │ │
│  └────────────────┘      └──────────────┘      └─────────────────┘ │
│         │                       │                       │           │
│         │                       ▼                       │           │
│         │              ┌──────────────────┐             │           │
│         └─────────────▶│  Memory Store    │◀────────────┘           │
│                        │.fgd_memory.json  │                         │
│                        └──────────────────┘                         │
│                                 │                                   │
│                                 ▼                                   │
│                        ┌──────────────────┐                         │
│                        │  File System     │                         │
│                        │  (Watched Dirs)  │                         │
│                        └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Diagram

### 1. GUI Layer (gui_main_pro.py)

```
┌──────────────────────────────────────────────────────────────┐
│                      PyQt6 GUI (2,400+ lines)                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   Main      │  │   Server     │  │     Memory        │  │
│  │  Window     │  │   Control    │  │    Explorer       │  │
│  │             │  │   Panel      │  │                   │  │
│  │ • Path      │  │ • Start/Stop │  │ • Tree View       │  │
│  │   Selector  │  │ • Provider   │  │ • Search          │  │
│  │ • Theme     │  │   Select     │  │ • Export          │  │
│  │ • Tabs      │  │ • Status     │  │                   │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │    Chat     │  │     Logs     │  │    Settings       │  │
│  │  Interface  │  │    Viewer    │  │                   │  │
│  │             │  │              │  │ • Config Edit     │  │
│  │ • Message   │  │ • Real-time  │  │ • Theme Toggle    │  │
│  │   History   │  │   Tail       │  │ • API Keys        │  │
│  │ • LLM Query │  │ • Filtering  │  │                   │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│                          ▼                                   │
│               ┌──────────────────────┐                       │
│               │  Subprocess Manager   │                       │
│               │  • Popen() Backend   │                       │
│               │  • Daemon Threads    │                       │
│               │  • Pipe Management   │                       │
│               └──────────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ stdin/stdout/stderr pipes
                           │ JSON-RPC 2.0 protocol
                           ▼
```

### 2. MCP Backend Layer (mcp_backend.py)

```
┌──────────────────────────────────────────────────────────────┐
│                  MCP Backend (1,375 lines)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              MCP Server (stdio_server)                │  │
│  │                  JSON-RPC 2.0 Protocol                │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │  Tool Registry (9 tools):                            │  │
│  │  ┌─────────────────┐  ┌────────────────────────┐     │  │
│  │  │ File Operations │  │   Git Operations       │     │  │
│  │  │                 │  │                        │     │  │
│  │  │ • list_directory│  │ • git_diff             │     │  │
│  │  │ • read_file     │  │ • git_commit           │     │  │
│  │  │ • write_file    │  │ • git_log              │     │  │
│  │  │ • edit_file     │  │                        │     │  │
│  │  │ • create_dir    │  │                        │     │  │
│  │  └─────────────────┘  └────────────────────────┘     │  │
│  │                                                       │  │
│  │  ┌────────────────────────────────────────────┐      │  │
│  │  │        LLM Integration (llm_query)         │      │  │
│  │  │                                            │      │  │
│  │  │ • Multi-provider support                  │      │  │
│  │  │ • Exponential backoff retry (2s→4s→8s)    │      │  │
│  │  │ • Context injection from memory           │      │  │
│  │  │ • Async HTTP with aiohttp                 │      │  │
│  │  └────────────────────────────────────────────┘      │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Memory Store                          │  │
│  │  • File-based persistence (.fgd_memory.json)         │  │
│  │  • LRU pruning (1000 entry limit)                    │  │
│  │  • Atomic writes (temp file + rename)                │  │
│  │  • File locking (cross-platform)                     │  │
│  │  • Permissions 0o600 (owner read/write only)         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            Approval Workflow Monitor                  │  │
│  │  • File-based signaling                              │  │
│  │  • 2-second polling interval                         │  │
│  │  • .fgd_pending_edit.json → .fgd_approval.json       │  │
│  │  • Auto-apply on approval                            │  │
│  │  • Backup creation (.bak files)                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              File Watcher (Watchdog)                  │  │
│  │  • Real-time file system monitoring                   │  │
│  │  • .gitignore awareness                              │  │
│  │  • Event callbacks (created/modified/deleted)        │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 3. REST API Layer (server.py)

```
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI Server (666 lines)                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 FastAPI Application                   │  │
│  │                    Port 8456                          │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │  Endpoints:                                          │  │
│  │  • GET  /                     → API info            │  │
│  │  • GET  /health               → Health check        │  │
│  │  • POST /tools/list           → List all tools      │  │
│  │  • POST /tools/{tool_name}    → Execute tool        │  │
│  │  • GET  /memory               → Get memory          │  │
│  │  • POST /memory               → Add memory          │  │
│  │  • GET  /config               → Get config          │  │
│  │                                                       │  │
│  │  Middleware:                                         │  │
│  │  • CORS (configurable origins)                      │  │
│  │  • Rate Limiting (slowapi) - 100 req/min           │  │
│  │  • Request logging                                  │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           │ Delegates to                     │
│                           ▼                                  │
│                  ┌─────────────────┐                        │
│                  │  MCPBackend     │                        │
│                  │  Instance       │                        │
│                  └─────────────────┘                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Communication Flow

### Scenario 1: GUI → MCP Backend (Stdio Mode)

```
┌─────────────┐                                    ┌──────────────┐
│  PyQt6 GUI  │                                    │ MCP Backend  │
│             │                                    │              │
│  User Click │                                    │              │
│  "Start"    │                                    │              │
└─────┬───────┘                                    └──────────────┘
      │
      │ 1. subprocess.Popen()
      │    [python, mcp_backend.py, config.yaml]
      │    stdin=PIPE, stdout=PIPE, stderr=PIPE
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Process Created                             │
│                                                                  │
│  GUI Process                         MCP Backend Process        │
│  ┌──────────┐                        ┌──────────────┐          │
│  │  Daemon  │  ─────stdin──────▶     │   stdin      │          │
│  │  Thread  │                         │   reader     │          │
│  │          │  ◀────stdout─────       │              │          │
│  │  (stdout)│                         │   asyncio    │          │
│  │          │  ◀────stderr─────       │   event loop │          │
│  │  (stderr)│                         │              │          │
│  └──────────┘                        └──────────────┘          │
│       │                                       │                 │
│       │ 2. Writes to log file                │                 │
│       │    (.fgd_backend.log)                │                 │
│       │                                       │                 │
│       │                             3. Initializes:            │
│       │                                - Memory Store           │
│       │                                - File Watcher           │
│       │                                - Approval Monitor       │
│       │                                - Tool Registry          │
│       │                                                         │
└──────┼─────────────────────────────────────────────────────────┘
       │
       │ 4. GUI Timer (100ms intervals)
       ▼
  ┌───────────────────────┐
  │  Approval File Poll   │
  │ .fgd_pending_edit.json│
  └───────────────────────┘
```

### Scenario 2: Tool Execution via JSON-RPC

```
┌─────────────┐                                    ┌──────────────┐
│   Client    │                                    │ MCP Backend  │
│  (GUI/REST) │                                    │              │
└──────┬──────┘                                    └──────────────┘
       │
       │ 1. JSON-RPC Request
       │    {"jsonrpc": "2.0", "method": "tools/call",
       │     "params": {"name": "read_file", "arguments": {"path": "test.py"}},
       │     "id": 1}
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                       MCP Backend                             │
│                                                              │
│  2. stdio_server() receives request                         │
│     ▼                                                        │
│  ┌────────────────────────────────────┐                     │
│  │  @server.call_tool() decorator     │                     │
│  │  async def call_tool(name, args)   │                     │
│  └──────────┬─────────────────────────┘                     │
│             │                                                │
│             │ 3. Route to handler                           │
│             ▼                                                │
│  ┌──────────────────────────────────────────┐               │
│  │  if name == "read_file":                │               │
│  │    path = self._sanitize(args["path"])  │               │
│  │    content = path.read_text()           │               │
│  │    return {"content": content, ...}     │               │
│  └──────────┬───────────────────────────────┘               │
│             │                                                │
│             │ 4. Pydantic validation                        │
│             │    Input validation                           │
│             │                                                │
│             │ 5. Execute operation                          │
│             │    - Path sanitization                        │
│             │    - .gitignore check                         │
│             │    - File size validation (250KB limit)       │
│             │    - Read file content                        │
│             │                                                │
│             │ 6. Return result                              │
│             ▼                                                │
│  {"jsonrpc": "2.0", "result": {...}, "id": 1}               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
       │
       │ 7. Write to stdout
       ▼
┌──────────────┐
│   Client     │
│  (receives   │
│   response)  │
└──────────────┘
```

### Scenario 3: File Edit Approval Workflow

```
┌─────────────┐                      ┌──────────────┐                    ┌─────────────┐
│   Client    │                      │ MCP Backend  │                    │  PyQt6 GUI  │
└──────┬──────┘                      └──────┬───────┘                    └──────┬──────┘
       │                                    │                                   │
       │ 1. Request edit_file               │                                   │
       │    {"filepath": "test.py",         │                                   │
       │     "old_text": "foo",             │                                   │
       │     "new_text": "bar"}             │                                   │
       │                                    │                                   │
       ▼                                    │                                   │
  ┌────────────────────────────┐           │                                   │
  │  MCP Backend               │           │                                   │
  │                            │           │                                   │
  │  2. Creates approval req   │           │                                   │
  │     .fgd_pending_edit.json │           │                                   │
  │     {                      │           │                                   │
  │       "filepath": "...",   │           │                                   │
  │       "old_text": "...",   │───────────┼──────────────────────────────────▶│
  │       "new_text": "...",   │           │  3. GUI polls every 100ms         │
  │       "uuid": "..."        │           │     Finds pending edit            │
  │     }                      │           │                                   │
  └────────────────────────────┘           │                                   │
                                           │                              ┌────▼────────┐
                                           │                              │ Shows modal │
                                           │                              │ "Approve    │
                                           │                              │  edit?"     │
                                           │                              │ [Yes] [No]  │
                                           │                              └────┬────────┘
                                           │                                   │
                                           │                                   │ User clicks Yes
                                           │                                   │
                                           │  4. GUI writes approval           │
                                           │     .fgd_approval.json            │
                                           │     {"approved": true, ...}       │
                                           │ ◀──────────────────────────────────┤
  ┌────────────────────────────┐           │                                   │
  │  MCP Backend               │           │                                   │
  │                            │           │                                   │
  │  5. Approval monitor       │           │                                   │
  │     (polls every 2s)       │           │                                   │
  │     Finds approval file    │           │                                   │
  │                            │           │                                   │
  │  6. Applies edit:          │           │                                   │
  │     - Create .bak backup   │           │                                   │
  │     - Replace text         │           │                                   │
  │     - Write file           │           │                                   │
  │     - Delete approval files│           │                                   │
  │                            │           │                                   │
  │  7. Returns success        │───────────┼──────────────────────────────────▶│
  └────────────────────────────┘           │  8. Shows notification            │
                                           │     "Edit applied successfully"   │
                                           │                                   │
```

---

## Data Flow

### Memory Persistence Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Memory Store Lifecycle                       │
└─────────────────────────────────────────────────────────────────────┘

1. Initialization
   ┌────────────────────────────┐
   │  MemoryStore.__init__()    │
   │  ├─ Load .fgd_memory.json  │
   │  ├─ Parse JSON             │
   │  ├─ Populate in-memory dict│
   │  └─ Prune if > 1000 entries│
   └────────────────────────────┘
                │
                ▼
2. Read Operation
   ┌────────────────────────────┐
   │  memory.get(key)           │
   │  └─ Return from dict       │
   └────────────────────────────┘
                │
                ▼
3. Write Operation
   ┌────────────────────────────────────────────────┐
   │  memory.add(key, value)                       │
   │  ├─ Update in-memory dict                     │
   │  ├─ Check if pruning needed (> 1000 entries)  │
   │  │  └─ If yes: Keep 900 most recent          │
   │  └─ Call _save()                              │
   └────────────────────────────────────────────────┘
                │
                ▼
4. Atomic Save
   ┌────────────────────────────────────────────────┐
   │  _save()                                       │
   │  ├─ Acquire file lock (timeout=10s)           │
   │  ├─ Write to .fgd_memory.tmp                  │
   │  ├─ chmod 0o600 (owner only)                  │
   │  ├─ Atomic rename: .tmp → .json               │
   │  │  └─ Windows fallback: direct write         │
   │  └─ Release lock                              │
   └────────────────────────────────────────────────┘
```

### Git Operations Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Git Tool Execution                          │
└─────────────────────────────────────────────────────────────────────┘

1. git_diff
   ┌────────────────────────────────────────┐
   │  subprocess.run(["git", "diff"])       │
   │  ├─ cwd = project_root                 │
   │  ├─ capture_output=True                │
   │  └─ text=True                          │
   └────┬───────────────────────────────────┘
        │
        ▼
   ┌────────────────────────────────────────┐
   │  Return stdout (diff output)           │
   │  OR error if returncode != 0           │
   └────────────────────────────────────────┘

2. git_commit
   ┌────────────────────────────────────────────┐
   │  subprocess.run(["git", "add", "."])       │
   │  subprocess.run(["git", "commit", "-m"])   │
   │  ├─ Validate message not empty            │
   │  ├─ Check git user config                 │
   │  └─ Return commit hash + summary          │
   └────────────────────────────────────────────┘

3. git_log
   ┌────────────────────────────────────────────┐
   │  subprocess.run(["git", "log", "-n", 10])  │
   │  └─ Return formatted log entries           │
   └────────────────────────────────────────────┘
```

### LLM Query Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          LLM Query Execution                         │
└─────────────────────────────────────────────────────────────────────┘

1. Input Validation
   ┌────────────────────────────────────────┐
   │  llm_query(prompt, context, provider)  │
   │  ├─ Validate provider in config        │
   │  ├─ Get API key from environment       │
   │  └─ Select provider endpoint           │
   └────┬───────────────────────────────────┘
        │
        ▼
2. Context Injection
   ┌────────────────────────────────────────┐
   │  Inject memory context into prompt     │
   │  ├─ Get recent memory entries          │
   │  ├─ Format as context                  │
   │  └─ Prepend to user prompt             │
   └────┬───────────────────────────────────┘
        │
        ▼
3. HTTP Request with Retry
   ┌────────────────────────────────────────┐
   │  _retry_request(url, payload)          │
   │  ├─ Try 1: Immediate                   │
   │  ├─ Try 2: Wait 2s (if failed)         │
   │  ├─ Try 3: Wait 4s (exponential)       │
   │  └─ Try 4: Wait 8s (final attempt)     │
   └────┬───────────────────────────────────┘
        │
        ▼
4. Response Processing
   ┌────────────────────────────────────────┐
   │  Parse JSON response                   │
   │  ├─ Extract completion text            │
   │  ├─ Add to memory context              │
   │  └─ Return to client                   │
   └────────────────────────────────────────┘
```

---

## File Structure

```
MCPM/
├── Core Backend
│   ├── mcp_backend.py           # Main MCP server (1,375 lines)
│   ├── server.py                # FastAPI REST wrapper (666 lines)
│   └── claude_bridge.py         # CLI interface (106 lines)
│
├── GUI
│   ├── gui_main_pro.py          # PyQt6 GUI application (2,400+ lines)
│   └── index.html               # Web-based UI (alternative)
│
├── Configuration
│   ├── .env.example             # Environment variables template
│   ├── config.example.yaml      # Server configuration template
│   ├── fgd_config.yaml          # Active configuration
│   └── .gitignore               # Git ignore patterns
│
├── Startup Scripts
│   ├── quick_start.bat          # Windows startup (needs update)
│   ├── Makefile.docker          # Docker commands (214 targets)
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml       # Full stack orchestration
│
├── Dependencies
│   ├── requirements.txt         # Python dependencies (14 packages)
│   └── requirements-lock.txt    # Locked versions (recommended)
│
├── Runtime Files (Generated)
│   ├── .fgd_memory.json         # Persistent memory store
│   ├── .fgd_pending_edit.json   # Edit approval requests
│   ├── .fgd_approval.json       # Edit approvals
│   └── .fgd_backend.log         # Backend logs
│
├── Tests
│   ├── test_grok_debugging.py
│   ├── test_watch_dir_validation.py
│   ├── test_grok_connection.py
│   ├── test_setup.py
│   └── test_path_validation.py
│
├── Documentation
│   ├── README.md                # Main documentation (1,070 lines)
│   ├── CONTRIBUTING.md          # Contribution guidelines
│   ├── SECURITY.md              # Security policy
│   ├── LICENSE                  # MIT license
│   ├── REVIEW_REPORT.md         # Comprehensive audit report
│   ├── TODO.md                  # Prioritized task list
│   └── ARCHITECTURE_MAP.md      # This file
│
└── Assets
    ├── assets/icons/            # SVG icons (8 files)
    └── assets/logo/             # Brand assets (to be created)
```

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.10+ | Core implementation |
| **MCP Protocol** | mcp | 1.0.0+ | JSON-RPC 2.0 server |
| **GUI Framework** | PyQt6 | 6.8.0 | Desktop application |
| **Web Framework** | FastAPI | 0.115.5 | REST API |
| **HTTP Server** | Uvicorn | 0.32.1 | ASGI server |
| **Async HTTP** | aiohttp | 3.11.7 | LLM API requests |
| **File Watching** | watchdog | 6.0.0 | Real-time FS monitoring |

### LLM Integrations

| Provider | SDK | Model | Base URL |
|----------|-----|-------|----------|
| **Grok** | openai | grok-3 | https://api.x.ai/v1 |
| **OpenAI** | openai | gpt-4o-mini | https://api.openai.com/v1 |
| **Claude** | anthropic | claude-3-5-sonnet | https://api.anthropic.com/v1 |
| **Ollama** | openai | llama3 | http://localhost:11434/v1 |

### Dependencies

```python
# Core MCP
mcp==1.0.0

# LLM Providers
openai==1.54.4
anthropic==0.39.0

# HTTP & Async
aiohttp==3.11.7
httpx==0.27.2

# Web Framework
fastapi==0.115.5
uvicorn[standard]==0.32.1
slowapi==0.1.9

# File Watching
watchdog==6.0.0

# GUI
PyQt6==6.8.0

# Utilities
python-dotenv==1.0.1
pyyaml==6.0.2
filelock==3.16.1
```

---

## Deployment Architecture

### Option 1: Desktop GUI (Recommended for Development)

```
┌─────────────────────────────────────────────────────┐
│              User's Desktop (Windows/Linux/macOS)    │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │          PyQt6 GUI Application                 │ │
│  │          (gui_main_pro.py)                     │ │
│  │                                                │ │
│  │  Spawns subprocess:                           │ │
│  │  └─ python mcp_backend.py fgd_config.yaml     │ │
│  │                                                │ │
│  │  File System:                                 │ │
│  │  ├─ .fgd_memory.json     (persistent state)   │ │
│  │  ├─ .fgd_backend.log     (logs)               │ │
│  │  └─ User's project files                      │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Environment:                                        │
│  • Python 3.10+ virtual environment                  │
│  • API keys in .env file                             │
│  • Config in fgd_config.yaml                         │
└─────────────────────────────────────────────────────┘
```

### Option 2: Stdio Server (Recommended for Production)

```
┌─────────────────────────────────────────────────────┐
│              MCP Client Application                  │
│              (VS Code, CLI, etc.)                    │
│                                                      │
│  Communicates via stdin/stdout:                      │
│  └─ python mcp_backend.py config.yaml               │
│                                                      │
│  JSON-RPC 2.0 Protocol:                              │
│  {"jsonrpc": "2.0", "method": "...", ...}            │
└─────────────────────────────────────────────────────┘
                        │
                        │ stdio pipes
                        ▼
┌─────────────────────────────────────────────────────┐
│              MCP Backend Process                     │
│              (mcp_backend.py)                        │
│                                                      │
│  • Reads JSON-RPC from stdin                         │
│  • Writes responses to stdout                        │
│  • Logs to stderr                                    │
│  • Accesses file system                              │
│  • Persists memory to .fgd_memory.json               │
└─────────────────────────────────────────────────────┘
```

### Option 3: REST API Server (Optional)

```
┌─────────────────────────────────────────────────────┐
│              HTTP Clients                            │
│              (curl, Postman, web apps)               │
│                                                      │
│  HTTP Requests:                                      │
│  POST http://localhost:8456/tools/read_file          │
└─────────────────────────────────────────────────────┘
                        │
                        │ HTTP/REST
                        ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Server                          │
│              (server.py)                             │
│                                                      │
│  • Port: 8456                                        │
│  • Rate limiting: 100 req/min                        │
│  • CORS enabled                                      │
│  • Delegates to MCPBackend instance                  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              MCP Backend Instance                    │
│              (in-process)                            │
└─────────────────────────────────────────────────────┘
```

### Option 4: Docker Deployment (Production Stack)

```
docker-compose.yml:

┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose Stack                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  nginx (Port 80)                                   │    │
│  │  • Reverse proxy                                   │    │
│  │  • SSL termination                                 │    │
│  │  • Load balancing                                  │    │
│  └──────────────┬─────────────────────────────────────┘    │
│                 │                                           │
│                 ▼                                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  mcpm-api-gateway (Port 8456)                      │    │
│  │  • FastAPI server                                  │    │
│  │  • Rate limiting                                   │    │
│  │  • Authentication                                  │    │
│  └──────────────┬─────────────────────────────────────┘    │
│                 │                                           │
│                 ▼                                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  mcpm-mcp-backend                                  │    │
│  │  • MCP server                                      │    │
│  │  • File operations                                 │    │
│  │  • Git operations                                  │    │
│  │  • LLM integration                                 │    │
│  └──────────────┬─────────────────────────────────────┘    │
│                 │                                           │
│                 ▼                                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  redis (Port 6379)                                 │    │
│  │  • Session storage                                 │    │
│  │  • Caching layer                                   │    │
│  │  • Pub/sub messaging                               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  Volumes:                                                   │
│  • ./data       → /app/data    (persistent memory)          │
│  • ./logs       → /app/logs    (log files)                  │
│  • ./projects   → /app/projects (user projects)             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

### Access Control

```
┌─────────────────────────────────────────────────────┐
│              Security Layers                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. API Keys (Environment Variables)                 │
│     • XAI_API_KEY (Grok)                             │
│     • OPENAI_API_KEY (OpenAI)                        │
│     • ANTHROPIC_API_KEY (Claude)                     │
│     • Loaded from .env file (gitignored)             │
│                                                      │
│  2. File System Access Control                       │
│     • Path sanitization (prevent ../traversal)       │
│     • .gitignore filtering                           │
│     • File permissions 0o600 for sensitive files     │
│     • Max file size limit (250KB)                    │
│                                                      │
│  3. Subprocess Safety                                │
│     • List-based commands (no shell injection)       │
│     • No shell=True parameter                        │
│     • stderr logging for audit                       │
│                                                      │
│  4. REST API Security                                │
│     • Rate limiting (100 req/min)                    │
│     • CORS configuration                             │
│     • Input validation (Pydantic)                    │
│     • Request logging                                │
│                                                      │
│  5. Memory Protection                                │
│     • File locking (prevent race conditions)         │
│     • Atomic writes (prevent corruption)             │
│     • Owner-only permissions (0o600)                 │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Performance Characteristics

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| **list_directory** (small) | < 10ms | Lazy tree loading |
| **list_directory** (large) | < 500ms | 20-50x improvement via lazy loading |
| **read_file** | < 50ms | 250KB size limit |
| **write_file** | < 100ms | Atomic write + backup |
| **git_diff** | 100-500ms | Subprocess overhead |
| **git_commit** | 200-1000ms | Subprocess + validation |
| **llm_query** | 2-30s | Network-dependent, retries enabled |
| **Memory save** | 50-200ms | JSON serialization |
| **Approval polling** | 100ms | GUI timer interval |
| **Approval monitor** | 2s | Backend polling interval |

### Optimization Opportunities

1. **File Polling Consolidation** - 67% I/O reduction
2. **Git Operation Caching** - 90% subprocess reduction
3. **Watchdog Filtering** - 10x fewer events
4. **LLM Response Caching** - Reduce API calls
5. **Batch Tool Execution** - Reduce round-trip latency

---

## Error Handling & Resilience

### Error Handling Strategy

```
┌─────────────────────────────────────────────────────┐
│              Error Handling Layers                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. Input Validation (Pydantic)                      │
│     • Type checking                                  │
│     • Required field validation                      │
│     • Format validation                              │
│     • Returns: {"error": "Invalid input"}            │
│                                                      │
│  2. Path Sanitization                                │
│     • Prevents directory traversal                   │
│     • Resolves to absolute paths                     │
│     • Checks within allowed directories              │
│     • Returns: {"error": "Path not allowed"}         │
│                                                      │
│  3. File Operations                                  │
│     • IOError, OSError handling                      │
│     • Timeout handling (file locks)                  │
│     • Backup creation before writes                  │
│     • Returns: {"error": "File not found"}           │
│                                                      │
│  4. Subprocess Execution                             │
│     • Return code validation                         │
│     • stderr capture                                 │
│     • Timeout handling                               │
│     • Returns: {"error": "Command failed"}           │
│                                                      │
│  5. LLM API Calls                                    │
│     • Exponential backoff retry (4 attempts)         │
│     • aiohttp exception handling                     │
│     • Timeout configuration                          │
│     • Returns: {"error": "LLM request failed"}       │
│                                                      │
│  6. JSON-RPC Protocol                                │
│     • ValidationError handling                       │
│     • JSONDecodeError handling                       │
│     • Detailed error messages                        │
│     • Returns: JSON-RPC error response               │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Retry Mechanisms

```
LLM Query Retry Logic:

Attempt 1: ───────────────────────▶ Immediate
            │                        │
            │ Fail                   │ Success
            ▼                        ▼
Attempt 2: ─── Wait 2s ───────────▶ Return
            │
            │ Fail
            ▼
Attempt 3: ─── Wait 4s ───────────▶ Return
            │
            │ Fail
            ▼
Attempt 4: ─── Wait 8s ───────────▶ Return
            │
            │ Fail
            ▼
         Raise Exception
```

---

## Monitoring & Observability

### Logging Architecture

```
┌─────────────────────────────────────────────────────┐
│              Logging Stack                           │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Python logging module:                              │
│  • Level: INFO (configurable)                        │
│  • Format: '%(asctime)s - %(levelname)s - %(message)s'│
│                                                      │
│  Output Destinations:                                │
│  ┌──────────────────────────────────────────────┐   │
│  │ 1. stderr (Console)                          │   │
│  │    • Real-time debugging                     │   │
│  │    • Captured by GUI daemon thread           │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ 2. .fgd_backend.log (File)                   │   │
│  │    • Persistent audit trail                  │   │
│  │    • Viewed in GUI log viewer                │   │
│  │    • Filtered by level (INFO/WARNING/ERROR)  │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Log Categories:                                     │
│  • 🔵 Tool execution (read/write/git/llm)            │
│  • 💾 Memory operations (save/load/prune)            │
│  • 📝 File modifications (edits/approvals)           │
│  • ⚠️  Errors and warnings                           │
│  • 🔐 Security events (path sanitization)            │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Metrics (To Be Implemented)

- Tool invocation count by type
- Average tool execution time
- LLM query success/failure rate
- Memory size over time
- Approval workflow latency
- File watcher event rate

---

## Future Enhancements

### Roadmap (v6.1+)

1. **Plugin Architecture**
   - Dynamic tool registration
   - External plugin discovery
   - Tool versioning
   - Dependency management

2. **Performance Optimizations**
   - Tool response caching
   - Batch tool execution endpoint
   - Git operation caching
   - Consolidated file polling

3. **Enhanced Security**
   - Request signing for APIs
   - Secrets encryption at rest
   - Audit logging for all file modifications
   - Role-based access control (RBAC)

4. **Monitoring & Observability**
   - Prometheus metrics endpoint
   - Grafana dashboards
   - Distributed tracing (OpenTelemetry)
   - Health check improvements

5. **Developer Experience**
   - Interactive web dashboard
   - Real-time task output visualization
   - Improved error messages
   - VS Code extension

---

## Glossary

| Term | Definition |
|------|------------|
| **MCP** | Model Context Protocol - Protocol for LLM-context management |
| **JSON-RPC** | JSON Remote Procedure Call - Protocol for client-server communication |
| **stdio** | Standard Input/Output - Unix communication mechanism |
| **LRU** | Least Recently Used - Cache eviction algorithm |
| **Pydantic** | Python data validation library |
| **asyncio** | Python async I/O framework |
| **FastAPI** | Modern Python web framework |
| **PyQt6** | Python bindings for Qt GUI framework |
| **Watchdog** | Python library for file system monitoring |
| **Atomic write** | Write operation that appears instantaneous (temp file + rename) |
| **Daemon thread** | Background thread that doesn't prevent process exit |

---

## References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-18
**Maintained By**: MCPM Contributors
**License**: MIT

---

**End of Architecture Map**
