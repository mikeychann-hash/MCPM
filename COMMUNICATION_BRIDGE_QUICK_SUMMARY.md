# MCPM Communication Bridge - Quick Reference Summary

## Key Findings

### Architecture
- **Pure Python** (no Node.js ↔ Python bridge exists)
- 3-layer architecture: GUI (PyQt6) → MCP Backend (Python) → Tools
- Communication: **stdio with JSON-RPC 2.0 protocol**
- No Redis integration found

### Critical P0 Issues (Must Fix)

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 1 | JSON-RPC exception re-raise crashes server | mcp_backend.py:1328 | Server crashes on invalid input |
| 2 | Daemon thread race condition on shutdown | gui_main_pro.py:1796 | AttributeError in background threads |
| 3 | Subprocess output buffers may deadlock | gui_main_pro.py:1862-1869 | Process hangs indefinitely |
| 4 | File lock timeout returns empty data | mcp_backend.py:153-155 | Silent data loss in memory store |
| 5 | Subprocess output data loss on termination | gui_main_pro.py:1737-1753 | Last log entries missing |

### Reliability P1 Issues (Should Fix)

| # | Issue | Impact |
|---|-------|--------|
| 1 | No tool argument validation | Unhandled KeyError on malformed requests |
| 2 | Blocking subprocess calls in async context | Event loop blocks, all requests wait 30s |
| 3 | Memory growth unbounded | Memory files grow to 100MB+ |
| 4 | File-based approval workflow racing | Edit requests can get lost |
| 5 | Git commands without user config | Commits fail without git.user.name |
| 6 | LLM context not size-limited | Can exceed token limits silently |

### Performance P2 Opportunities

| Optimization | Current | Potential Gain |
|---|---|---|
| File polling consolidation | 3 stat calls/100ms | -2 calls (67% reduction) |
| Watchdog directory filtering | All files watched | 10x fewer events on large repos |
| Git operation caching | Fresh subprocess each time | Avoid 90% of calls |
| Memory implementation | 100% serialization on each save | Incremental updates possible |

### Communication Flow

```
GUI (PyQt6)
  ↓ subprocess.Popen()
MCP Backend (Python process)
  ↓ stdio JSON-RPC 2.0
Tools (9 total):
  - read_file, write_file, edit_file
  - list_directory, create_directory
  - git_diff, git_commit, git_log
  - llm_query
  
Reverse: File-based signaling
  pending_edit.json → (GUI polls every 100ms)
  approval.json ← (Backend monitors every 2s)
```

### Code Quality Metrics

| Metric | Rating | Notes |
|--------|--------|-------|
| JSON-RPC Protocol | 7/10 | Core protocol solid, error handling weak |
| Serialization | 9/10 | Atomic writes, proper JSON handling |
| Process Lifecycle | 5/10 | 3 P0 issues with threads/pipes |
| File Locking | 6/10 | Implemented but timeout too aggressive |
| Async Patterns | 6/10 | Blocking calls defeat async benefits |
| Error Handling | 6/10 | Logging good, validation missing |
| Security | 6/10 | Path validation solid, env vars exposed |
| Overall | **7/10** | Solid foundation with critical gaps |

### Recommended Fix Priority

**Week 1 (P0 Critical):**
1. Fix JSON-RPC exception handling (1h)
2. Replace daemon thread checks with stop flag (2h)
3. Implement output reader with timeout (2h)
4. Change FileLock timeout to re-raise (1h)
5. Read remaining subprocess buffer on exit (2h)

**Week 2-3 (P1 Reliability):**
1. Add argument validation schema (4h)
2. Wrap subprocess calls with asyncio.to_thread() (3h)
3. Implement size-aware memory pruning (3h)
4. Add UUID to approval workflow (2h)
5. Set GIT_AUTHOR environment variables (1h)
6. Validate LLM context token count (2h)

**Week 4+ (P2 Optimization):**
- Consolidate file polling checks
- Add watchdog filters for common patterns
- Implement git operation caching
- Migrate from file-based IPC to message queue

### Full Report Location
- `/home/user/MCPM/COMMUNICATION_BRIDGE_ANALYSIS.md` (1003 lines, 31KB)

### Key Code Files
- MCP Backend: `/home/user/MCPM/mcp_backend.py` (1375 lines)
- GUI: `/home/user/MCPM/gui_main_pro.py` (2200+ lines)
- REST API: `/home/user/MCPM/server.py` (665 lines)
- CLI Bridge: `/home/user/MCPM/claude_bridge.py` (106 lines)

