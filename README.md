# FGD Fusion Stack Pro - MCP Memory & LLM Integration

A professional Model Context Protocol (MCP) server with intelligent memory management, file monitoring, and multi-LLM provider support. Features a modern PyQt6 GUI for managing your development workspace with persistent memory and context-aware AI assistance.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [How It Works](#how-it-works)
- [LLM Connection & Memory System](#llm-connection--memory-system)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Code Review Findings](#code-review-findings)

---

## Overview

FGD Fusion Stack Pro provides an MCP-compliant server that bridges your local development environment with Large Language Models. It maintains persistent memory of interactions, monitors file system changes, and provides intelligent context to LLM queries.

**Key Components:**
- **MCP Server**: Model Context Protocol compliant server for tool execution
- **Memory Store**: Persistent JSON-based memory with categories and access tracking
- **File Watcher**: Real-time file system monitoring and change detection
- **LLM Backend**: Multi-provider support (Grok, OpenAI, Claude, Ollama)
- **PyQt6 GUI**: Professional dark-themed interface for management
- **FastAPI Server**: Optional REST API wrapper for web integration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│  ┌────────────────┐              ┌────────────────┐         │
│  │  PyQt6 GUI     │              │  FastAPI REST  │         │
│  │  (gui_main_    │              │  (server.py)   │         │
│  │   pro.py)      │              │                │         │
│  └────────┬───────┘              └────────┬───────┘         │
└───────────┼──────────────────────────────┼─────────────────┘
            │                              │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │   MCP Server (mcp_backend.py) │
            │                               │
            │  ┌─────────────────────────┐  │
            │  │  MCP Protocol Handler   │  │
            │  │  - list_tools()         │  │
            │  │  - call_tool()          │  │
            │  └─────────────────────────┘  │
            │                               │
            │  ┌──────────┬───────────┐    │
            │  │ Memory   │ File      │    │
            │  │ Store    │ Watcher   │    │
            │  └──────────┴───────────┘    │
            │                               │
            │  ┌─────────────────────────┐  │
            │  │    LLM Backend          │  │
            │  │  ┌─────┬──────┬──────┐ │  │
            │  │  │Grok │OpenAI│Claude│ │  │
            │  │  └─────┴──────┴──────┘ │  │
            │  └─────────────────────────┘  │
            └──────────────┬────────────────┘
                           ▼
            ┌──────────────────────────────┐
            │    External LLM APIs         │
            │  - X.AI (Grok)               │
            │  - OpenAI                    │
            │  - Anthropic (Claude)        │
            │  - Ollama (Local)            │
            └──────────────────────────────┘
```

---

## Features

### MCP Tools
- **read_file**: Read file contents with size limits and path validation
- **list_files**: List files matching glob patterns (limited to prevent overload)
- **search_in_files**: Full-text search across project files
- **llm_query**: Query LLMs with automatic context injection from memory
- **remember**: Store key-value pairs in categorized persistent memory
- **recall**: Retrieve stored memories by key or category

### Memory System
- **Persistent Storage**: JSON-based memory file (`.fgd_memory.json`)
- **Categories**: Organize memories by category (general, llm, file_change, etc.)
- **Access Tracking**: Count how many times each memory is accessed
- **Timestamps**: Track when memories are created
- **Context Window**: Maintains rolling window of recent interactions (configurable limit)

### File Monitoring
- **Watchdog Integration**: Real-time file system event monitoring
- **Change Tracking**: Records created, modified, and deleted files
- **Context Integration**: File changes automatically added to context window
- **Size Limits**: Configurable directory and file size limits to prevent overload

### GUI Features
- **Dark Theme**: Professional GitHub-inspired dark mode (light mode available)
- **Live Logs**: Real-time log viewing with filtering by level and search
- **Provider Selection**: Easy switching between LLM providers (Grok, OpenAI, Claude, Ollama)
- **API Key Validation**: Automatic fallback to Grok if other API keys are missing
- **Process Management**: Clean start/stop of MCP server with proper cleanup

---

## How It Works

### 1. Server Initialization
When you start the MCP server:
1. **Configuration Loading**: Reads YAML config with watch directory, memory file path, LLM settings
2. **Memory Store Init**: Loads existing memories from JSON file or creates new store
3. **File Watcher Setup**: Starts watchdog observer on specified directory
4. **MCP Registration**: Registers all available tools with the MCP protocol
5. **Log Handler**: Sets up file logging to track all operations

### 2. File System Monitoring
The file watcher continuously monitors your project directory:
```python
# Example: File change flow
User modifies file.py
    ↓
Watchdog detects change event
    ↓
Event added to recent_changes[] (max 50)
    ↓
Context added to memory.context (rolling window)
    ↓
Available for next LLM query
```

### 3. Memory Lifecycle
Memories persist across sessions and track usage:
```python
# Memory structure
{
  "category_name": {
    "key_name": {
      "value": "stored data",
      "timestamp": "2025-11-03T10:30:00",
      "access_count": 5
    }
  }
}
```

**Categories Used:**
- `general`: User-defined key-value pairs
- `llm`: Stores LLM responses for future reference
- `file_change`: Automatic tracking of file modifications (in context window)

---

## LLM Connection & Memory System

### How LLM Queries Work

When you call the `llm_query` tool, here's what happens:

```
1. User/Agent calls llm_query with prompt
         ↓
2. Server retrieves last 5 context items from memory
   (file changes, previous queries, user actions)
         ↓
3. Context is formatted as JSON and prepended to prompt
         ↓
4. Full prompt sent to selected LLM provider
         ↓
5. LLM response received
         ↓
6. Response stored in memory under "llm" category
   with timestamp as key
         ↓
7. Response returned to caller
```

### Context Injection Example

```python
# Before sending to LLM:
context = [
  {"type": "file_change", "data": {"type": "modified", "path": "src/main.py"}, "timestamp": "2025-11-03T10:15:00"},
  {"type": "file_read", "data": {"path": "config.yaml"}, "timestamp": "2025-11-03T10:16:00"},
  {"type": "llm_query", "data": {"prompt": "Explain this code"}, "timestamp": "2025-11-03T10:17:00"}
]

full_prompt = f"{json.dumps(context)}\n\n{user_prompt}"
# LLM now has context of recent file changes and interactions
```

### Supported LLM Providers

#### 1. **Grok (X.AI)** - Default Provider
- **Model**: `grok-beta`
- **API**: `https://api.x.ai/v1`
- **Key**: `XAI_API_KEY` environment variable
- **Features**: Fast responses, good code understanding

#### 2. **OpenAI**
- **Model**: `gpt-4o-mini` (configurable)
- **API**: `https://api.openai.com/v1`
- **Key**: `OPENAI_API_KEY` environment variable
- **Features**: Excellent reasoning, widely supported

#### 3. **Claude (Anthropic)**
- **Model**: `claude-3-5-sonnet-20241022`
- **API**: `https://api.anthropic.com/v1`
- **Key**: `ANTHROPIC_API_KEY` environment variable
- **Note**: Currently mentioned in config but needs implementation completion

#### 4. **Ollama (Local)**
- **Model**: `llama3` (configurable)
- **API**: `http://localhost:11434/v1`
- **Key**: No API key required (local)
- **Features**: Privacy-focused, no cost, runs locally

### Memory Utilization Strategies

The memory system enables:

1. **Conversation Continuity**: Previous LLM responses stored and retrievable
2. **File Context Awareness**: LLM knows which files were recently modified
3. **Usage Analytics**: Access counts help identify frequently referenced information
4. **Session Persistence**: Memories survive server restarts
5. **Categorization**: Easy filtering of memory types (code, docs, errors, etc.)

---

## Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager
- Virtual environment (recommended)

### System Dependencies (Linux)

The PyQt6 GUI requires the following system libraries on Linux:

```bash
# Ubuntu/Debian
sudo apt-get install -y libegl1 libegl-mesa0 libgl1 libxkbcommon0 libdbus-1-3 \
    libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-cursor0 libxcb-xfixes0
```

**Note**: These are automatically installed on most desktop Linux systems, but may be missing in minimal/server installations.

### Steps

1. **Clone or download the repository**
   ```bash
   cd MCPM
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   # Required for Grok (default provider)
   XAI_API_KEY=your_xai_api_key_here

   # Optional: Only needed if using these providers
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

5. **Configure settings** (optional)
   Edit `config.example.yaml` to customize:
   - Default LLM provider
   - Model names
   - File size limits
   - Context window size

---

## Configuration

### config.example.yaml

```yaml
watch_dir: "/path/to/your/project"    # Directory to monitor
memory_file: ".fgd_memory.json"        # Memory storage file
log_file: "fgd_server.log"             # Log output file
context_limit: 20                      # Max context items to keep

scan:
  max_dir_size_gb: 2                   # Max directory size to scan
  max_files_per_scan: 5                # Max files per list operation
  max_file_size_kb: 250                # Max individual file size to read

llm:
  default_provider: "grok"             # Default LLM provider
  providers:
    grok:
      model: "grok-beta"
      base_url: "https://api.x.ai/v1"
    openai:
      model: "gpt-4o-mini"
      base_url: "https://api.openai.com/v1"
    claude:
      model: "claude-3-5-sonnet-20241022"
      base_url: "https://api.anthropic.com/v1"
    ollama:
      model: "llama3"
      base_url: "http://localhost:11434/v1"
```

---

## Usage

### Option 1: PyQt6 GUI (Recommended)

```bash
python gui_main_pro.py
```

**GUI Workflow:**
1. Click **Browse** to select your project directory
2. Choose LLM provider from dropdown (Grok, OpenAI, Claude, Ollama)
3. Click **Start Server** to launch MCP backend
4. View live logs with filtering options
5. Monitor server status in real-time

**GUI automatically:**
- Generates config file for selected directory
- Validates API keys and falls back to Grok if needed
- Manages subprocess lifecycle
- Provides log filtering by level (INFO, WARNING, ERROR)

### Option 2: MCP Server Directly

```bash
python mcp_backend.py config.example.yaml
```

This starts the MCP server in stdio mode for integration with MCP clients.

### Option 3: FastAPI REST Server

```bash
python server.py
```

Access endpoints at `http://localhost:8456`:
- `GET /api/status` - Check server status
- `POST /api/start` - Start MCP server
- `GET /api/logs?file=fgd_server.log` - View logs
- `GET /api/memory` - Retrieve all memories
- `POST /api/llm_query` - Query LLM directly

### Command-Line Grok Control Cheatsheet

Use the REST server when you just need a quick way to send prompts to the Grok LLM without opening the GUI. The sequence below assumes you are in the repository root and have already followed the [Installation](#installation) steps.

```bash
# 1) Activate your virtual environment (or skip if already active)
source .venv/bin/activate

# 2) Ensure your Grok key is available to the process
export XAI_API_KEY="sk-your-grok-key"

# 3) Launch the FastAPI wrapper in the background
python server.py &

# 4) Start the MCP backend through the API (edit watch_dir to your project path)
curl -s -X POST http://localhost:8456/api/start \
  -H 'Content-Type: application/json' \
  -d '{
        "watch_dir": "/workspace/MCPM",
        "default_provider": "grok"
      }'

# 5) Send a prompt to Grok
curl -s -X POST http://localhost:8456/api/llm_query \
  -H 'Content-Type: application/json' \
  -d '{
        "prompt": "Summarize README.md",
        "provider": "grok"
      }'

# 6) (Optional) Inspect status or stop the backend when finished
curl -s http://localhost:8456/api/status | jq
curl -s -X POST http://localhost:8456/api/stop | jq

# 7) Bring the FastAPI process to the foreground then exit
fg
^C
```

> 💡 Tip: If `jq` is not installed, you can drop the `| jq` portion of the commands—the responses are still valid JSON.

---

## API Reference

### MCP Tools

#### read_file
Read contents of a file in the watched directory.
```json
{
  "tool": "read_file",
  "arguments": {
    "filepath": "src/main.py"
  }
}
```

#### list_files
List files matching a glob pattern.
```json
{
  "tool": "list_files",
  "arguments": {
    "pattern": "**/*.py"  // optional, defaults to "**/*"
  }
}
```

#### search_in_files
Search for text across files.
```json
{
  "tool": "search_in_files",
  "arguments": {
    "query": "TODO",
    "pattern": "**/*.py"  // optional
  }
}
```

#### llm_query
Query an LLM with automatic context injection.
```json
{
  "tool": "llm_query",
  "arguments": {
    "prompt": "Explain this error",
    "provider": "grok"  // optional, defaults to config
  }
}
```

#### remember
Store information in persistent memory.
```json
{
  "tool": "remember",
  "arguments": {
    "key": "api_endpoint",
    "value": "https://api.example.com",
    "category": "general"  // optional
  }
}
```

#### recall
Retrieve stored memories.
```json
{
  "tool": "recall",
  "arguments": {
    "key": "api_endpoint",     // optional
    "category": "general"      // optional
  }
}
```

---

## Code Review Findings

### ✅ Fixed Issues

1. **Exception Handling** (Priority: HIGH) - ✅ **FIXED**
   - **Status**: All exception handlers now use specific exception types (`except Exception as e:`, `except aiohttp.ClientError`, etc.)
   - **Location**: Main codebase uses proper exception handling with logging
   - **Note**: Bare `except:` clauses only exist in backup file (`local_directory_memory_mcp_refactored.py.backup`)

2. **Claude Provider Implementation** (Priority: MEDIUM) - ✅ **FIXED**
   - **Status**: Claude, OpenAI, and Ollama providers now fully implemented
   - **Location**: `mcp_backend.py:169-189` (Claude), `mcp_backend.py:155-167` (OpenAI), `mcp_backend.py:191-201` (Ollama)
   - **Features**: All four providers (Grok, OpenAI, Claude, Ollama) are now operational

3. **Security Improvements** (Priority: HIGH) - ✅ **IMPROVED**
   - **Rate Limiting**: ✅ Implemented using slowapi in `server.py`
   - **CORS Policy**: ✅ Now displays prominent security warnings when using wildcard origins
   - **Path Traversal**: ✅ `_sanitize()` method validates paths against base directory
   - **Input Validation**: ✅ Pydantic models validate all API inputs

### Remaining Considerations

1. **CORS Configuration** (Priority: MEDIUM)
   - **Status**: Secure by configuration
   - **Default**: Allows all origins (`*`) for development convenience
   - **Production**: Set `CORS_ORIGINS` environment variable to specific domains
   - **Warning**: Server now logs prominent security warning when using wildcard CORS

2. **Duplicate Server Implementation** (Priority: LOW)
   - **Status**: Clarified
   - **Note**: `local_directory_memory_mcp_refactored.py.backup` is a backup file
   - **Active**: Only `mcp_backend.py` is the current implementation

### Code Quality Improvements

1. **Type Hints**: Add comprehensive type annotations
2. **Error Messages**: More descriptive error messages with context
3. **Logging**: Add DEBUG level logging for troubleshooting
4. **Documentation**: Add docstrings to all public methods
5. **Testing**: No unit tests present - recommend adding test suite

### Architecture Recommendations

1. **Configuration Management**: Use Pydantic for config validation
2. **Graceful Shutdown**: Implement proper cleanup on SIGTERM/SIGINT
3. **Health Checks**: Add `/health` endpoint to FastAPI server
4. **Authentication**: Add API key authentication for REST endpoints
5. **Monitoring**: Add metrics collection (request counts, latency, errors)

---

## Security Best Practices

If deploying in production:

1. **Environment Variables**: Never commit `.env` file
2. **API Keys**: Rotate keys regularly, use secret management service
3. **CORS**: Whitelist specific origins instead of `*`
4. **Input Validation**: Validate all user inputs and file paths
5. **Rate Limiting**: Implement per-user/IP rate limits
6. **TLS**: Use HTTPS for all external API communications
7. **Logging**: Avoid logging sensitive data (API keys, tokens)

---

## Troubleshooting

### Server won't start
- Check API key in `.env` file
- Verify directory permissions for watch_dir
- Check if port 8456 is available (for FastAPI)

### File watcher not detecting changes
- Ensure watch_dir is correctly configured
- Check directory isn't too large (>2GB default limit)
- Verify sufficient system resources

### LLM queries failing
- Verify API key is valid and has credits
- Check network connectivity to API endpoint
- Review logs for detailed error messages

### Memory not persisting
- Check write permissions on memory_file location
- Verify disk space available
- Look for errors in logs during save operations

### JSON-RPC validation errors
If you see errors like `"Invalid JSON: expected value at line 1 column 1"` or `"validation error for JSONRPCMessage"`:

**Cause**: The MCP server communicates via stdio using JSON-RPC 2.0 protocol and expects properly formatted JSON messages on stdin.

**Common scenarios:**
1. **Testing/Debugging**: Typing plain text into the terminal running the MCP server
2. **Misconfigured Client**: A client sending non-JSON data
3. **Protocol Mismatch**: Client not using JSON-RPC 2.0 format

**Expected Input Format:**
```json
{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"filepath": "test.py"}}, "id": 1}
```

**Invalid Input Examples:**
- Plain text: `"hello"` or `"ass"`
- Malformed JSON: `{invalid json}`
- Non-JSON-RPC format: `{"command": "read_file"}`

**How to Fix:**
- Use the PyQt6 GUI (`gui_main_pro.py`) instead of running the server directly
- Use the FastAPI REST wrapper (`server.py`) for HTTP-based interaction
- If using stdio directly, ensure all input is valid JSON-RPC 2.0 format
- Don't type directly into a terminal running the MCP server

**Note**: The server handles these errors gracefully and will continue running. The error is logged for debugging purposes.

---

## Contributing

Code review identified several improvement opportunities:
- Fix bare exception handlers
- Add comprehensive test suite
- Complete Claude provider implementation
- Add type hints throughout
- Improve error messages
- Consolidate duplicate server implementations

---

## License

[Add your license here]

---

## Support

For issues, questions, or contributions, please [add contact information or repository link].
