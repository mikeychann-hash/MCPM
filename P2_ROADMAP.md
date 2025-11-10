# P2 BUGS ROADMAP - MEDIUM PRIORITY FIXES
**Timeline:** Next 2 Weeks (2025-11-21 to 2025-11-28)
**Estimated Effort:** 10-12 hours
**Status:** Ready to start after P1 completion

---

## P2 Bugs Overview

| # | Bug ID | Bug Name | Effort | Priority | Status |
|---|--------|----------|--------|----------|--------|
| 1 | MCP-CONN | File Write/List Failures | 2-3 hrs | 🔴 CRITICAL | ⏳ URGENT |
| 2 | MEMORY-5 | Unbounded Memory Growth | 30 min | 🟡 HIGH | ⏳ TODO |
| 3 | MCP-2 | No Startup Validation | 15 min | 🟡 HIGH | ⏳ TODO |
| 4 | MCP-3 | Fixed Timeout | 10 min | 🟡 HIGH | ⏳ TODO |
| 5 | GUI-6/7/8 | Window Persistence | 45 min | 🟠 MEDIUM | ⏳ TODO |
| 6 | GUI-20 | Keyboard Shortcuts | 30 min | 🟠 MEDIUM | ⏳ TODO |

**Total Estimated Time:** 3.5-4.5 hours coding + 5-6 hours testing
**Timeline:** Complete by 2025-11-28

---

## URGENT: MCP Connection Issues (HIGH PRIORITY)

### MCP-CONN: File Write/List Failures
**Severity:** 🔴 CRITICAL (Blocking tool reliability)
**Effort:** 2-3 hours
**Impact:** Core tool functionality broken, Grok receives false success messages
**Status:** Ready to implement immediately

**Problem:**
- Write operations don't create parent directories
- List operations return empty results without explanation
- No content verification after write
- Error messages lack context for debugging
- Grok believes operations succeeded when they fail

**Solution Details:**
See MCP_CONNECTION_ISSUES.md for comprehensive analysis

**Implementation Checklist:**
- [ ] Add parent directory creation to write_file (lines 826-853)
- [ ] Add detailed list_directory response (lines 790-805)
- [ ] Implement content verification after write
- [ ] Add error context helper method
- [ ] Create new create_directory tool
- [ ] Test all edge cases
- [ ] Verify Grok integration works

**Files to Modify:**
- mcp_backend.py: write_file implementation
- mcp_backend.py: list_directory implementation
- mcp_backend.py: tool definitions
- mcp_backend.py: add helper methods

**Timeline:** 2025-11-10 (TOMORROW - before other P2 work)

---

## P2-1: Unbounded Memory Growth (MEMORY-5)

**Severity:** MEDIUM
**Effort:** 30 minutes
**Impact:** Prevents memory file from growing unboundedly

**Problem:**
```python
# Current: No size limits
self.memories[category][key] = {
    "value": value,
    "timestamp": datetime.now().isoformat(),
    "access_count": 0
}
# Memory grows forever!
```

**Solution:**
```python
# 1. Add max_memory_size config
MAX_MEMORY_SIZE = 10_000_000  # 10MB max

# 2. Implement pruning
def _prune_memory(self):
    """Remove old/unused entries when size exceeds limit"""
    # Get memory file size
    if self.memory_file.stat().st_size > self.MAX_MEMORY_SIZE:
        # Remove entries with lowest access_count
        # Keep recent entries (based on timestamp)
        # Implement LRU (Least Recently Used) strategy

# 3. Call pruning periodically or on write
```

**File:** mcp_backend.py (MemoryStore class)
**Timeline:** 2025-11-21

---

## P2-2: No Startup Validation (MCP-2)

**Severity:** MEDIUM
**Effort:** 15 minutes
**Impact:** Provides clear error messages if config is wrong

**Problem:**
```python
# Current: Fails at first tool call
# No validation that provider is accessible
# User doesn't know what's wrong
```

**Solution:**
```python
def _validate_startup(self):
    """Validate all provider credentials at startup"""
    providers = self.config.get('llm', {}).get('providers', {})
    default = self.config.get('llm', {}).get('default_provider')

    # Check if default provider is configured
    if default not in providers:
        raise ValueError(f"Default provider '{default}' not in configured providers")

    # Check for required env variables
    if default == 'grok' and not os.getenv("XAI_API_KEY"):
        raise ValueError("XAI_API_KEY environment variable required for Grok")

    if default == 'openai' and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable required for OpenAI")

    if default == 'claude' and not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable required for Claude")

    logger.info(f"✅ Startup validation passed for provider: {default}")
```

**File:** mcp_backend.py (__init__ method)
**Timeline:** 2025-11-21

---

## P2-3: Fixed Timeout (MCP-3)

**Severity:** MEDIUM
**Effort:** 10 minutes
**Impact:** Allows users to configure timeout for different network conditions

**Problem:**
```python
# Current: Hardcoded timeout
timeout=30  # Always 30 seconds
```

**Solution:**
```python
# 1. Add to config file
llm:
  timeout_seconds: 30  # Configurable

# 2. Use in queries
def query(self, prompt, provider, timeout=None):
    timeout = timeout or self.config.get('llm', {}).get('timeout_seconds', 30)
    response = await self.llm.query(prompt, provider, timeout=timeout)

# 3. Document in config template
```

