# MCPM Comprehensive Bug Report
**Date:** 2025-11-08
**Focus:** GUI and Backend Critical Issues

---

## 🚨 CRITICAL BUGS (High Priority)

### gui_main_pro.py

#### 1. **Race Condition in Subprocess Output Reading** (Lines 1555-1595)
**Severity:** HIGH
**Location:** `_read_subprocess_stdout()` and `_read_subprocess_stderr()`
**Issue:** The background threads use `readline()` which can block indefinitely if the subprocess doesn't flush output or hangs. Daemon threads won't exit cleanly when the main program closes.
**Impact:** Potential zombie threads, resource leaks, and application hang on exit.
**Fix Required:** Implement non-blocking I/O or use `select`/`poll` with timeout.

```python
# Current problematic code:
def _read_subprocess_stdout(self):
    try:
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()  # BLOCKS INDEFINITELY
                if not line:
                    break
```

#### 2. **Unchecked Process State Access** (Line 1598)
**Severity:** HIGH
**Location:** `toggle_server()`
**Issue:** `self.process.poll()` is called without checking if process object is in valid state. Can raise AttributeError or OSError.
**Impact:** Application crash when toggling server if process is in invalid state.
**Fix Required:** Add try-except around `poll()` call.

```python
# Current code:
if self.process and self.process.poll() is None:  # poll() can raise!
```

#### 3. **Memory Leak in Log Viewer** (Lines 1704-1736)
**Severity:** HIGH
**Location:** `update_logs()`
**Issue:** Entire log file is read into memory every second with no size check. As logs grow (MB+), this causes severe performance degradation and eventual OOM.
**Impact:** GUI freezes, high CPU usage, memory exhaustion on long-running servers.
**Fix Required:** Implement log rotation, pagination, or tail-only reading.

```python
# Current code reads ENTIRE file every second:
lines = self.log_file.read_text().splitlines()  # NO SIZE CHECK!
```

#### 4. **Path Resolution Fragility** (Lines 1664-1671)
**Severity:** HIGH
**Location:** `start_server()`
**Issue:** Backend script path constructed from `__file__` will fail if GUI is:
- Run from different directory
- Frozen with PyInstaller/cx_Freeze
- Symlinked
**Impact:** Server fails to start with cryptic error.
**Fix Required:** Use proper resource path resolution or require backend in same directory.

```python
# Current fragile code:
backend_script = mcpm_root / "mcp_backend.py"
if not backend_script.exists():  # Will fail in many scenarios
```

---

### mcp_backend.py

#### 5. **Race Condition in Approval File Handling** (Lines 336-388)
**Severity:** CRITICAL
**Location:** `_approval_monitor_loop()`
**Issue:** Approval file is read and deleted without file locking. If multiple processes or the GUI accesses simultaneously, data corruption or lost approvals can occur.
**Impact:** Lost edit approvals, file corruption, inconsistent state.
**Fix Required:** Implement file locking (fcntl on Unix, msvcrt on Windows) or use atomic operations.

```python
# Current code has NO LOCKING:
approval_data = json.loads(approval_file.read_text())
# ... process ...
approval_file.unlink()  # Race condition if GUI writes simultaneously
```

#### 6. **Silent File Watcher Failure** (Lines 315-323)
**Severity:** HIGH
**Location:** `_start_watcher()`
**Issue:** If file watcher fails to start (permissions, inotify limits), the exception is caught and only logged as warning. Server continues without change detection.
**Impact:** File changes not detected, broken functionality with no user notification.
**Fix Required:** Fail fast or prominently warn user.

```python
# Current code:
except Exception as e:
    logger.warning(f"File watcher failed: {e}")  # Server continues broken!
```

#### 7. **Unbounded Memory Growth** (Lines 115-119)
**Severity:** MEDIUM-HIGH
**Location:** `MemoryStore.add_context()`
**Issue:** Context is limited to `context_limit` entries, but old entries are discarded without archiving. Long-running servers lose important historical context.
**Impact:** Context loss, no audit trail, debugging difficulties.
**Fix Required:** Implement context archiving or rotation to separate file.

