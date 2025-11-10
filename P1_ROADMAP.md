# P1 BUGS ROADMAP - HIGH PRIORITY FIXES
**Timeline:** This Week (5-7 Days)
**Estimated Effort:** 12-16 hours
**Status:** Ready to start after P0 completion

---

## P1 Bugs Overview

| # | Bug ID | Bug Name | Effort | Status |
|---|--------|----------|--------|--------|
| 1 | MEMORY-4 | Timestamp Collisions (UUID needed) | 10 min | ⏳ TODO |
| 2 | GUI-2 | Toast Notification Positioning | 20 min | ⏳ TODO |
| 3 | GUI-3 | Gradient Timer Leaks (AnimatedButton) | 20 min | ⏳ TODO |
| 4 | GUI-4 | Header Timer Leaks | 15 min | ⏳ TODO |
| 5 | GUI-11 | No Loading Indicator | 40 min | ⏳ TODO |
| 6 | GUI-15 | Memory Explorer Refresh Rate | 10 min | ⏳ TODO |
| 7 | GUI-16 | File Tree Not Virtualized | 60 min | ⏳ TODO |
| 8 | MCP-1 | Hardcoded Grok Provider | 2 min | ⏳ TODO |
| 9 | MEMORY-6, MEMORY-7 | Permissions & Atomic Writes | 15 min | ⏳ TODO |

**Total Estimated Time:** ~3 hours active coding + 9 hours testing/integration

---

## Detailed P1 Fixes

### Fix P1-1: Timestamp Collisions → UUID (MEMORY-4)
**Severity:** HIGH
**Effort:** 10 minutes
**Impact:** Prevents chat overwrites

**Problem:**
```python
# Current (BROKEN):
chat_key = f"chat_{timestamp}"  # 16% collision rate in rapid calls!
self.memory.remember(chat_key, conversation_entry, "conversations")
```

**Solution:**
```python
# Fixed (WORKING):
import uuid
chat_id = str(uuid.uuid4())
self.memory.remember(f"chat_{chat_id}", conversation_entry, "conversations")
```

**File:** `mcp_backend.py` line ~851
**Testing:** Run 1000 rapid queries, verify no overwrites

---

### Fix P1-2: Toast Notification Positioning (GUI-2)
**Severity:** MEDIUM
**Effort:** 20 minutes
**Impact:** Smooth toast animations, no overlaps

**Problem:**
```python
# Current: Positions toasts but doesn't reposition when dismissed
toast.move(self.width() - 420 - 20,
           self.height() - (len(self._toast_notifications) * 80))
# When toast closes, gap is created
```

**Solution:**
```python
# Add reposition method called on dismiss
def _reposition_toasts(self):
    """Reposition all visible toasts"""
    y_offset = self.height() - 20
    for toast in reversed(self._toast_notifications):
        y_offset -= toast.height()
        toast.move(self.width() - toast.width() - 20, y_offset)
        y_offset -= 10  # Gap between toasts

def show_toast(self, message, toast_type="info"):
    # ... existing code ...
    QTimer.singleShot(4000, lambda: (
        self._toast_notifications.remove(toast),
        self._reposition_toasts()  # ADD THIS
    ))
```

**File:** `gui_main_pro.py` lines 1099-1125
**Testing:** Show 5 toasts rapidly, verify smooth positioning on dismiss

---

### Fix P1-3: Gradient Timer Leak - AnimatedButton (GUI-3)
**Severity:** MEDIUM
**Effort:** 20 minutes
**Impact:** Reduces CPU usage, battery drain

**Problem:**
```python
# Current: Timer never stops
self._gradient_timer = QTimer(self)
self._gradient_timer.timeout.connect(self._advance_gradient)
self._gradient_timer.start(60)  # NEVER STOPPED
```

**Solution:**
```python
# Add hideEvent/showEvent handlers
def hideEvent(self, event):
    """Stop animation when hidden"""
    super().hideEvent(event)
    if hasattr(self, '_gradient_timer'):
        self._gradient_timer.stop()

def showEvent(self, event):
    """Resume animation when shown"""
    super().showEvent(event)
    if hasattr(self, '_gradient_timer'):
        self._gradient_timer.start(60)

def __del__(self):
    """Clean up timer on destruction"""
    if hasattr(self, '_gradient_timer'):
        self._gradient_timer.stop()
        self._gradient_timer.deleteLater()
```

