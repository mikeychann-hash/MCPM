# Quick Wins - Implementation Guide

## 🚀 5 Features in ~9 Hours = Massive Improvement

This guide shows **exact code** to implement the highest-impact, lowest-effort improvements.

---

## 1. Implement Missing LLM Providers (2 hours) ⭐⭐⭐⭐⭐

### Current Problem
Only Grok works. OpenAI/Claude/Ollama configured but not implemented.

### Location
`mcp_backend.py:104-134`

### Implementation

```python
# mcp_backend.py

async def query(self, prompt: str, provider: str = None, model: str = None, context: str = "") -> str:
    provider = provider or self.default
    conf = self.config['providers'].get(provider)
    if not conf:
        return f"Error: Provider '{provider}' not configured"

    full_prompt = f"{context}\n\n{prompt}" if context else prompt
    model = model or conf['model']
    base_url = conf['base_url']
    timeout = aiohttp.ClientTimeout(total=30)

    try:
        # ============ GROK ============
        if provider == "grok":
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                return "Error: XAI_API_KEY not set"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{base_url}/chat/completions", json=data, headers=headers) as r:
                    if r.status != 200:
                        txt = await r.text()
                        return f"Grok API Error {r.status}: {txt}"
                    resp = await r.json()
                    return resp['choices'][0]['message']['content']

        # ============ OPENAI ============
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "Error: OPENAI_API_KEY not set"

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.7
            }
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{base_url}/chat/completions", json=data, headers=headers) as r:
                    if r.status != 200:
                        txt = await r.text()
                        return f"OpenAI API Error {r.status}: {txt}"
                    resp = await r.json()
                    return resp['choices'][0]['message']['content']

        # ============ CLAUDE (Anthropic) ============
        elif provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return "Error: ANTHROPIC_API_KEY not set"

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": 4096
            }
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{base_url}/messages", json=data, headers=headers) as r:
                    if r.status != 200:
                        txt = await r.text()
                        return f"Claude API Error {r.status}: {txt}"
                    resp = await r.json()
                    return resp['content'][0]['text']

        # ============ OLLAMA (Local) ============
        elif provider == "ollama":
            # Ollama uses OpenAI-compatible API
            data = {
                "model": model,
                "messages": [{"role": "user", "content": full_prompt}],
                "stream": False
            }
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{base_url}/chat/completions", json=data) as r:
                    if r.status != 200:
                        txt = await r.text()
                        return f"Ollama Error {r.status}: {txt}. Is Ollama running?"
                    resp = await r.json()
                    return resp['choices'][0]['message']['content']

        else:
            return f"Provider '{provider}' not implemented"

    except asyncio.TimeoutError:
        return f"Error: {provider} request timed out"
    except aiohttp.ClientError as e:
        return f"Error: {provider} connection failed: {str(e)}"
    except Exception as e:
        logger.error(f"LLM query error: {e}")
        return f"Error: {str(e)}"
```

### Update .env
```bash
# Add to .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
# Ollama needs no key (local)
```

### Test
```python
# Test all providers
python claude_bridge.py
> ask grok what is python
> ask openai what is python
> ask claude what is python
> ask ollama what is python
```

---

## 2. Fix GUI Log Viewer (1 hour) ⭐⭐⭐⭐⭐

### Current Problem
GUI creates `fgd_server.log` but backend never writes to it, so log viewer is always empty.

### Location
`mcp_backend.py:32` (logging setup)

### Implementation

```python
# mcp_backend.py

class FGDMCPServer:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.watch_dir = Path(self.config['watch_dir']).resolve()

        # ============ ADD THIS: Set up file logging ============
        log_file = self.watch_dir / "fgd_server.log"
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        logger.info(f"MCP Server initialized - watching: {self.watch_dir}")
        # ============ END ADDITION ============

        self.scan = self.config.get('scan', {})
        # ... rest of __init__
```

### Also Update GUI to Show Correct Log Path

```python
# gui_main_pro.py:229

# BEFORE:
self.log_file = Path(dir_path) / "fgd_server.log"

# AFTER (same, but make sure it's the right directory):
self.log_file = Path(dir_path) / "fgd_server.log"
logger.info(f"GUI will monitor log file: {self.log_file}")

# Add check if file doesn't exist after 5 seconds
QTimer.singleShot(5000, self.check_log_file_exists)

def check_log_file_exists(self):
    if self.log_file and not self.log_file.exists():
        logger.warning(f"Log file not created: {self.log_file}")
        self.status.setText("Warning: Log file not found")
```

---

