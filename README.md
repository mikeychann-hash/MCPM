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

### Critical Issues Identified

1. **Exception Handling** (Priority: HIGH)
   - **Location**: `mcp_backend.py:239`, `local_directory_memory_mcp_refactored.py:38,172,239`
   - **Issue**: Bare `except:` clauses without specific exception types
   - **Impact**: Can hide bugs and make debugging difficult
   - **Recommendation**: Replace with specific exception types or `except Exception as e:`

2. **Duplicate Server Implementation** (Priority: MEDIUM)
   - **Location**: `mcp_backend.py` vs `local_directory_memory_mcp_refactored.py`
   - **Issue**: Two similar MCP server implementations causing confusion
   - **Recommendation**: Consolidate into single implementation or clearly document use cases

3. **Security Concerns** (Priority: HIGH)
   - **Path Traversal**: `_sanitize()` methods need hardening
   - **CORS Policy**: `server.py:16-20` allows all origins (insecure for production)
   - **No Rate Limiting**: LLM queries can be abused
   - **Recommendation**: Implement stricter validation, CORS whitelist, and rate limiting

4. **Missing Claude Implementation** (Priority: MEDIUM)
   - **Location**: `mcp_backend.py:109-111`
   - **Issue**: Claude provider configured but not fully implemented
   - **Recommendation**: Complete Claude API integration or remove from options

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