#### 8. **Incomplete .gitignore Support** (Lines 436-460)
**Severity:** MEDIUM
**Location:** `_matches_gitignore()`
**Issue:** Uses `fnmatch` which doesn't support:
- Negation patterns (`!important.log`)
- Double-asterisk globbing (`**/test/*.py`)
- Full .gitignore specification
**Impact:** Files incorrectly ignored or included.
**Fix Required:** Use proper gitignore library (e.g., `pathspec`).

#### 9. **Ambiguous Edit Detection** (Lines 674-679)
**Severity:** MEDIUM
**Location:** `edit_file` tool
**Issue:** Only checks if `old_text` exists in file, not if it appears multiple times. If text appears multiple times, wrong occurrence might be replaced.
**Impact:** Incorrect edits, data corruption.
**Fix Required:** Require exact match or line number specification.

```python
# Current code:
if old_text not in content:
    return [TextContent(type="text", text="Old text not found")]
# But what if old_text appears 5 times?
```

#### 10. **Git Operations Without Timeout** (Lines 476-491, 751-820)
**Severity:** MEDIUM
**Location:** `_check_git_available()`, `git_diff`, `git_log`
**Issue:** Git commands run without timeout. If git hangs (network repo, corrupted index), the server hangs.
**Impact:** Server deadlock, unresponsive application.
**Fix Required:** Add timeout to all git subprocess calls.

---

### server.py (API Server)

#### 11. **Silent Provider Validation Failure** (Lines 106-113)
**Severity:** MEDIUM
**Location:** `StartRequest.validate_provider()`
**Issue:** Invalid provider is silently converted to 'grok' with only a log warning. User doesn't know their requested provider was ignored.
**Impact:** Unexpected behavior, wrong LLM used.
**Fix Required:** Raise ValidationError for invalid providers.

```python
# Current code:
if v not in valid_providers:
    logger.warning(f"Invalid provider '{v}', falling back to 'grok'")
    return 'grok'  # SILENT FAILURE
```

#### 12. **Denial of Service via Directory Traversal** (Lines 195-198)
**Severity:** HIGH (Security)
**Location:** `/api/suggest` endpoint
**Issue:** Uses `rglob("*")` on filesystem without depth limit. Attacker can cause DoS by requesting suggestion on root directory.
**Impact:** Server hang, resource exhaustion.
**Fix Required:** Limit recursion depth and total files scanned.

```python
# Current code:
dirs = [str(p.relative_to(base)) for p in base.rglob("*") if p.is_dir()]
# No depth limit! Can scan entire filesystem!
```

#### 13. **Race Condition in Server State** (Lines 269-289)
**Severity:** MEDIUM
**Location:** `/api/start` endpoint
**Issue:** `RUN` dictionary is modified without locking. Concurrent API requests can cause race conditions.
**Impact:** Corrupted server state, crashes.
**Fix Required:** Use threading lock or asyncio lock for RUN dict.

#### 14. **Private Method Encapsulation Violation** (Line 474)
**Severity:** LOW-MEDIUM
**Location:** `/api/llm_query` endpoint
**Issue:** Calls `RUN["server"]._get_mcp_status_context()` - private method from another class.
**Impact:** Brittle code, breaks if backend refactored.
**Fix Required:** Make method public or use proper interface.

---

## ⚠️ MODERATE BUGS

### gui_main_pro.py

#### 15. **Toast Notification Memory Leak** (Line 996)
**Severity:** MEDIUM
**Location:** `show_toast()`
**Issue:** Toast removal lambda can fail if toast already removed, and positions aren't recalculated when toasts close.
**Impact:** Overlapping toasts, memory leak with many notifications.
**Fix Required:** Use WeakSet or proper cleanup mechanism.

#### 16. **Timestamp Comparison Fragility** (Lines 1828-1830)
**Severity:** MEDIUM
**Location:** `check_pending_edits()`
**Issue:** Timestamp comparison uses string equality which works but is fragile.
**Impact:** Changes missed if timestamp format varies.
**Fix Required:** Parse timestamps and compare as datetime objects.

```python
# Current fragile code:
if self.pending_edit and self.pending_edit.get("timestamp") == pending_data.get("timestamp"):
    return  # String equality!
```

#### 17. **Duplicate Process Termination Logic** (Lines 1597-1626, 2030-2045)
**Severity:** LOW-MEDIUM
**Location:** `toggle_server()` and `closeEvent()`
**Issue:** Process termination logic duplicated in two places. Maintenance burden and potential inconsistency.
**Impact:** Code smell, harder to maintain.
**Fix Required:** Extract to `_terminate_process()` method.

