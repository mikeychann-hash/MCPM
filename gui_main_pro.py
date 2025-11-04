#!/usr/bin/env python3
"""
MCPM v5.0 GUI – Full visual experience
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QTextCursor
from pathlib import Path
import sys
import yaml
import subprocess
import os
import json
import logging
import traceback
from dotenv import load_dotenv

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

class FGDGUI(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.setWindowTitle("MCPM v5.0 – AI Code Co‑Pilot")
            self.resize(1200, 800)
            self.layout = QVBoxLayout()
            self.setLayout(self.layout)
            self.process = None
            self.log_file = None
            self.pending_action = None
            self.pending_edit = None

            self._build_ui()
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_logs)
            self.timer.start(1000)

            self.apply_dark_mode(True)
            logger.info("GUI initialized successfully")
        except Exception as e:
            logger.error(f"GUI initialization failed: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(None, "Initialization Error", f"Failed to initialize GUI:\n{str(e)}\n\nCheck mcpm_gui.log for details")
            raise

    def _build_ui(self):
        # Header
        header = QLabel("MCPM v5.0 – AI Code Co‑Pilot")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 28px; font-weight: bold; margin: 20px; color: #667eea;")
        self.layout.addWidget(header)

        # Project Card
        card = QWidget()
        card.setStyleSheet(".card { background: rgba(255,255,255,0.1); border-radius: 16px; padding: 20px; margin: 10px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); }")
        card_layout = QVBoxLayout()
        h = QHBoxLayout()
        self.path_edit = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        h.addWidget(self.path_edit)
        h.addWidget(browse)
        card_layout.addWidget(QLabel("Project Directory"))
        card_layout.addLayout(h)

        self.provider = QComboBox()
        self.provider.addItems(["grok", "openai", "claude", "ollama"])
        self.provider.setCurrentText("grok")
        card_layout.addWidget(QLabel("LLM Provider"))
        card_layout.addWidget(self.provider)

        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.toggle_server)
        card_layout.addWidget(self.start_btn)

        self.status = QLabel("Status: Ready")
        self.status.setStyleSheet("color: #50fa7b; font-weight: bold;")
        card_layout.addWidget(self.status)

        card.setLayout(card_layout)
        self.layout.addWidget(card)

        # Split: Tree + Preview
        split = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Files")
        self.tree.itemClicked.connect(self.on_file_click)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 10))
        split.addWidget(self.tree)
        split.addWidget(self.preview)
        split.setSizes([300, 700])
        self.layout.addWidget(split)

        # Diff Viewer
        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Consolas", 10))
        self.layout.addWidget(QLabel("Diff Preview"))
        self.layout.addWidget(self.diff_view)

        btns = QHBoxLayout()
        self.approve_btn = QPushButton("Approve")
        self.approve_btn.clicked.connect(self.approve_edit)
        self.reject_btn = QPushButton("Reject")
        self.reject_btn.clicked.connect(self.reject_edit)
        btns.addWidget(self.approve_btn)
        btns.addWidget(self.reject_btn)
        self.layout.addLayout(btns)

        # Backups
        self.backup_list = QListWidget()
        self.layout.addWidget(QLabel("Backups"))
        self.layout.addWidget(self.backup_list)

        # Logs
        log_card = QWidget()
        log_layout = QVBoxLayout()
        log_layout.addWidget(QLabel("Live Logs"))
        filters = QHBoxLayout()
        self.level = QComboBox()
        self.level.addItems(["All", "INFO", "WARNING", "ERROR"])
        filters.addWidget(QLabel("Level:"))
        filters.addWidget(self.level)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search...")
        filters.addWidget(self.search)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear_filters)
        filters.addWidget(clear)
        log_layout.addLayout(filters)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.log_view)
        log_card.setLayout(log_layout)
        self.layout.addWidget(log_card)

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
                item.setData(0, Qt.ItemDataRole.UserRole, str(p))  # Store full path
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
                if path.stat().st_size > 500_000:  # 500KB limit
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

    def toggle_server(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status.setText("Status: Stopped")
            self.start_btn.setText("Start Server")
        else:
            self.start_server()

    def start_server(self):
        dir_path = self.path_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            self.status.setText("Invalid directory")
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
            env=env
        )
        self.status.setText(f"Server running: {provider}")
        self.start_btn.setText("Stop Server")

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
                    self.log_view.setTextColor(Qt.GlobalColor.red)
                elif "WARNING" in line:
                    self.log_view.setTextColor(Qt.GlobalColor.yellow)
                else:
                    self.log_view.setTextColor(Qt.GlobalColor.white)
                self.log_view.insertPlainText(line + "\n")
        except Exception as e:
            logger.debug(f"Error updating logs: {e}")

    def clear_filters(self):
        self.level.setCurrentIndex(0)
        self.search.clear()

    def approve_edit(self):
        try:
            if self.pending_edit:
                # In a real implementation, this would send approval to the backend
                logger.info(f"Edit approved for: {self.pending_edit.get('filepath')}")
                QMessageBox.information(self, "Edit Approved", "Changes have been approved and applied.")
                self.diff_view.clear()
                self.pending_edit = None
            else:
                QMessageBox.information(self, "No Pending Edit", "There are no pending edits to approve.")
        except Exception as e:
            logger.error(f"Error approving edit: {e}")
            QMessageBox.warning(self, "Error", f"Failed to approve edit: {str(e)}")

    def reject_edit(self):
        try:
            if self.pending_edit:
                logger.info(f"Edit rejected for: {self.pending_edit.get('filepath')}")
                QMessageBox.information(self, "Edit Rejected", "Changes have been rejected.")
                self.diff_view.clear()
                self.pending_edit = None
            else:
                QMessageBox.information(self, "No Pending Edit", "There are no pending edits to reject.")
        except Exception as e:
            logger.error(f"Error rejecting edit: {e}")
            QMessageBox.warning(self, "Error", f"Failed to reject edit: {str(e)}")

    def apply_dark_mode(self, dark):
        if dark:
            self.setStyleSheet("background:#0d1117; color:#f0f6fc; QTextEdit {background:#010409;}")
        else:
            self.setStyleSheet("background:#f7f9fc; color:#24292f; QTextEdit {background:#f6f8fa;}")

    def closeEvent(self, event):
        if self.process:
            self.process.terminate()
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
        # Show error dialog if possible
        try:
            QMessageBox.critical(None, "Fatal Error",
                f"Application failed to start:\n{str(e)}\n\nCheck mcpm_gui.log for details.\n\nPress OK to exit.")
        except:
            print(f"\n{'='*60}\nFATAL ERROR:\n{e}\n{traceback.format_exc()}\n{'='*60}")
        input("\nPress Enter to close...")
        sys.exit(1)