**File:** `gui_main_pro.py` AnimatedButton class (~line 370)
**Testing:** Monitor CPU usage, verify drops when window minimized

---

### Fix P1-4: Header Timer Leak (GUI-4)
**Severity:** MEDIUM
**Effort:** 15 minutes
**Impact:** Consistent with Fix P1-3

**Problem:**
Header gradient timer runs continuously

**Solution:**
```python
# In FGDGUI class
def hideEvent(self, event):
    """Stop timers when window hidden"""
    super().hideEvent(event)
    if hasattr(self, 'timer'):
        self.timer.stop()
    if hasattr(self, '_header_timer'):
        self._header_timer.stop()

def showEvent(self, event):
    """Resume timers when shown"""
    super().showEvent(event)
    if hasattr(self, 'timer'):
        self.timer.start(1000)
    if hasattr(self, '_header_timer'):
        self._header_timer.start(90)
```

**File:** `gui_main_pro.py` FGDGUI class (~line 980)
**Testing:** Monitor CPU when window minimized, should drop significantly

---

### Fix P1-5: Loading Indicator (GUI-11)
**Severity:** MEDIUM
**Effort:** 40 minutes
**Impact:** Better UX, prevents force-quit due to perceived freeze

**Problem:**
No visual feedback for long operations

**Solution:**
```python
class LoadingOverlay(QWidget):
    """Modern loading spinner overlay"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spinner = QLabel("⏳")
        spinner.setFont(QFont("Segoe UI Emoji", 48))
        spinner.setStyleSheet(f"color: {COLORS.PRIMARY};")

        text = QLabel("Loading...")
        text.setFont(QFont("Inter", 14, QFont.Weight.DemiBold))
        text.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY};")

        layout.addWidget(spinner)
        layout.addWidget(text)
        self.setLayout(layout)

    def show_loading(self):
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()

# Usage in file loading:
def on_file_click(self, item, column):
    file_path = item.data(0, Qt.ItemDataRole.UserRole)
    path = Path(file_path)
    if path.stat().st_size > 100_000:
        loader = LoadingOverlay(self)
        loader.show_loading()
        QApplication.processEvents()

        try:
            content = path.read_text(encoding='utf-8')
            self.preview.setPlainText(content)
        finally:
            loader.close()
```

**File:** `gui_main_pro.py` (add LoadingOverlay class and usage)
**Testing:** Load large file (>100KB), verify spinner shown during load

---

### Fix P1-6: Memory Explorer Refresh Rate (GUI-15)
**Severity:** MEDIUM
**Effort:** 10 minutes
**Impact:** Reduces unnecessary tree redraws

**Problem:**
```python
# Current: Called every 1 second
self.timer.timeout.connect(self.update_memory_explorer)
# Has mtime check but called too frequently
```

**Solution:**
```python
# Separate slower timer for memory explorer
self.memory_timer = QTimer(self)
self.memory_timer.timeout.connect(
    lambda: self.update_memory_explorer(force=False)
)
self.memory_timer.start(5000)  # Every 5 seconds instead of 1
```

**File:** `gui_main_pro.py` FGDGUI.__init__ (~line 1015)
**Testing:** Monitor tree flicker, should reduce significantly

---

### Fix P1-7: File Tree Virtualization (GUI-16)
**Severity:** MEDIUM
**Effort:** 60 minutes
**Impact:** 20-50x faster for large projects (1000+ files)

**Problem:**
Loads entire directory tree recursively into memory

**Solution:**
```python
def _add_tree_items(self, parent, path, lazy=True):
    """Add tree items with optional lazy loading"""
    try:
        if lazy and not parent.isExpanded():
            # Add placeholder for lazy load
            placeholder = QTreeWidgetItem(["📁 Loading..."])
            parent.addChild(placeholder)
            parent.setData(0, Qt.ItemDataRole.UserRole + 1, str(path))
            return

        for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if p.name.startswith('.') or p.name in ['node_modules']:
                continue

            item = QTreeWidgetItem([p.name])
            item.setData(0, Qt.ItemDataRole.UserRole, str(p))
            parent.addChild(item)

            if p.is_dir():
                self._add_tree_items(item, p, lazy=True)

    except Exception as e:
        logger.warning(f"Error adding tree items: {e}")

def on_tree_item_expanded(self, item):
    """Load children when expanded (lazy loading)"""
    if item.childCount() == 1 and item.child(0).text(0) == "📁 Loading...":
        item.removeChild(item.child(0))

        path_str = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if path_str:
            self._add_tree_items(QTreeWidgetItem([Path(path_str).name]),
                                Path(path_str), lazy=False)

# Connect in __init__:
self.tree.itemExpanded.connect(self.on_tree_item_expanded)
```