#### 18. **Memory Update Race Condition** (Lines 1754-1756)
**Severity:** LOW
**Location:** `update_memory_explorer()`
**Issue:** Uses file mtime for change detection. If file written multiple times in same second, changes missed.
**Impact:** Stale memory view.
**Fix Required:** Use file hash or content comparison.

#### 19. **Missing Highlighter Cleanup** (Line 1236)
**Severity:** LOW
**Location:** `_create_explorer_tab()`
**Issue:** Syntax highlighter created but not stored for cleanup or reconfiguration.
**Impact:** Minor resource leak.
**Fix Required:** Store as `self.preview_highlighter` (it's done correctly elsewhere).

---

### mcp_backend.py

#### 20. **Missing Memory Save Retry Logic** (Lines 80-94)
**Severity:** MEDIUM
**Location:** `MemoryStore._save()`
**Issue:** No retry mechanism for transient failures (disk full, temporary permissions issues).
**Impact:** Lost memory data.
**Fix Required:** Implement exponential backoff retry.

#### 21. **Generic Exception Handling Loses Context** (Lines 206-212)
**Severity:** LOW-MEDIUM
**Location:** `LLMBackend.query()`
**Issue:** Catches generic Exception, loses specific error information for debugging.
**Impact:** Hard to diagnose LLM failures.
**Fix Required:** Catch specific exception types separately.

#### 22. **Hardcoded Timeout** (Line 139)
**Severity:** LOW
**Location:** `LLMBackend.query()`
**Issue:** 30-second timeout hardcoded for all LLM providers. Some might need longer (complex prompts) or shorter.
**Impact:** Premature timeouts or excessive waits.
**Fix Required:** Make timeout configurable per provider.

#### 23. **File Size Limit Without Chunking** (Lines 622-634)
**Severity:** MEDIUM
**Location:** `read_file` tool
**Issue:** 250KB file size limit with no way to read larger files in chunks.
**Impact:** Large files completely inaccessible.
**Fix Required:** Add chunk reading support or increase limit with warning.

#### 24. **Git Add All Behavior** (Line 785)
**Severity:** MEDIUM
**Location:** `git_commit` tool
**Issue:** Runs `git add .` which stages ALL changes. User might want selective commits.
**Impact:** Unintended files committed.
**Fix Required:** Add parameter to specify files to commit.

```python
# Current code:
subprocess.run(["git", "add", "."], ...)  # Adds EVERYTHING
```

---

## 🔍 MINOR BUGS & CODE SMELLS

### gui_main_pro.py

#### 25. **Multiline Highlighting Edge Case** (Lines 305-306)
**Severity:** LOW
**Location:** `PythonHighlighter._match_multiline()`
**Issue:** Complex boolean return logic might not handle all edge cases correctly.
**Impact:** Occasional syntax highlighting glitches.

#### 26. **Property Naming Convention** (Lines 467-468)
**Severity:** VERY LOW
**Location:** `AnimatedButton`
**Issue:** PyQt properties use camelCase (`hoverProgress`) instead of Python snake_case.
**Impact:** Style inconsistency.

#### 27. **No Backend Validation Before Launch** (Lines 1677-1690)
**Severity:** LOW
**Location:** `start_server()`
**Issue:** Only checks if backend script exists, doesn't validate it's executable or correct version.
**Impact:** Cryptic startup failures.

---

### server.py

#### 28. **Deprecated FastAPI Event Handlers** (Lines 614-640)
**Severity:** LOW
**Location:** `startup_event()`, `shutdown_event()`
**Issue:** Uses deprecated `@app.on_event()` decorator. Should use lifespan context manager.
**Impact:** Will break in future FastAPI versions.

#### 29. **Arbitrary Suggestion Limit** (Line 198)
**Severity:** VERY LOW
**Location:** `/api/suggest` endpoint
**Issue:** Hardcoded 100 directory limit with no explanation.
**Impact:** Inconsistent user experience.

---

### claude_bridge.py

#### 30. **Fragile Command Parsing** (Lines 74-101)
**Severity:** MEDIUM
**Location:** Main command loop
**Issue:** Uses `"command" in user.lower()` which matches ANY string containing the word (e.g., "I want to commit later" triggers commit).
**Impact:** Unintended command execution.
**Fix Required:** Use proper command parsing with exact match or regex.

```python
# Current fragile code:
elif command == "commit" or "commit" in user.lower():
    # Matches "I don't want to commit" !!
```

#### 31. **Fallback Parsing Loses Quoted Paths** (Lines 38-41)
**Severity:** LOW
**Location:** `parse_command()`
**Issue:** If `shlex.split()` fails, falls back to simple split, losing quoted path support.
**Impact:** Paths with spaces break.

---

### test_path_validation.py

#### 32. **Incomplete Windows Path Detection** (Lines 18-20)
**Severity:** LOW
**Location:** `validate_paths()`
**Issue:** Regex doesn't handle UNC paths (`\\server\share`), network paths, or other Windows formats.
**Impact:** False negatives on validation.

---

### test_watch_dir_validation.py

#### 33. **Hacky Test Object Creation** (Lines 12-14)
**Severity:** VERY LOW
**Location:** `_make_server()`
**Issue:** Creates server object without calling `__init__` using `object.__new__()`. Brittle if `__init__` changes.
**Impact:** Tests might not catch real initialization bugs.

---

## 🛡️ SECURITY CONCERNS

### 1. **Path Traversal Risk**
**Location:** mcp_backend.py `_sanitize()` (Line 416-421)
**Issue:** While there's path traversal protection, it relies on string prefix checking which can be bypassed with symlinks.
**Fix Required:** Use `os.path.realpath()` and compare canonical paths.

### 2. **No Input Sanitization on Edit Operations**
**Location:** mcp_backend.py `edit_file` (Lines 667-741)
**Issue:** Old text and new text parameters not sanitized. Could contain malicious content.
**Impact:** Potential code injection if misused.

### 3. **Unrestricted Git Command Execution**
**Location:** mcp_backend.py git commands (Lines 751-820)
**Issue:** Git commands run with user-provided input (commit messages, file paths) without sanitization.
**Impact:** Command injection risk.

---

## 📊 PERFORMANCE ISSUES

### 1. **Log File Reading** (gui_main_pro.py:1704-1736)
- Reading entire log file every second without size check
- Can cause UI freezes with large logs (10MB+)

### 2. **Directory Recursion** (server.py:195-198)
- Unbounded `rglob("*")` can scan millions of files
- DoS vulnerability

### 3. **Memory Store Growing Unbounded** (mcp_backend.py:96-104)
- Memories dict never pruned, only context limited
- Long-running servers accumulate data

---

## 🧪 TESTING GAPS

### Missing Test Coverage:
1. **No GUI tests** - Critical UI logic untested
2. **No integration tests** - Components tested in isolation only
3. **No error injection tests** - Failure scenarios not tested
4. **No performance tests** - No regression detection for perf issues
5. **No security tests** - Path traversal, injection not tested

---

## 🎯 RECOMMENDED IMMEDIATE FIXES

### Priority 1 (Fix This Week):
1. ✅ Add timeout to subprocess readline operations
2. ✅ Implement file locking for approval files
3. ✅ Add log file size check before reading
4. ✅ Fix path resolution for frozen/packaged apps
5. ✅ Add race condition protection for RUN dict

### Priority 2 (Fix This Month):
1. Implement log rotation/pagination
2. Add retry logic to memory saves
3. Fix .gitignore parsing with proper library
4. Add timeout to all git operations
5. Improve command parsing in CLI bridge

### Priority 3 (Technical Debt):
1. Migrate FastAPI to lifespan handlers
2. Refactor duplicate process termination code
3. Add comprehensive test suite
4. Implement security hardening
5. Add performance monitoring

---

## 📝 ADDITIONAL NOTES

### Code Quality Observations:
- **Overall:** Code is well-structured but has production-readiness gaps
- **Error Handling:** Inconsistent - some places excellent, others swallow errors
- **Logging:** Good coverage but could be more structured (JSON logs)
- **Documentation:** Minimal inline comments, could use more docstrings
- **Type Hints:** Partial coverage, should be comprehensive

### Architecture Concerns:
- **Tight Coupling:** GUI directly manages backend process, should use proper IPC
- **State Management:** Global `RUN` dict in server.py is anti-pattern
- **Resource Cleanup:** Inconsistent cleanup on failures
- **Configuration:** Hardcoded values should be in config files

---

**END OF REPORT**