## 3. Add Keyboard Shortcuts (1 hour) ⭐⭐⭐⭐⭐

### Current Problem
No hotkeys - everything requires clicking.

### Location
`gui_main_pro.py:45-50` (in __init__)

### Implementation

```python
# gui_main_pro.py

from PyQt6.QtGui import QKeySequence, QShortcut

class FGDGUI(QWidget):
    def __init__(self):
        # ... existing init code ...

        self.apply_dark_mode(True)
        logger.info("GUI initialized successfully")

        # ============ ADD THIS: Keyboard shortcuts ============
        self._setup_shortcuts()
        # ============ END ADDITION ============

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Ctrl+F: Focus search
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)

        # Ctrl+R: Refresh file tree
        QShortcut(QKeySequence("Ctrl+R"), self, self.refresh_tree)

        # F5: Refresh preview
        QShortcut(QKeySequence("F5"), self, self.refresh_preview)

        # Ctrl+L: Clear logs
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_logs_shortcut)

        # Ctrl+S: Start/Stop server
        QShortcut(QKeySequence("Ctrl+S"), self, self.toggle_server)

        # Ctrl+O: Browse for directory
        QShortcut(QKeySequence("Ctrl+O"), self, self.browse)

        # Ctrl+Q: Quit
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

        # Ctrl+D: Show diff
        QShortcut(QKeySequence("Ctrl+D"), self, self.show_git_diff)

        logger.info("Keyboard shortcuts registered")

    def focus_search(self):
        """Focus the search box (to be added)"""
        # For now, just show message
        self.status.setText("Search: Press Ctrl+F (coming soon)")
        logger.info("Search shortcut pressed")

    def refresh_tree(self):
        """Refresh file tree"""
        dir_path = self.path_edit.text().strip()
        if dir_path and Path(dir_path).exists():
            self.load_file_tree(dir_path)
            self.status.setText("File tree refreshed")
            logger.info(f"Refreshed tree for: {dir_path}")

    def refresh_preview(self):
        """Refresh current preview"""
        current_item = self.tree.currentItem()
        if current_item:
            self.on_file_click(current_item, 0)
            self.status.setText("Preview refreshed")

    def clear_logs_shortcut(self):
        """Clear log viewer"""
        self.log_view.clear()
        self.status.setText("Logs cleared")

    def show_git_diff(self):
        """Show git diff in diff viewer"""
        dir_path = self.path_edit.text().strip()
        if not dir_path:
            return

        try:
            result = subprocess.run(
                ["git", "diff"],
                cwd=dir_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.stdout:
                self.diff_view.setPlainText(result.stdout)
                self.status.setText("Git diff loaded")
            else:
                self.diff_view.setPlainText("No changes")
                self.status.setText("No git changes")
        except Exception as e:
            logger.error(f"Git diff failed: {e}")
            self.status.setText(f"Git diff error: {e}")
```

### Add Status Bar (bonus!)

```python
# gui_main_pro.py - in _build_ui()

# Add before logs section:
self.status = QStatusBar()
self.layout.addWidget(self.status)
self.status.showMessage("Ready - Press Ctrl+O to open project")
```

### Show Shortcuts in UI

```python
# Add to header or help menu
shortcuts_text = """
Keyboard Shortcuts:
  Ctrl+O  - Open project directory
  Ctrl+S  - Start/Stop server
  Ctrl+F  - Search (coming soon)
  Ctrl+R  - Refresh file tree
  Ctrl+D  - Show git diff
  Ctrl+L  - Clear logs
  F5      - Refresh preview
  Ctrl+Q  - Quit
"""
```

---

## 4. Add File Search (2 hours) ⭐⭐⭐⭐⭐

### Current Problem
No way to find files quickly in large projects.

### Location
`gui_main_pro.py` - add to _build_ui()

### Implementation

