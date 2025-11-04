#!/usr/bin/env python3
"""
MCPM v5.0 GUI – Beautiful Modern Interface
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QFont, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QColor, QPalette
from pathlib import Path
import sys
import yaml
import subprocess
import os
import json
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv
import threading
import re

# Set up logging to file AND console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcpm_gui.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# --------------------------------------------------------------------------- #
# -------------------------- SYNTAX HIGHLIGHTER ----------------------------- #
# --------------------------------------------------------------------------- #
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        # Define syntax highlighting rules
        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff79c6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            'def', 'class', 'import', 'from', 'if', 'elif', 'else', 'for',
            'while', 'return', 'try', 'except', 'finally', 'with', 'as',
            'async', 'await', 'yield', 'lambda', 'pass', 'break', 'continue'
        ]
        for word in keywords:
            pattern = f'\\b{word}\\b'
            self.highlighting_rules.append((re.compile(pattern), keyword_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#f1fa8c"))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6272a4"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r'#[^\n]*'), comment_format))

        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#50fa7b"))
        self.highlighting_rules.append((re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\()'), function_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

# --------------------------------------------------------------------------- #
# -------------------------- POP-OUT WINDOWS -------------------------------- #
# --------------------------------------------------------------------------- #
class PopOutWindow(QWidget):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 700)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 11))
        self.text_edit.setPlainText(content)

        # Apply syntax highlighting for Python files
        if title.endswith('.py'):
            PythonHighlighter(self.text_edit.document())

        layout.addWidget(self.text_edit)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c8ff0, stop:1 #8a5cb8);
            }
        """)
        layout.addWidget(close_btn)

        self.apply_dark_mode()

    def apply_dark_mode(self):
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
                color: #f0f6fc;
            }
            QTextEdit {
                background: #0d1117;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-size: 11pt;
            }
        """)

# --------------------------------------------------------------------------- #
# -------------------------- MAIN GUI --------------------------------------- #
# --------------------------------------------------------------------------- #
class FGDGUI(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.setWindowTitle("MCPM v5.0 – AI Code Co‑Pilot 🚀")
            self.resize(1600, 1000)
            self.layout = QVBoxLayout()
            self.setLayout(self.layout)
            self.process = None
            self.log_file = None
            self.pending_action = None
            self.pending_edit = None
            self.pop_out_windows = []

            self._build_ui()
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_logs)
            self.timer.start(1000)

            self.apply_dark_mode()
            logger.info("GUI initialized successfully")
        except Exception as e:
            logger.error(f"GUI initialization failed: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(None, "Initialization Error", f"Failed to initialize GUI:\n{str(e)}\n\nCheck mcpm_gui.log for details")
            raise

    def _build_ui(self):
        # Header with gradient
        header = QLabel("MCPM v5.0 – AI Code Co‑Pilot 🚀")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            margin: 30px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            color: #667eea;
        """)
        self.layout.addWidget(header)

        # Control Panel Card
        control_card = self._create_control_panel()
        self.layout.addWidget(control_card)

        # Main Content Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #30363d;
                border-radius: 12px;
                background: rgba(13, 17, 23, 0.6);
                padding: 10px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #30363d, stop:1 #21262d);
                color: #f0f6fc;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
            }
            QTabBar::tab:hover {
                background: #30363d;
            }
        """)

        # Tab 1: File Explorer & Preview
        explorer_tab = self._create_explorer_tab()
        self.tabs.addTab(explorer_tab, "📁 File Explorer")

        # Tab 2: Diff Viewer
        diff_tab = self._create_diff_tab()
        self.tabs.addTab(diff_tab, "🔍 Diff Viewer")

        # Tab 3: Logs
        logs_tab = self._create_logs_tab()
        self.tabs.addTab(logs_tab, "📋 Live Logs")

        # Tab 4: Backups
        backups_tab = self._create_backups_tab()
        self.tabs.addTab(backups_tab, "💾 Backups")

        self.layout.addWidget(self.tabs)

    def _create_control_panel(self):
        """Create beautiful control panel"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(102, 126, 234, 0.15),
                    stop:1 rgba(118, 75, 162, 0.15));
                border-radius: 16px;
                padding: 20px;
                border: 2px solid rgba(102, 126, 234, 0.3);
            }
        """)
        card_layout = QVBoxLayout()

        # Project Directory
        dir_layout = QHBoxLayout()
        dir_label = QLabel("📂 Project Directory:")
        dir_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #50fa7b;")
        self.path_edit = QLineEdit()
        self.path_edit.setStyleSheet("""
            QLineEdit {
                background: rgba(13, 17, 23, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        browse.setStyleSheet(self._button_style())
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.path_edit)
        dir_layout.addWidget(browse)
        card_layout.addLayout(dir_layout)

        # Provider and Controls
        controls_layout = QHBoxLayout()

        provider_label = QLabel("🤖 LLM Provider:")
        provider_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #50fa7b;")
        self.provider = QComboBox()
        self.provider.addItems(["grok", "openai", "claude", "ollama"])
        self.provider.setCurrentText("grok")
        self.provider.setStyleSheet("""
            QComboBox {
                background: rgba(13, 17, 23, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 2px solid #667eea;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #0d1117;
                color: #f0f6fc;
                selection-background-color: #667eea;
            }
        """)

        self.start_btn = QPushButton("▶ Start Server")
        self.start_btn.clicked.connect(self.toggle_server)
        self.start_btn.setStyleSheet(self._button_style("#50fa7b", "#5fff8a"))
        self.start_btn.setMinimumHeight(50)

        self.status = QLabel("🟢 Status: Ready")
        self.status.setStyleSheet("color: #50fa7b; font-weight: bold; font-size: 14px;")

        controls_layout.addWidget(provider_label)
        controls_layout.addWidget(self.provider)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.status)
        card_layout.addLayout(controls_layout)

        card.setLayout(card_layout)
        return card

    def _create_explorer_tab(self):
        """Create file explorer tab with larger preview"""
        widget = QWidget()
        layout = QVBoxLayout()

        split = QSplitter()
        split.setOrientation(Qt.Orientation.Horizontal)

        # File Tree
        tree_widget = QWidget()
        tree_layout = QVBoxLayout()
        tree_header = QHBoxLayout()
        tree_label = QLabel("📁 File Tree")
        tree_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #667eea;")
        tree_header.addWidget(tree_label)
        tree_layout.addLayout(tree_header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Files")
        self.tree.itemClicked.connect(self.on_file_click)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #0d1117;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                font-size: 13px;
                padding: 8px;
            }
            QTreeWidget::item {
                padding: 6px;
            }
            QTreeWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
            }
            QTreeWidget::item:hover {
                background: #21262d;
            }
        """)
        tree_layout.addWidget(self.tree)
        tree_widget.setLayout(tree_layout)

        # Code Preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        preview_header = QHBoxLayout()
        preview_label = QLabel("📄 Code Preview")
        preview_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #667eea;")
        pop_out_btn = QPushButton("🔍 Pop Out")
        pop_out_btn.clicked.connect(self.pop_out_preview)
        pop_out_btn.setStyleSheet(self._button_style())
        preview_header.addWidget(preview_label)
        preview_header.addStretch()
        preview_header.addWidget(pop_out_btn)
        preview_layout.addLayout(preview_header)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 11))
        self.preview.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-size: 11pt;
                line-height: 1.5;
            }
        """)
        self.preview_highlighter = PythonHighlighter(self.preview.document())
        preview_layout.addWidget(self.preview)
        preview_widget.setLayout(preview_layout)

        split.addWidget(tree_widget)
        split.addWidget(preview_widget)
        split.setSizes([400, 1100])  # Much larger preview

        layout.addWidget(split)
        widget.setLayout(layout)
        return widget

    def _create_diff_tab(self):
        """Create beautiful diff viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Header
        header = QHBoxLayout()
        diff_label = QLabel("🔍 Pending Edit Review")
        diff_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #667eea;")
        pop_out_btn = QPushButton("🔍 Pop Out")
        pop_out_btn.clicked.connect(self.pop_out_diff)
        pop_out_btn.setStyleSheet(self._button_style())
        header.addWidget(diff_label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        # Diff Viewer
        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Consolas", 12))
        self.diff_view.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 16px;
                font-size: 12pt;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.diff_view)

        # Approve/Reject Buttons
        btns = QHBoxLayout()
        self.approve_btn = QPushButton("✅ Approve Changes")
        self.approve_btn.clicked.connect(self.approve_edit)
        self.approve_btn.setStyleSheet(self._button_style("#50fa7b", "#5fff8a"))
        self.approve_btn.setMinimumHeight(50)

        self.reject_btn = QPushButton("❌ Reject Changes")
        self.reject_btn.clicked.connect(self.reject_edit)
        self.reject_btn.setStyleSheet(self._button_style("#ff5555", "#ff6e6e"))
        self.reject_btn.setMinimumHeight(50)

        btns.addWidget(self.approve_btn)
        btns.addWidget(self.reject_btn)
        layout.addLayout(btns)

        widget.setLayout(layout)
        return widget

    def _create_logs_tab(self):
        """Create logs viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Header
        header = QHBoxLayout()
        log_label = QLabel("📋 Live Server Logs")
        log_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #667eea;")
        pop_out_btn = QPushButton("🔍 Pop Out")
        pop_out_btn.clicked.connect(self.pop_out_logs)
        pop_out_btn.setStyleSheet(self._button_style())
        header.addWidget(log_label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        # Filters
        filters = QHBoxLayout()
        level_label = QLabel("Level:")
        level_label.setStyleSheet("color: #50fa7b; font-weight: bold;")
        self.level = QComboBox()
        self.level.addItems(["All", "INFO", "WARNING", "ERROR"])
        self.level.setStyleSheet("""
            QComboBox {
                background: rgba(13, 17, 23, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 8px;
            }
            QComboBox QAbstractItemView {
                background: #0d1117;
                color: #f0f6fc;
                selection-background-color: #667eea;
            }
        """)

        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #50fa7b; font-weight: bold;")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search logs...")
        self.search.setStyleSheet("""
            QLineEdit {
                background: rgba(13, 17, 23, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)

        clear = QPushButton("Clear Filters")
        clear.clicked.connect(self.clear_filters)
        clear.setStyleSheet(self._button_style())

        filters.addWidget(level_label)
        filters.addWidget(self.level)
        filters.addWidget(search_label)
        filters.addWidget(self.search)
        filters.addWidget(clear)
        layout.addLayout(filters)

        # Log Viewer
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 11))
        self.log_view.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-size: 11pt;
            }
        """)
        layout.addWidget(self.log_view)

        widget.setLayout(layout)
        return widget

    def _create_backups_tab(self):
        """Create backups viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        backup_label = QLabel("💾 File Backups")
        backup_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #667eea;")
        layout.addWidget(backup_label)

        self.backup_list = QListWidget()
        self.backup_list.setStyleSheet("""
            QListWidget {
                background: #0d1117;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
            }
            QListWidget::item:hover {
                background: #21262d;
            }
        """)
        layout.addWidget(self.backup_list)

        widget.setLayout(layout)
        return widget

    def _button_style(self, color1="#667eea", color2="#764ba2"):
        """Return button stylesheet with gradient"""
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color1}, stop:1 {color2});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color2}, stop:1 {color1});
            }}
            QPushButton:pressed {{
                padding: 12px 18px 8px 22px;
            }}
        """

    def pop_out_preview(self):
        """Pop out preview window"""
        content = self.preview.toPlainText()
        if content:
            window = PopOutWindow("Code Preview", content, self)
            window.show()
            self.pop_out_windows.append(window)

    def pop_out_diff(self):
        """Pop out diff window"""
        content = self.diff_view.toPlainText()
        if content:
            window = PopOutWindow("Diff Viewer", content, self)
            window.show()
            self.pop_out_windows.append(window)

    def pop_out_logs(self):
        """Pop out logs window"""
        content = self.log_view.toPlainText()
        if content:
            window = PopOutWindow("Live Logs", content, self)
            window.show()
            self.pop_out_windows.append(window)

    def browse(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Project")
        if dir_path:
            self.path_edit.setText(dir_path)
            self.load_file_tree(dir_path)

    def load_file_tree(self, root):
        self.tree.clear()
        root_item = QTreeWidgetItem([Path(root).name])
        self.tree.addTopLevelItem(root_item)
        self._add_tree_items(root_item, Path(root))
        root_item.setExpanded(True)

    def _add_tree_items(self, parent, path):
        try:
            for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                if p.name.startswith('.') or p.name in ['node_modules', '__pycache__']:
                    continue
                item = QTreeWidgetItem([p.name])
                item.setData(0, Qt.ItemDataRole.UserRole, str(p))
                parent.addChild(item)
                if p.is_dir():
                    self._add_tree_items(item, p)
        except Exception as e:
            logger.warning(f"Error adding tree items for {path}: {e}")

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
                except UnicodeDecodeError:
                    self.preview.setPlainText("[Binary file - cannot preview]")
        except Exception as e:
            logger.error(f"Error previewing file: {e}")
            self.preview.setPlainText(f"Error: {str(e)}")

    def _read_subprocess_stdout(self):
        """Background thread to read subprocess stdout and write to log file."""
        try:
            for line in self.process.stdout:
                try:
                    decoded = line.decode('utf-8', errors='replace')
                    if self.log_file:
                        with open(self.log_file, 'a') as f:
                            f.write(decoded)
                            f.flush()
                except Exception as e:
                    logger.error(f"Error writing stdout to log: {e}")
        except Exception as e:
            logger.debug(f"Stdout reader stopped: {e}")

    def _read_subprocess_stderr(self):
        """Background thread to read subprocess stderr and write to log file."""
        try:
            for line in self.process.stderr:
                try:
                    decoded = line.decode('utf-8', errors='replace')
                    if self.log_file:
                        with open(self.log_file, 'a') as f:
                            f.write(decoded)
                            f.flush()
                except Exception as e:
                    logger.error(f"Error writing stderr to log: {e}")
        except Exception as e:
            logger.debug(f"Stderr reader stopped: {e}")

    def toggle_server(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status.setText("🔴 Status: Stopped")
            self.start_btn.setText("▶ Start Server")
        else:
            self.start_server()

    def start_server(self):
        dir_path = self.path_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            self.status.setText("🔴 Invalid directory")
            return

        provider = self.provider.currentText()
        config = {
            "watch_dir": dir_path,
            "memory_file": str(Path(dir_path) / ".fgd_memory.json"),
            "context_limit": 20,
            "scan": {"max_dir_size_gb": 2, "max_files_per_scan": 5, "max_file_size_kb": 250},
            "reference_dirs": [],
            "llm": {
                "default_provider": provider,
                "providers": {
                    "grok": {"model": "grok-beta", "base_url": "https://api.x.ai/v1"},
                    "openai": {"model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1"},
                    "claude": {"model": "claude-3-5-sonnet-20241022", "base_url": "https://api.anthropic.com/v1"},
                    "ollama": {"model": "llama3", "base_url": "http://localhost:11434/v1"}
                }
            }
        }
        config_path = Path(dir_path) / "fgd_config.yaml"
        config_path.write_text(yaml.dump(config))

        self.log_file = Path(dir_path) / "fgd_server.log"
        self.log_file.write_text("")

        env = os.environ.copy()
        self.process = subprocess.Popen(
            [sys.executable, "mcp_backend.py", str(config_path)],
            cwd=dir_path,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Start background threads to read subprocess output
        stdout_thread = threading.Thread(target=self._read_subprocess_stdout, daemon=True)
        stderr_thread = threading.Thread(target=self._read_subprocess_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        logger.info("Subprocess output monitoring threads started")

        self.status.setText(f"🟢 Server running: {provider}")
        self.start_btn.setText("⏹ Stop Server")

    def update_logs(self):
        if not self.log_file or not self.log_file.exists():
            return
        try:
            lines = self.log_file.read_text().splitlines()
            level = self.level.currentText()
            search = self.search.text().lower()
            filtered = []
            for line in lines:
                if level != "All" and level not in line:
                    continue
                if search and search not in line.lower():
                    continue
                filtered.append(line)

            self.log_view.clear()
            for line in filtered:
                cursor = self.log_view.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.log_view.setTextCursor(cursor)
                if "ERROR" in line:
                    self.log_view.setTextColor(QColor("#ff5555"))
                elif "WARNING" in line:
                    self.log_view.setTextColor(QColor("#f1fa8c"))
                elif "✅" in line or "SUCCESS" in line:
                    self.log_view.setTextColor(QColor("#50fa7b"))
                else:
                    self.log_view.setTextColor(QColor("#f0f6fc"))
                self.log_view.insertPlainText(line + "\n")

            # Check for pending edits
            self.check_pending_edits()
        except Exception as e:
            logger.debug(f"Error updating logs: {e}")

    def check_pending_edits(self):
        """Poll for pending edit requests from the backend."""
        try:
            dir_path = self.path_edit.text().strip()
            if not dir_path:
                return

            pending_file = Path(dir_path) / ".fgd_pending_edit.json"
            if not pending_file.exists():
                return

            # Load pending edit
            pending_data = json.loads(pending_file.read_text())

            # Only update if this is a new pending edit
            if self.pending_edit and self.pending_edit.get("timestamp") == pending_data.get("timestamp"):
                return

            self.pending_edit = pending_data

            # Display diff in the diff viewer with better formatting
            diff_text = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔍 PENDING EDIT: {pending_data['filepath']}
╚══════════════════════════════════════════════════════════════════════════════╝

┌─ 🔴 OLD TEXT ────────────────────────────────────────────────────────────────┐
{pending_data['old_text']}
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 🟢 NEW TEXT ────────────────────────────────────────────────────────────────┐
{pending_data['new_text']}
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 📄 PREVIEW (first 500 chars) ───────────────────────────────────────────────┐
{pending_data['preview']}
└──────────────────────────────────────────────────────────────────────────────┘

⏱️  Timestamp: {pending_data['timestamp']}

👉 Review the changes above and click "Approve" or "Reject" below.
"""
            self.diff_view.setPlainText(diff_text)

            # Switch to diff tab and highlight buttons
            self.tabs.setCurrentIndex(1)
            self.approve_btn.setStyleSheet(self._button_style("#50fa7b", "#5fff8a") +
                "QPushButton { animation: pulse 2s infinite; font-size: 16px; }")
            self.reject_btn.setStyleSheet(self._button_style("#ff5555", "#ff6e6e") +
                "QPushButton { font-size: 16px; }")

            logger.info(f"Pending edit detected: {pending_data['filepath']}")

        except Exception as e:
            logger.debug(f"Error checking pending edits: {e}")

    def clear_filters(self):
        self.level.setCurrentIndex(0)
        self.search.clear()

    def approve_edit(self):
        try:
            if self.pending_edit:
                dir_path = self.path_edit.text().strip()
                if not dir_path:
                    QMessageBox.warning(self, "Error", "No project directory selected")
                    return

                # Write approval decision
                approval_file = Path(dir_path) / ".fgd_approval.json"
                approval_data = {
                    "approved": True,
                    "filepath": self.pending_edit['filepath'],
                    "old_text": self.pending_edit['old_text'],
                    "new_text": self.pending_edit['new_text'],
                    "timestamp": datetime.now().isoformat()
                }
                approval_file.write_text(json.dumps(approval_data, indent=2))

                # Delete pending edit file to signal completion
                pending_file = Path(dir_path) / ".fgd_pending_edit.json"
                if pending_file.exists():
                    pending_file.unlink()

                logger.info(f"✅ Edit APPROVED for: {self.pending_edit.get('filepath')}")
                QMessageBox.information(self, "✅ Edit Approved",
                    f"✅ Changes approved!\n\nFile: {self.pending_edit['filepath']}\n\nThe backend will apply the changes automatically.")

                # Clear display
                self.diff_view.clear()
                self.approve_btn.setStyleSheet(self._button_style("#50fa7b", "#5fff8a"))
                self.reject_btn.setStyleSheet(self._button_style("#ff5555", "#ff6e6e"))
                self.pending_edit = None
            else:
                QMessageBox.information(self, "No Pending Edit", "There are no pending edits to approve.")
        except Exception as e:
            logger.error(f"Error approving edit: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "Error", f"Failed to approve edit: {str(e)}")

    def reject_edit(self):
        try:
            if self.pending_edit:
                dir_path = self.path_edit.text().strip()
                if not dir_path:
                    QMessageBox.warning(self, "Error", "No project directory selected")
                    return

                # Write rejection decision
                approval_file = Path(dir_path) / ".fgd_approval.json"
                approval_data = {
                    "approved": False,
                    "filepath": self.pending_edit['filepath'],
                    "reason": "Rejected by user",
                    "timestamp": datetime.now().isoformat()
                }
                approval_file.write_text(json.dumps(approval_data, indent=2))

                # Delete pending edit file
                pending_file = Path(dir_path) / ".fgd_pending_edit.json"
                if pending_file.exists():
                    pending_file.unlink()

                logger.info(f"❌ Edit REJECTED for: {self.pending_edit.get('filepath')}")
                QMessageBox.information(self, "❌ Edit Rejected",
                    f"❌ Changes rejected!\n\nFile: {self.pending_edit['filepath']}\n\nNo changes will be made.")

                # Clear display
                self.diff_view.clear()
                self.approve_btn.setStyleSheet(self._button_style("#50fa7b", "#5fff8a"))
                self.reject_btn.setStyleSheet(self._button_style("#ff5555", "#ff6e6e"))
                self.pending_edit = None
            else:
                QMessageBox.information(self, "No Pending Edit", "There are no pending edits to reject.")
        except Exception as e:
            logger.error(f"Error rejecting edit: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "Error", f"Failed to reject edit: {str(e)}")

    def apply_dark_mode(self):
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0c29, stop:0.3 #302b63, stop:0.7 #24243e, stop:1 #0f0c29);
                color: #f0f6fc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMessageBox {
                background: #0d1117;
            }
            QScrollBar:vertical {
                background: #0d1117;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #667eea;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #764ba2;
            }
        """)

    def closeEvent(self, event):
        if self.process:
            self.process.terminate()
        for window in self.pop_out_windows:
            window.close()
        event.accept()

if __name__ == "__main__":
    try:
        logger.info("Starting MCPM GUI...")
        app = QApplication(sys.argv)
        win = FGDGUI()
        win.show()
        logger.info("GUI window displayed")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())
        try:
            QMessageBox.critical(None, "Fatal Error",
                f"Application failed to start:\n{str(e)}\n\nCheck mcpm_gui.log for details.\n\nPress OK to exit.")
        except:
            print(f"\n{'='*60}\nFATAL ERROR:\n{e}\n{traceback.format_exc()}\n{'='*60}")
        input("\nPress Enter to close...")
        sys.exit(1)
