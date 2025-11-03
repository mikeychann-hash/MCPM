#!/usr/bin/env python3
"""
FGD Stack Pro GUI – Grok-Only by Default + Safe LLM Switching
"""

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QGroupBox,
)
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
        self.setWindowTitle("FGD Stack Pro v2.4")
        self.resize(960, 720)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(18)
        self.layout.setContentsMargins(28, 28, 28, 28)
        self.setLayout(self.layout)
        self.process = None
        self.log_file = None

        header = QLabel("FGD Stack Pro")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setObjectName("header")
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.layout.addWidget(header)

        # Directory
        dir_group = QGroupBox("Project Directory")
        dir_layout = QVBoxLayout()
        self.path_edit = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        h = QHBoxLayout()
        h.addWidget(self.path_edit)
        h.addWidget(browse)
        dir_layout.addLayout(h)
        dir_group.setLayout(dir_layout)
        self.layout.addWidget(dir_group)

        # Provider
        provider_group = QGroupBox("LLM Provider")
        provider_layout = QVBoxLayout()
        self.provider = QComboBox()
        self.provider.addItems(["grok", "openai", "claude", "ollama"])
        self.provider.setCurrentText("grok")  # GROK DEFAULT
        provider_layout.addWidget(self.provider)
        provider_group.setLayout(provider_layout)
        self.layout.addWidget(provider_group)

        # Start/Stop
        control_group = QGroupBox("Server Control")
        control_layout = QVBoxLayout()
        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.toggle_server)
        control_layout.addWidget(self.start_btn)

        self.status = QLabel("Status: Ready")
        self.status.setObjectName("status")
        control_layout.addWidget(self.status)
        control_group.setLayout(control_layout)
        self.layout.addWidget(control_group)

        # Logs
        logs_group = QGroupBox("Live Logs")
        logs_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Courier", 10))
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
        logs_layout.addLayout(filters)
        logs_layout.addWidget(self.log_view)
        logs_group.setLayout(logs_layout)
        self.layout.addWidget(logs_group)

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
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self.status.setText("Status: Stopped")
            self.start_btn.setText("Start Server")
        else:
            self.start_server()

    def start_server(self):
        dir_path = self.path_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            self.status.setText("Status: Invalid directory")
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
                    self.status.setText("Status: Start cancelled")
                    return

        # Generate config
        self.log_file = Path(dir_path) / "fgd_server.log"
        self.log_file.write_text("")

        config = {
            "watch_dir": dir_path,
            "memory_file": str(Path(dir_path) / ".fgd_memory.json"),
            "log_file": str(self.log_file),
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

        # Start subprocess with env
        env = os.environ.copy()
        try:
            self.process = subprocess.Popen(
                [sys.executable, "mcp_backend.py", str(config_path)],
                cwd=dir_path,
                env=env
            )
        except Exception as exc:
            self.status.setText(f"Status: Failed to start ({exc})")
            self.start_btn.setText("Start Server")
            self.process = None
            return

        self.status.setText(f"Status: Running ({provider})")
        self.start_btn.setText("Stop Server")

    def update_logs(self):
        if self.process and self.process.poll() is not None:
            self.status.setText("Status: Server stopped")
            self.start_btn.setText("Start Server")
            self.process = None

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

            if len(filtered) > 500:
                filtered = filtered[-500:]

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
            self.log_view.setTextColor(Qt.GlobalColor.white)
        except:
            pass

    def clear_filters(self):
        self.level.setCurrentIndex(0)
        self.search.clear()

    def apply_dark_mode(self, dark):
        if dark:
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #0d1117;
                    color: #f0f6fc;
                    font-family: 'Segoe UI', sans-serif;
                }
                QGroupBox {
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 12px;
                    font-weight: bold;
                    color: #f0f6fc;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 4px 0 4px;
                }
                QPushButton {
                    background-color: #238636;
                    color: #ffffff;
                    padding: 8px 16px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #2ea043;
                }
                QPushButton:disabled {
                    background-color: #161b22;
                    color: #8b949e;
                }
                QLineEdit, QComboBox {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 6px 8px;
                    color: #f0f6fc;
                }
                QTextEdit {
                    background-color: #010409;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 8px;
                }
                QLabel#status {
                    font-size: 14px;
                }
                QLabel#header {
                    color: #58a6ff;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #f7f9fc;
                    color: #24292f;
                    font-family: 'Segoe UI', sans-serif;
                }
                QGroupBox {
                    border: 1px solid #d0d7de;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 12px;
                    font-weight: bold;
                    color: #24292f;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 4px 0 4px;
                }
                QPushButton {
                    background-color: #0969da;
                    color: #ffffff;
                    padding: 8px 16px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #218bff;
                }
                QPushButton:disabled {
                    background-color: #d0d7de;
                    color: #57606a;
                }
                QLineEdit, QComboBox {
                    background-color: #ffffff;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    padding: 6px 8px;
                    color: #24292f;
                }
                QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #d0d7de;
                    border-radius: 8px;
                    padding: 8px;
                }
                QLabel#status {
                    font-size: 14px;
                }
                QLabel#header {
                    color: #0969da;
                }
                """
            )

    def closeEvent(self, event):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FGDGUI()
    win.show()
    sys.exit(app.exec())
