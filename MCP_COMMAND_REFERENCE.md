# MCPM Command Reference Guide
**Complete list of all MCP tools, API endpoints, and CLI commands**

---

## 📋 TABLE OF CONTENTS

1. [MCP Tools (via MCP Protocol)](#mcp-tools)
2. [API Endpoints (via REST API)](#api-endpoints)
3. [CLI Commands (via claude_bridge.py)](#cli-commands)
4. [GUI Commands (via gui_main_pro.py)](#gui-commands)
5. [Setup & Configuration](#setup--configuration)
6. [Troubleshooting](#troubleshooting)

---

## 🛠️ MCP TOOLS

These tools are available when connecting to MCPM via the Model Context Protocol (e.g., Claude Desktop app).

### 1. **list_directory**
List files in a directory (gitignore-aware)

**Parameters:**
- `path` (optional): Relative path from watch_dir, default: "."

**Example:**
```json
{
  "tool": "list_directory",
  "arguments": {
    "path": "src"
  }
}
```

**Returns:**
```json
{
  "files": [
    {"name": "main.py", "is_dir": false, "size": 1234},
    {"name": "utils", "is_dir": true, "size": 0}
  ]
}
```

---

### 2. **read_file**
Read file contents with metadata

**Parameters:**
- `filepath` (required): Relative path to file

**Example:**
```json
{
  "tool": "read_file",
  "arguments": {
    "filepath": "src/main.py"
  }
}
```

**Returns:**
```json
{
  "content": "#!/usr/bin/env python3...",
  "meta": {
    "size_kb": 1.21,
    "modified": "2025-11-08T12:34:56",
    "lines": 45
  }
}
```

**Limits:**
- Max file size: 250 KB (configurable)
- UTF-8 encoding required

---

### 3. **write_file**
Create or overwrite a file (with automatic backup)

**Parameters:**
- `filepath` (required): Relative path to file
- `content` (required): File content

**Example:**
```json
{
  "tool": "write_file",
  "arguments": {
    "filepath": "output.txt",
    "content": "Hello, world!"
  }
}
```

**Returns:**
```
Written: output.txt
Actual location: /full/path/to/output.txt
Backup: output.bak
```

**Behavior:**
- Creates .bak backup of existing file
- Logs actual write location
- Verifies write succeeded

---

### 4. **edit_file**
Edit file with diff preview and approval workflow

**Parameters:**
- `filepath` (required): File to edit
- `old_text` (required): Text to find and replace
- `new_text` (required): Replacement text
- `confirm` (optional): Skip approval if true, default: false

**Example (Request Approval):**
```json
{
  "tool": "edit_file",
  "arguments": {
    "filepath": "config.py",
    "old_text": "DEBUG = False",
    "new_text": "DEBUG = True"
  }
}
```

**Returns:**
```json
{
  "action": "confirm_edit",
  "filepath": "config.py",
  "diff": "- DEBUG = False\n+ DEBUG = True",
  "preview": "...",
  "message": "Edit pending approval - check GUI"
}
```

**Example (Auto-Apply):**
```json
{
  "tool": "edit_file",
  "arguments": {
    "filepath": "config.py",
    "old_text": "DEBUG = False",
    "new_text": "DEBUG = True",
    "confirm": true
  }
}
```

**Approval Workflow:**
1. Edit request creates `.fgd_pending_edit.json`
2. GUI displays diff in "Diff Viewer" tab
3. User clicks "Approve" or "Reject"
4. GUI creates `.fgd_approval.json`
5. Backend applies edit automatically

---

### 5. **git_diff**
Show git diff for uncommitted changes

**Parameters:**
- `files` (optional): Array of specific files, default: all changes

**Example:**
```json
{
  "tool": "git_diff",
  "arguments": {
    "files": ["src/main.py", "README.md"]
  }
}
```

**Returns:**
```diff
diff --git a/src/main.py b/src/main.py
index abc123..def456 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,7 +10,7 @@
-DEBUG = False
+DEBUG = True
```

**Requires:**
- Git repository (.git directory)
- Git installed and in PATH

---

### 6. **git_commit**
Commit changes to git

**Parameters:**
- `message` (required): Commit message

**Example:**
```json
{
  "tool": "git_commit",
  "arguments": {
    "message": "Fix: Update debug flag"
  }
}
```

**Returns:**
```
Committed: abc1234
Fix: Update debug flag
```

**Behavior:**
- Runs `git add .` (stages all changes)
- Commits with provided message
- Saves commit hash to memory

---

### 7. **git_log**
Show recent commit history

**Parameters:**
- `limit` (optional): Number of commits, default: 5

**Example:**
```json
{
  "tool": "git_log",
  "arguments": {
    "limit": 10
  }
}
```

**Returns:**
```
abc1234 Fix: Update debug flag
def5678 Add new feature
...
```

---

### 8. **llm_query**
Query an LLM (Grok, OpenAI, Claude, or Ollama)

**Parameters:**
- `prompt` (required): Question or instruction for the LLM

**Example:**
```json
{
  "tool": "llm_query",
  "arguments": {
    "prompt": "Explain this codebase structure"
  }
}
```

**Returns:**
```
[LLM response text]
```

**Context Provided:**
- MCP server status and capabilities
- Recent 5 context entries (file reads, edits, etc.)
- Previous conversations

**⚠️ BUG:** Currently hardcoded to use "grok" provider, ignoring default_provider setting

**Memory:**
- Saved to `conversations` category
- Also saved to `llm` category for backward compatibility
- Includes prompt, response, provider, timestamp

---

## 🌐 API ENDPOINTS

Access these via HTTP when running `server.py` (default port: 8456)

### Health Check

**GET** `/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "FGD Stack API",
  "version": "2.0.0",
  "mcp_server_running": true,
  "watch_dir": "/path/to/project"
}
```

---

### Server Status

**GET** `/api/status`

**Response:**
```json
{
  "api": "ok",
  "mcp_running": true,
  "watch_dir": "/path/to/project",
  "memory_file": "/path/.fgd_memory.json",
  "log_file": "fgd_runtime.log",
  "config_path": ".fgd_runtime_config.yaml"
}
```

---

### Start MCP Server

**POST** `/api/start`

**Request:**
```json
{
  "watch_dir": "/path/to/project",
  "default_provider": "grok"
}
```

**Response:**
```json
{
  "success": true,
  "memory_file": "/path/.fgd_memory.json",
  "log_file": "fgd_runtime.log",
  "watch_dir": "/path/to/project",
  "provider": "grok"
}
```

---

### Stop MCP Server

**POST** `/api/stop`

**Response:**
```json
{
  "success": true,
  "message": "MCP server stopped successfully"
}
```

---

### Get Logs

**GET** `/api/logs?file=fgd_runtime.log`

**Response:**
```
2025-11-08 12:34:56 - INFO - Server started
2025-11-08 12:35:01 - INFO - File read: main.py
...
```

---

### Get Memory

**GET** `/api/memory`

**Response:**
```json
{
  "conversations": {
    "chat_2025-11-08T12:34:56": {
      "value": {
        "prompt": "...",
        "response": "...",
        "provider": "grok"
      }
    }
  },
  "context": [...]
}
```

---

### Query LLM

**POST** `/api/llm_query`

**Request:**
```json
{
  "prompt": "What is this project about?",
  "provider": "grok"
}
```

**Response:**
```json
{
  "success": true,
  "response": "[LLM response]",
  "provider": "grok"
}
```

---

### Get Conversations

**GET** `/api/conversations`

**Response:**
```json
{
  "success": true,
  "count": 5,
  "conversations": [
    {
      "id": "chat_2025-11-08T12:34:56",
      "prompt": "...",
      "response": "...",
      "provider": "grok",
      "timestamp": "2025-11-08T12:34:56",
      "context_used": 5
    }
  ]
}
```

---

### Get Pending Edits

**GET** `/api/pending_edits`

**Response:**
```json
{
  "success": true,
  "has_pending": true,
  "pending_edit": {
    "filepath": "config.py",
    "old_text": "...",
    "new_text": "...",
    "diff": "...",
    "timestamp": "2025-11-08T12:34:56"
  }
}
```

---

### Suggest Directories

**GET** `/api/suggest`

**Response:**
```json
[
  "src",
  "tests",
  "docs",
  "scripts"
]
```

**⚠️ WARNING:** Can be slow on large directories

---

## 💻 CLI COMMANDS

Use `claude_bridge.py` for interactive CLI access

### Launch CLI

```bash
python claude_bridge.py
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `read <file>` | Read a file | `read src/main.py` |
| `list [path]` | List directory | `list src` |
| `diff [files...]` | Show git diff | `diff` |
| `commit <msg>` | Commit changes | `commit "Fix bug"` |
| `help` | Show help | `help` |
| `exit` | Quit | `exit` |

### Examples

```bash
You: read src/main.py
MCPM: [file contents]

You: list .
MCPM: [directory listing]

You: diff
MCPM: [git diff output]

You: commit "Add new feature"
MCPM: Committed: abc1234
```

**⚠️ BUG:** Command parsing uses `in user.lower()` which matches substrings
- "I want to commit later" triggers commit command!
- Use exact command words at start of input

---

## 🖥️ GUI COMMANDS

Use `gui_main_pro.py` for graphical interface

### Launch GUI

```bash
python gui_main_pro.py
```

### GUI Features

**Control Center:**
- Browse and select project directory
- Choose LLM provider (grok, openai, claude, ollama)
- Start/Stop MCP server

**File Explorer Tab:**
- Browse project files
- Preview file contents with syntax highlighting
- Pop out preview in separate window

**Diff Viewer Tab:**
- Review pending edits
- Approve or reject changes
- See before/after comparison

**Live Logs Tab:**
- Real-time server logs
- Filter by level (INFO, WARNING, ERROR)
- Search log entries
- Pop out logs window

**Memory Explorer Tab:**
- View all stored memories
- See conversation history
- Inspect context entries
- Refresh to reload

**Backups Tab:**
- List all .bak files
- View backup contents
- Restore from backup

---

## ⚙️ SETUP & CONFIGURATION

### Environment Variables

Create `.env` file in project root:

```bash
# Required for Grok
XAI_API_KEY=your_grok_api_key_here

# Required for OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Required for Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional API settings
API_HOST=127.0.0.1
API_PORT=8456
CORS_ORIGINS=*
```

### Configuration File

Edit `fgd_config.yaml`:

```yaml
watch_dir: "./your-project-directory"
memory_file: ".fgd_memory.json"
context_limit: 20

scan:
  max_dir_size_gb: 2
  max_files_per_scan: 5
  max_file_size_kb: 250

reference_dirs:
  - "/path/to/docs"
  - "/path/to/shared-lib"

llm:
  default_provider: "grok"  # or openai, claude, ollama
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

## 🔧 TROUBLESHOOTING

### "XAI_API_KEY not set" Error

**Problem:** Grok provider selected but API key missing

**Solution:**
```bash
export XAI_API_KEY="your_key_here"
# Or add to .env file
echo "XAI_API_KEY=your_key_here" >> .env
```

---

### "watch_dir is configured with a Windows-specific path"

**Problem:** Config has Windows path (C:\...) on Linux/Mac

**Solution:**
Edit `fgd_config.yaml`:
```yaml
# Change from:
watch_dir: "C:/Users/Admin/Desktop/project"

# To (Linux/Mac):
watch_dir: "/home/user/project"
# Or (relative):
watch_dir: "./project"
```

---

### MCP Server Not Starting

**Checklist:**
1. ✅ Check `watch_dir` exists and is writable
2. ✅ Verify API key is set for chosen provider
3. ✅ Check logs: `tail -f fgd_server.log`
4. ✅ Ensure no other process using same config file

---

### File Writes Not Working

**Possible Causes:**
1. **Silent write failure** - Check logs for errors
2. **Wrong directory** - Verify `watch_dir` in config
3. **Permissions** - Ensure directory is writable
4. **Path traversal block** - File path must be relative to watch_dir

---

### GUI Crashes on Startup

**Common Issues:**
1. **Missing dependencies** - Run `python test_setup.py`
2. **Invalid config** - Check `fgd_config.yaml` syntax
3. **Backend not found** - Ensure `mcp_backend.py` in same directory

**Solutions:**
```bash
# Install dependencies
pip install PyQt6 pyyaml watchdog aiohttp python-dotenv mcp

# Check for errors
python gui_main_pro.py 2>&1 | tee gui_errors.log
```

---

### Memory Not Persisting

**Check:**
1. `.fgd_memory.json` exists in watch_dir
2. File is writable (not read-only)
3. No race condition (multiple server instances)
4. Check logs for save errors

**Debug:**
```bash
# Verify memory file
cat .fgd_memory.json | jq .

# Watch for writes
watch -n 1 'ls -lh .fgd_memory.json'
```

---

### Git Commands Failing

**Requirements:**
1. ✅ Git installed: `git --version`
2. ✅ Git repository initialized: `ls -la .git`
3. ✅ Changes to commit: `git status`

**Solutions:**
```bash
# Initialize git repo
git init

# Configure git
git config user.name "Your Name"
git config user.email "you@example.com"
```

---

## 📊 RATE LIMITS

**API Endpoints:**
- Health check: 100/minute
- Status: 60/minute
- Start/Stop: 10/minute
- Logs: 30/minute
- Memory: 30/minute
- LLM Query: 20/minute
- Conversations: 30/minute
- Pending Edits: 60/minute
- Suggest: 30/minute

---

## 🔐 SECURITY NOTES

1. **API Keys**: Never commit `.env` file to git
2. **CORS**: Default allows all origins (*) - restrict in production
3. **Memory Files**: World-readable by default - contains sensitive data
4. **Logs**: May contain API responses - secure accordingly

---

**END OF COMMAND REFERENCE**
