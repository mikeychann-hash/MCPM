# MCPM Memory & MCP Compatibility - Quick Reference

**Last Updated**: 2025-11-18

---

## Memory System Health Check

### ✅ Status: HEALTHY (No Critical Leaks)

| Aspect | Status | Details |
|--------|--------|---------|
| **Memory Leaks** | 🟢 None | LRU pruning at 1,000 entries |
| **Context Window** | 🟢 Healthy | Rolling 20-entry limit |
| **File Growth** | 🟡 Monitor | Could reach 100MB before prune (P1 fix recommended) |
| **LLM Integration** | 🟢 Active | Context auto-injected |
| **MCP Compatibility** | 🟢 Full | Works with all MCP 2.0 clients |

---

## Memory Storage

**File**: `.fgd_memory.json` (created in project directory)

**Structure**:
```json
{
  "memories": {
    "general": { "key1": {"value": "...", "timestamp": "...", "access_count": 5} },
    "conversations": { "chat_abc": {...} }
  },
  "context": [
    {"type": "file_read", "data": {...}, "timestamp": "..."},
    {"type": "file_edit", "data": {...}, "timestamp": "..."}
  ]
}
```

**Limits**:
- Max entries: **1,000** (LRU pruning)
- Context window: **20** (rolling)
- File size: Unlimited (⚠️ P1 fix recommended: 10MB limit)

---

## How LLMs Use Memory

**Every `llm_query` call includes**:
1. MCP server status (tools available, capabilities)
2. **Last 5 context entries** (recent file reads, edits, commits)

**Example Context Injected**:
```
=== MCP SERVER STATUS ===
Server: FGD MCP Server v6.0
Available Tools: [9 tools listed]
=== END MCP SERVER STATUS ===

=== RECENT ACTIVITY ===
[
  {"type": "file_edit", "data": {"path": "main.py", ...}, "timestamp": "..."},
  {"type": "git_commit", "data": {"message": "Fix bug"}, "timestamp": "..."}
]
=== END RECENT ACTIVITY ===

[User's actual prompt here]
```

**Result**: LLM has full awareness of recent actions.

---

## MCP Client Compatibility

### ✅ Fully Compatible Clients

| Client | Setup Difficulty | Notes |
|--------|------------------|-------|
| **Claude Desktop** | ⭐ Easy | Recommended - Best integration |
| **Claude CLI** | ⭐⭐ Medium | Official Anthropic CLI |
| **Codex CLI** | ⭐⭐ Medium | OpenAI Codex |
| **VS Code MCP Extensions** | ⭐⭐ Medium | Any MCP-compatible extension |
| **Custom Clients** | ⭐⭐⭐ Advanced | Any JSON-RPC 2.0/stdio client |

---

## Quick Setup: Claude Desktop

### macOS/Linux:
```bash
# 1. Find config location
# macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
# Linux: ~/.config/Claude/claude_desktop_config.json

# 2. Edit config
{
  "mcpServers": {
    "mcpm": {
      "command": "python",
      "args": [
        "/absolute/path/to/MCPM/mcp_backend.py",
        "/absolute/path/to/MCPM/fgd_config.yaml"
      ],
      "env": {
        "XAI_API_KEY": "your-key-here"
      }
    }
  }
}

# 3. Restart Claude Desktop
# 4. Tools appear in Claude Desktop interface
```

### Windows:
```powershell
# Config: %APPDATA%\Claude\claude_desktop_config.json
# Same JSON structure as above
```

---

## Quick Setup: Claude CLI

```bash
# Install
npm install -g @anthropic-ai/claude-cli

# Use MCPM
claude --mcp-server "python /path/to/MCPM/mcp_backend.py /path/to/MCPM/fgd_config.yaml"
```

---

## Available Tools (via MCP)

1. **list_directory** - Browse files (gitignore-aware)
2. **read_file** - Read file contents (250KB limit)
3. **write_file** - Atomic write + backup
4. **edit_file** - 2-step approval workflow
5. **create_directory** - Create with parents
6. **git_diff** - Show uncommitted changes
7. **git_commit** - Commit with validation
8. **git_log** - View commit history
9. **llm_query** - Query external LLMs (Grok/OpenAI/Claude/Ollama)

---

## Testing MCP Server

```bash
cd /home/user/MCPM
python mcp_backend.py fgd_config.yaml

# Send JSON-RPC request via stdin:
{"jsonrpc": "2.0", "method": "tools/list", "id": 1}

# Should receive tool list in stdout
```

---

## Memory Configuration

**File**: `fgd_config.yaml`

```yaml
context_limit: 20              # Rolling window (increase for more LLM context)
max_memory_entries: 1000       # LRU threshold (optional, default: 1000)
```

**Tuning**:
- **Small projects**: 20 context, 500 entries
- **Medium projects**: 50 context, 1000 entries
- **Large projects**: 100 context, 2000 entries (⚠️ watch file size)

---

## Common Issues

### Issue: Memory file growing too large
**Solution**: Add file size limit (see TODO.md P1-7)

### Issue: LLM lacks recent context
**Solution**: Increase `context_limit` in fgd_config.yaml

### Issue: Claude Desktop doesn't see tools
**Solutions**:
1. Check absolute paths in config (not relative!)
2. Restart Claude Desktop
3. Check logs: `~/Library/Logs/Claude/` (macOS)

### Issue: "Invalid JSON-RPC" errors
**Solution**: Don't run mcp_backend.py manually - use via MCP client

---

## Monitoring Memory

**Check memory file size**:
```bash
ls -lh .fgd_memory.json
```

**View memory contents**:
```bash
cat .fgd_memory.json | python -m json.tool | less
```

**Count entries**:
```bash
python -c "import json; data = json.load(open('.fgd_memory.json')); print(sum(len(v) for v in data['memories'].values()))"
```

---

## Recommendations

### P1 (High Priority)
- [ ] Add 10MB file size limit (TODO.md P1-7)
- [ ] Limit context entry size to 10KB (TODO.md P1-10)

### P2 (Nice to Have)
- [ ] Batch recall() saves for performance
- [ ] Add memory statistics API
- [ ] Memory export/import tools

---

## Resources

- **Full Analysis**: MEMORY_ANALYSIS_MCP_COMPATIBILITY.md
- **Architecture**: ARCHITECTURE_MAP.md
- **TODO List**: TODO.md
- **MCP Spec**: https://spec.modelcontextprotocol.io/

---

**Quick Reference** | MCPM v6.0