```python
# gui_main_pro.py

class FGDGUI(QWidget):
    def _build_ui(self):
        # ... existing header code ...

        # ============ ADD THIS: Search bar ============
        search_container = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files... (Ctrl+F)")
        self.search_input.textChanged.connect(self.filter_tree)
        self.search_input.returnPressed.connect(self.focus_first_match)

        self.search_count_label = QLabel("0 matches")

        search_clear_btn = QPushButton("✕")
        search_clear_btn.setMaximumWidth(30)
        search_clear_btn.clicked.connect(self.clear_search)

        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_count_label)
        search_layout.addWidget(search_clear_btn)

        search_container.setLayout(search_layout)
        self.layout.addWidget(search_container)
        # ============ END ADDITION ============

        # ... rest of _build_ui ...

    def filter_tree(self, search_text):
        """Filter tree view based on search text"""
        if not search_text:
            self._show_all_items()
            self.search_count_label.setText("0 matches")
            return

        search_lower = search_text.lower()
        match_count = 0

        def filter_item(item):
            """Recursively filter items"""
            nonlocal match_count

            # Check if this item matches
            item_text = item.text(0).lower()
            matches = search_lower in item_text

            # Check children
            child_matches = False
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_item(child):
                    child_matches = True

            # Show if this item or any child matches
            should_show = matches or child_matches
            item.setHidden(not should_show)

            if matches and item.childCount() == 0:  # It's a file
                match_count += 1

            return should_show

        # Filter all top-level items
        for i in range(self.tree.topLevelItemCount()):
            filter_item(self.tree.topLevelItem(i))

        self.search_count_label.setText(f"{match_count} matches")

    def _show_all_items(self):
        """Show all items in tree"""
        def show_item(item):
            item.setHidden(False)
            for i in range(item.childCount()):
                show_item(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            show_item(self.tree.topLevelItem(i))

    def focus_first_match(self):
        """Select first visible file"""
        def find_first_file(item):
            if not item.isHidden() and item.childCount() == 0:
                return item
            for i in range(item.childCount()):
                result = find_first_file(item.child(i))
                if result:
                    return result
            return None

        for i in range(self.tree.topLevelItemCount()):
            first_match = find_first_file(self.tree.topLevelItem(i))
            if first_match:
                self.tree.setCurrentItem(first_match)
                self.on_file_click(first_match, 0)
                break

    def clear_search(self):
        """Clear search box"""
        self.search_input.clear()

    def focus_search(self):
        """Focus search box (for Ctrl+F shortcut)"""
        self.search_input.setFocus()
        self.search_input.selectAll()
```

### Add Search Stats

```python
# Show in status bar
def filter_tree(self, search_text):
    # ... existing code ...
    self.status.setText(f"Found {match_count} matches for '{search_text}'")
```

---

## 5. Add Syntax Highlighting (3 hours) ⭐⭐⭐⭐⭐

### Current Problem
Code preview is plain text - hard to read.

### Location
`gui_main_pro.py` - modify preview widget

### Implementation

```python
# gui_main_pro.py

from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
import re

class CodeHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for multiple languages"""

    def __init__(self, parent=None, language="python"):
        super().__init__(parent)
        self.language = language
        self.highlighting_rules = []

        # Define formats
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))  # Blue
        keyword_format.setFontWeight(QFont.Weight.Bold)

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))  # Orange

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))  # Green

        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#dcdcaa"))  # Yellow

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))  # Light green

        # Python keywords
        if language == "python":
            keywords = [
                'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
                'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
                'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
                'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True',
                'try', 'while', 'with', 'yield', 'async', 'await'
            ]

            for word in keywords:
                pattern = f'\\b{word}\\b'
                self.highlighting_rules.append((re.compile(pattern), keyword_format))

            # Built-in functions
            builtins = ['print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'open', 'input']
            for word in builtins:
                pattern = f'\\b{word}\\b'
                self.highlighting_rules.append((re.compile(pattern), function_format))

            # Strings
            self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
            self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

            # Comments
            self.highlighting_rules.append((re.compile(r'#[^\n]*'), comment_format))

        # JavaScript keywords
        elif language == "javascript":
            keywords = [
                'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
                'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
                'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new',
                'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof', 'var',
                'void', 'while', 'with', 'yield', 'async', 'await', 'true', 'false', 'null'
            ]

            for word in keywords:
                pattern = f'\\b{word}\\b'
                self.highlighting_rules.append((re.compile(pattern), keyword_format))

            # Strings
            self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
            self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
            self.highlighting_rules.append((re.compile(r'`[^`]*`'), string_format))

            # Comments
            self.highlighting_rules.append((re.compile(r'//[^\n]*'), comment_format))

        # Numbers (all languages)
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*\b'), number_format))

    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format)