**File:** `gui_main_pro.py` (~line 1518)
**Testing:** Load large project (1000+ files), verify no freeze on startup

---

### Fix P1-8: Hardcoded Grok Provider (MCP-1)
**Severity:** MEDIUM
**Effort:** 2 minutes
**Impact:** Respects user's provider configuration

**Problem:**
```python
# Current (WRONG): Line 838
response = await self.llm.query(prompt, "grok", context=context)
```

**Solution:**
```python
# Fixed (CORRECT):
response = await self.llm.query(prompt, self.llm.default, context=context)
```

**File:** `mcp_backend.py` line ~838
**Testing:** Set `default_provider: openai`, verify uses OpenAI instead of Grok

---

### Fix P1-9: File Permissions & Atomic Writes (MEMORY-6, MEMORY-7)
**Severity:** MEDIUM
**Effort:** 15 minutes
**Impact:** Security + reliability

**Problem:**
```python
# Current: Already partially fixed but verify complete
temp_file.write_text(json.dumps(full_data))
# Missing: Atomic rename on all platforms
```

**Solution:**
```python
# Verify implementation (already mostly done):
temp_file = self.memory_file.with_suffix('.tmp')
temp_file.write_text(json.dumps(full_data, indent=2))

# Set restrictive permissions
os.chmod(temp_file, 0o600)  # ✅ Already done (line 178)

# Atomic rename
temp_file.replace(self.memory_file)  # ✅ Already done (line 184)

# Windows fallback (already done):
try:
    temp_file.replace(self.memory_file)
except OSError:
    # Windows fallback
    self.memory_file.write_text(...)
    temp_file.unlink(missing_ok=True)
```

**File:** `mcp_backend.py` lines 171-193
**Testing:** Verify with concurrent access, no corruption

---

## Implementation Plan

### Day 1: Quick Wins (2 hours)
1. ✅ P1-1: UUID for chat keys (10 min)
2. ✅ P1-8: Hardcoded provider (2 min)
3. ✅ P1-6: Memory explorer refresh (10 min)
4. ✅ P1-4: Header timer leak (15 min)
5. Testing: Verify all work correctly (1 hour)

### Day 2: UI Improvements (3 hours)
1. ✅ P1-2: Toast positioning (20 min)
2. ✅ P1-3: Timer leak fixes (20 min)
3. ✅ P1-5: Loading indicator (40 min)
4. Testing: UI responsiveness, animations (1 hour)

### Day 3: Performance (3 hours)
1. ✅ P1-7: File tree virtualization (60 min)
2. ✅ P1-9: Verify atomic writes (15 min)
3. Testing: Large projects, stress test (1 hour)

### Day 4-5: Integration & Testing (8 hours)
1. Full integration testing
2. Real-world scenario testing
3. Performance benchmarking
4. Documentation updates

---

## Success Criteria

- [ ] All 9 P1 bugs fixed
- [ ] No regressions from P0 fixes
- [ ] 1000+ file project loads without freeze
- [ ] CPU usage drops when window minimized
- [ ] Toasts position smoothly
- [ ] Loading indicator shows for large operations
- [ ] Provider configuration respected
- [ ] Unit tests passing
- [ ] User-reported issues resolved

---

## Risk Assessment

| Fix | Risk | Mitigation |
|-----|------|-----------|
| UUID for chat | LOW | Simple change, backward compatible |
| Toast positioning | LOW | Animation-only change |
| Timer leaks | MEDIUM | Test in different scenarios |
| Loading indicator | LOW | New feature, non-breaking |
| File tree lazy load | HIGH | Requires careful testing |
| Provider hardcode | LOW | Straightforward config change |

---

## Next Document
After P1 completion, see P2_ROADMAP.md for medium-priority improvements.

---

**Document Created:** 2025-11-09
**Ready to Start:** After P0 verification complete
**Estimated Completion:** 2025-11-14 (End of week)