**Files:**
- mcp_backend.py: LLMBackend class
- fgd_config.yaml: Add timeout_seconds option

**Timeline:** 2025-11-21

---

## P2-4: Window Persistence (GUI-6/7/8)

**Severity:** MEDIUM
**Effort:** 45 minutes
**Impact:** Remember window size, position, and splitter state

**Problem:**
```python
# Current: Window always opens at default size/position
# User has to resize every time
```

**Solution:**
```python
def _save_session(self):
    """Save window state"""
    self.settings.setValue("window_geometry", self.saveGeometry())
    self.settings.setValue("window_state", self.saveState())
    self.settings.setValue("splitter_sizes", self.splitter.sizes())

def _restore_session(self):
    """Restore window state"""
    geometry = self.settings.value("window_geometry")
    if geometry:
        self.restoreGeometry(geometry)

    state = self.settings.value("window_state")
    if state:
        self.restoreState(state)

    sizes = self.settings.value("splitter_sizes")
    if sizes:
        self.splitter.setSizes(sizes)

# Call in __init__ and closeEvent
```

**File:** gui_main_pro.py (FGDGUI class)
**Timeline:** 2025-11-28

---

## P2-5: Keyboard Shortcuts (GUI-20)

**Severity:** MEDIUM
**Effort:** 30 minutes
**Impact:** Professional keyboard navigation

**Problem:**
```python
# Current: No keyboard shortcuts
# Users must use mouse for everything
```

**Solution:**
```python
def _setup_shortcuts(self):
    """Setup keyboard shortcuts"""
    shortcuts = {
        "Ctrl+O": ("Open project", self.on_open_project),
        "Ctrl+S": ("Save", self.on_save),
        "Ctrl+L": ("Clear log", self.on_clear_log),
        "Ctrl+Q": ("Quit", self.close),
        "Ctrl+N": ("New file", self.on_new_file),
        "Ctrl+R": ("Refresh", self.on_refresh),
        "F5": ("Run", self.on_run),
        "F10": ("Debug", self.on_debug),
    }

    for shortcut, (tooltip, handler) in shortcuts.items():
        action = QAction(tooltip, self)
        action.setShortcut(shortcut)
        action.triggered.connect(handler)
        self.addAction(action)

    logger.info(f"✅ Registered {len(shortcuts)} keyboard shortcuts")
```

**File:** gui_main_pro.py (FGDGUI class)
**Timeline:** 2025-11-28

---

## Implementation Schedule

### Week 1: Critical MCP Fixes
**Date:** 2025-11-10 (TOMORROW)
**Focus:** Fix file operation issues

1. **Day 1 (2025-11-10):** MCP-CONN (4 hours)
   - Implement write_file parent directory creation
   - Implement list_directory detailed response
   - Add content verification
   - Test with Grok

2. **Day 2 (2025-11-11):** Testing & Validation (3 hours)
   - Test all edge cases
   - Verify Grok integration
   - Performance test

### Week 2: Core P2 Fixes
**Date:** 2025-11-21 (Following week)
**Focus:** Feature improvements

1. **Day 1 (2025-11-21):** Quick Wins (1 hour)
   - P2-2: Startup validation (15 min)
   - P2-3: Timeout configuration (10 min)
   - P2-1: Memory pruning (30 min)
   - Testing (5 min)

2. **Days 2-3 (2025-11-22 to 2025-11-23):** UI Improvements (2 hours)
   - P2-4: Window persistence (1 hour)
   - P2-5: Keyboard shortcuts (1 hour)
   - Testing (15 min)

3. **Days 4-5 (2025-11-24 to 2025-11-28):** Integration & Testing (2 hours)
   - Full system testing
   - Performance benchmarking
   - Documentation updates

---

## Success Criteria

- [ ] MCP file operations work reliably
- [ ] Parent directories created automatically
- [ ] List operations explain filtering
- [ ] All errors include helpful context
- [ ] Grok receives accurate success/failure messages
- [ ] Memory size bounded with pruning
- [ ] Startup validation prevents cryptic errors
- [ ] Timeout is configurable
- [ ] Window state persists between sessions
- [ ] Keyboard shortcuts work
- [ ] All P2 bugs fixed and verified
- [ ] No regressions from P0/P1 fixes

---

## Risk Assessment

| Fix | Risk | Mitigation |
|-----|------|-----------|
| MCP file operations | MEDIUM | Comprehensive testing required |
| Memory pruning | LOW | LRU strategy well-established |
| Startup validation | LOW | Clear error messages |
| Timeout config | LOW | Backward compatible |
| Window persistence | LOW | Native Qt functionality |
| Keyboard shortcuts | LOW | Standard Qt approach |

---

## Dependencies

- P0 fixes (COMPLETE ✅)
- P1 fixes (COMPLETE ✅)
- MCP backend running
- Test environment ready

---

## Next Steps

1. **Immediate (Today):** Plan MCP fixes
2. **Tomorrow (2025-11-10):** Implement MCP-CONN critical fixes
3. **By 2025-11-21:** Complete all P2-1 to P2-3
4. **By 2025-11-28:** Complete all P2 fixes
5. **By 2025-12-01:** Production deployment

---

**Document Created:** 2025-11-09
**Ready to Start:** 2025-11-10 (MCP-CONN critical)
**Estimated Completion:** 2025-11-28