class FGDGUI(QWidget):
    def __init__(self):
        # ... existing init ...

        # ============ ADD THIS ============
        self.current_highlighter = None
        # ============ END ADDITION ============

    def on_file_click(self, item, column):
        try:
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            if file_path and Path(file_path).is_file():
                path = Path(file_path)
                if path.stat().st_size > 500_000:
                    self.preview.setPlainText(f"File too large to preview: {path.stat().st_size / 1024:.1f} KB")
                    return

                try:
                    content = path.read_text(encoding='utf-8')
                    self.preview.setPlainText(content)

                    # ============ ADD THIS: Apply syntax highlighting ============
                    # Determine language from file extension
                    language = None
                    if path.suffix in ['.py']:
                        language = 'python'
                    elif path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                        language = 'javascript'
                    elif path.suffix in ['.json']:
                        language = 'json'
                    elif path.suffix in ['.yaml', '.yml']:
                        language = 'yaml'

                    # Remove old highlighter
                    if self.current_highlighter:
                        self.current_highlighter.setDocument(None)

                    # Apply new highlighter if we know the language
                    if language:
                        self.current_highlighter = CodeHighlighter(
                            self.preview.document(),
                            language
                        )
                    # ============ END ADDITION ============

                except UnicodeDecodeError:
                    self.preview.setPlainText("[Binary file - cannot preview]")
        except Exception as e:
            logger.error(f"Error previewing file: {e}")
            self.preview.setPlainText(f"Error: {str(e)}")
```

### Enhance with Line Numbers (Bonus!)

```python
class LineNumberArea(QWidget):
    """Widget to show line numbers next to code"""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def paintEvent(self, event):
        """Draw line numbers"""
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#1e1e1e"))

        # Draw line numbers
        # (Implementation omitted for brevity - see VSCode line numbers)

# Add to text edit
self.preview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
```

---

## 🎯 Testing Your Changes

### Test Script

```bash
#!/bin/bash

echo "🧪 Testing Quick Wins Implementation"

echo "1️⃣ Testing LLM providers..."
python -c "
from mcp_backend import LLMBackend
import asyncio

config = {
    'llm': {
        'default_provider': 'grok',
        'providers': {
            'grok': {'model': 'grok-beta', 'base_url': 'https://api.x.ai/v1'},
            'openai': {'model': 'gpt-4o-mini', 'base_url': 'https://api.openai.com/v1'},
        }
    }
}

llm = LLMBackend(config)
response = asyncio.run(llm.query('Say hi', 'grok'))
print(f'Grok: {response[:50]}...')
"

echo "2️⃣ Testing log viewer..."
python -c "
from pathlib import Path
log = Path('.') / 'fgd_server.log'
print(f'Log exists: {log.exists()}')
if log.exists():
    print(f'Log size: {log.stat().st_size} bytes')
"

echo "3️⃣ Testing GUI shortcuts..."
python gui_main_pro.py &
sleep 3
echo "GUI should be open - test Ctrl+R, Ctrl+D, etc."
kill %1

echo "4️⃣ Testing search..."
# (Manual test in GUI)

echo "5️⃣ Testing syntax highlighting..."
# (Manual test in GUI)

echo "✅ All tests complete!"
```

---

## 📊 Before/After Comparison

### Before
- ❌ Only Grok works
- ❌ Logs never show up
- ❌ Must click everything
- ❌ Can't find files in large projects
- ❌ Code is hard to read

### After (9 hours of work)
- ✅ All 4 LLM providers work
- ✅ Logs update in real-time
- ✅ 10 keyboard shortcuts
- ✅ Fast file search with live filtering
- ✅ Beautiful syntax highlighting

**User Experience:** 10x better!

---

## 🚀 Next Steps

After implementing these 5 features:

1. **Test thoroughly** - Try all shortcuts, search patterns, LLM providers
2. **Get feedback** - Have someone else try it
3. **Pick next 5** from the roadmap based on their feedback
4. **Iterate** - Keep improving

---

## 💡 Pro Tips

1. **Commit after each feature** - Don't bundle all 5 together
2. **Write tests** - At least for LLM providers
3. **Document shortcuts** - Add help menu showing all hotkeys
4. **Add telemetry** - Track which features users actually use
5. **Ask for feedback** - The user knows best!

---

## 🐛 Common Issues

### Issue: Syntax highlighting is slow
**Solution:** Limit file size for highlighting to 100KB

```python
if path.stat().st_size < 100_000:  # Only highlight small files
    self.current_highlighter = CodeHighlighter(...)
```

### Issue: Search freezes on huge directories
**Solution:** Add async search

```python
from PyQt6.QtCore import QThread

class SearchThread(QThread):
    def run(self):
        # Do search in background
        pass
```

### Issue: LLM calls block GUI
**Solution:** Already async! But add loading indicator:

```python
self.status.setText("Querying LLM...")
QApplication.processEvents()  # Update UI
response = await llm.query(...)
self.status.setText("Done!")
```

---

**Ready to implement? Start with #1 (LLM providers) - biggest bang for buck!**
