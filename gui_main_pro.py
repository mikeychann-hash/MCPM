#!/usr/bin/env python3
"""
FGD Stack Pro GUI – Grok-Only by Default + Safe LLM Switching
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QTextCursor
from pathlib import Path
import sys
import yaml
import subprocess
import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

class FGDGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FGD Stack Pro v2.3")
        self.resize(900, 700)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.process = None
        self.log_file = None

        # Directory
        self.path_edit = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        h = QHBoxLayout()
        h.addWidget(self.path_edit)
        h.addWidget(browse)
        self.layout.addWidget(QLabel("Project Directory:"))
        self.layout.addLayout(h)

        # Provider
        self.provider = QComboBox()
        self.provider.addItems(["grok", "openai", "claude", "ollama"])
        self.provider.setCurrentText("grok")  # GROK DEFAULT
        self.layout.addWidget(QLabel("LLM Provider:"))
        self.layout.addWidget(self.provider)

        # Start/Stop
        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.toggle_server)
        self.layout.addWidget(self.start_btn)

        self.status = QLabel("Status: Ready")
        self.layout.addWidget(self.status)

        # Logs
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Courier", 10))
        self.layout.addWidget(QLabel("Live Logs:"))

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
        self.layout.addLayout(filters)
        self.layout.addWidget(self.log_view)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logs)
        self.timer.start(1000)

        self.apply_dark_mode(True)

    def browse(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Project")
        if dir_path:
            self.path_edit.setText(dir_path)

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

        # BLOCK NON-GROK IF KEY MISSING
        if provider != "grok":
            key_map = {
                "openai": "OPENAI_API_KEY",
                "claude": "ANTHROPIC_API_KEY"
            }
            key_name = key_map.get(provider)
            if key_name and not os.getenv(key_name):
                reply = QMessageBox.question(
                    self, "Missing API Key",
                    f"{key_name} not found in .env\n\nUse Grok instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.provider.setCurrentText("grok")
                    provider = "grok"
                else:
                    self.status.setText("Start cancelled")
                    return

        # Generate config
        config = {
            "watch_dir": dir_path,
            "memory_file": str(Path(dir_path) / ".fgd_memory.json"),
            "context_limit": 20,
            "scan": {"max_dir_size_gb": 2, "max_files_per_scan": 5, "max_file_size_kb": 250},
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

        # Start subprocess with env
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
        except:
            pass

    def clear_filters(self):
        self.level.setCurrentIndex(0)
        self.search.clear()

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
    app = QApplication(sys.argv)
    win = FGDGUI()
    win.show()
    sys.exit(app.exec())