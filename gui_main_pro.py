#!/usr/bin/env python3
#!/usr/bin/env python3
"""MCPM v5.0 GUI – Beautiful Modern Interface."""

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QFileDialog,
    QLabel,
    QListWidget,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QPoint,
    QSize,
    QTimer,
    Qt,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QTextCharFormat,
    QTextCursor,
    QSyntaxHighlighter,
)
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
import math
from typing import Dict, List, Optional

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

def _color(hex_color: str, alpha: int = 255) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color


def _mix_hex(color_a: str, color_b: str, progress: float) -> str:
    progress = max(0.0, min(1.0, progress))
    start = QColor(color_a)
    end = QColor(color_b)
    r = round(start.red() + (end.red() - start.red()) * progress)
    g = round(start.green() + (end.green() - start.green()) * progress)
    b = round(start.blue() + (end.blue() - start.blue()) * progress)
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------- #
# -------------------------- SYNTAX HIGHLIGHTER ----------------------------- #
# --------------------------------------------------------------------------- #
class PythonHighlighter(QSyntaxHighlighter):
    """Feature-rich syntax highlighter tuned for the MCPM editor."""

    KEYWORDS = [
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "False",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "None",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "True",
        "try",
        "while",
        "with",
        "yield",
    ]

    BUILTINS = [
        "abs",
        "any",
        "all",
        "bool",
        "bytes",
        "callable",
        "dict",
        "enumerate",
        "float",
        "format",
        "getattr",
        "hasattr",
        "int",
        "len",
        "list",
        "map",
        "max",
        "min",
        "open",
        "print",
        "range",
        "set",
        "sorted",
        "str",
        "sum",
        "type",
        "zip",
    ]

    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules: List[tuple[re.Pattern, QTextCharFormat]] = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(_color("#bd93f9"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        for keyword in self.KEYWORDS:
            self.highlighting_rules.append((re.compile(rf"\b{keyword}\b"), keyword_format))

        builtin_format = QTextCharFormat()
        builtin_format.setForeground(_color("#8be9fd"))
        for builtin in self.BUILTINS:
            self.highlighting_rules.append((re.compile(rf"\b{builtin}\b"), builtin_format))

        decorator_format = QTextCharFormat()
        decorator_format.setForeground(_color("#ff79c6"))
        decorator_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"@[_A-Za-z][_A-Za-z0-9.]*"), decorator_format))

        class_format = QTextCharFormat()
        class_format.setForeground(_color("#50fa7b"))
        class_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"\bclass\s+([_A-Za-z][_A-Za-z0-9]*)"), class_format))

        function_format = QTextCharFormat()
        function_format.setForeground(_color("#50fa7b"))
        self.highlighting_rules.append((re.compile(r"\bdef\s+([_A-Za-z][_A-Za-z0-9]*)"), function_format))

        number_format = QTextCharFormat()
        number_format.setForeground(_color("#f1fa8c"))
        self.highlighting_rules.append((re.compile(r"\b0[bB][01_]+\b"), number_format))
        self.highlighting_rules.append((re.compile(r"\b0[oO][0-7_]+\b"), number_format))
        self.highlighting_rules.append((re.compile(r"\b0[xX][0-9a-fA-F_]+\b"), number_format))
        self.highlighting_rules.append((re.compile(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?j?\b"), number_format))

        single_string_format = QTextCharFormat()
        single_string_format.setForeground(_color("#f1fa8c"))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), single_string_format))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), single_string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(_color("#6272a4"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r"#[^\n]*"), comment_format))

        todo_format = QTextCharFormat()
        todo_format.setForeground(_color("#ffb86c"))
        todo_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"#.*\b(TODO|FIXME|NOTE)\b.*"), todo_format))

        self.multi_line_string_format = QTextCharFormat()
        self.multi_line_string_format.setForeground(_color("#f1fa8c"))

        self._current_delimiter: Optional[str] = None

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

        continued = False
        if self.previousBlockState() == 1 and self._current_delimiter:
            continued = self._match_multiline(text, self._current_delimiter, start_in_block=True)
            if continued:
                return

        self._current_delimiter = None
        if self._match_multiline(text, "'''"):
            self._current_delimiter = "'''"
            return
        if self._match_multiline(text, '"""'):
            self._current_delimiter = '"""'

    def _match_multiline(self, text: str, delimiter: str, *, start_in_block: bool = False) -> bool:
        start = text.find(delimiter) if not start_in_block else 0
        length = len(delimiter)
        if start == -1 and not start_in_block:
            return False

        while start >= 0:
            end = text.find(delimiter, start + length)
            if end >= 0:
                span = end - start + length
                self.setFormat(start, span, self.multi_line_string_format)
                start = text.find(delimiter, end + length)
                if start_in_block:
                    self.setCurrentBlockState(0)
                    self._current_delimiter = None
                    return True
            else:
                self.setFormat(start, len(text) - start, self.multi_line_string_format)
                self.setCurrentBlockState(1)
                self._current_delimiter = delimiter
                return True
        return start_in_block


# --------------------------------------------------------------------------- #
# ------------------------ CUSTOM UI COMPONENTS ----------------------------- #
# --------------------------------------------------------------------------- #
class AnimatedButton(QPushButton):
    """Gradient button with hover scaling and animated feedback."""

    def __init__(self, text: str, gradient: Optional[tuple[str, str]] = None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.gradient = gradient or ("#667eea", "#764ba2")
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._gradient_shift = 0.0

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.setStyleSheet("color: white; border: none; padding: 0 20px;")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setOffset(0, 12)
        shadow.setBlurRadius(32)
        shadow.setColor(_color("#000000", 120))
        self.setGraphicsEffect(shadow)

        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(240)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_anim = QPropertyAnimation(self, b"pressProgress", self)
        self._press_anim.setDuration(140)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._gradient_timer = QTimer(self)
        self._gradient_timer.timeout.connect(self._advance_gradient)
        self._gradient_timer.start(60)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(max(hint.width(), 160), max(hint.height(), 44))

    def enterEvent(self, event):  # noqa: D401 - Qt override
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: D401 - Qt override
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):  # noqa: D401 - Qt override
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press_progress)
        self._press_anim.setEndValue(1.0)
        self._press_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: D401 - Qt override
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press_progress)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()
        super().mouseReleaseEvent(event)

    def _advance_gradient(self) -> None:
        self._gradient_shift = (self._gradient_shift + 0.01) % 1.0
        self.update()

    def paintEvent(self, event):  # noqa: D401 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)

        scale = 1.0 + 0.04 * self._hover_progress - 0.02 * self._press_progress
        painter.translate(rect.center())
        painter.scale(scale, scale)
        painter.translate(-rect.center())

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        shift = self._gradient_shift
        gradient.setColorAt((shift + 0.0) % 1.0, QColor(self.gradient[0]))
        gradient.setColorAt((shift + 0.5) % 1.0, QColor(self.gradient[1]))
        gradient.setColorAt((shift + 1.0) % 1.0, QColor(self.gradient[0]))

        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(path)

        overlay_color = QColor("white")
        overlay_color.setAlphaF(0.1 * self._hover_progress + 0.05 * self._press_progress)
        painter.setBrush(overlay_color)
        painter.drawPath(path)

        painter.resetTransform()
        painter.setPen(QColor("white"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = value
        self.update()

    def get_press_progress(self) -> float:
        return self._press_progress

    def set_press_progress(self, value: float) -> None:
        self._press_progress = value
        self.update()

    hoverProgress = pyqtProperty(float, fget=get_hover_progress, fset=set_hover_progress)
    pressProgress = pyqtProperty(float, fget=get_press_progress, fset=set_press_progress)


class GlassCard(QWidget):
    """Semi-transparent container with a soft drop shadow."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setOffset(0, 18)
        shadow.setBlurRadius(40)
        shadow.setColor(_color("#000000", 150))
        self.setGraphicsEffect(shadow)
        self.setContentsMargins(0, 0, 0, 0)

    def paintEvent(self, event):  # noqa: D401 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, _color("#ffffff", 30))
        gradient.setColorAt(1.0, _color("#667eea", 35))

        painter.setPen(QPen(_color("#ffffff", 45), 2))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 20, 20)


class AnimatedLineEdit(QLineEdit):
    """Line edit with animated focus glow."""

    def __init__(self, placeholder: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._focus_progress = 0.0
        self.setPlaceholderText(placeholder)
        self.setFont(QFont("Segoe UI", 11))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("color: #f0f6fc; padding: 12px 16px; background: transparent; border: none;")

        self._focus_anim = QPropertyAnimation(self, b"focusProgress", self)
        self._focus_anim.setDuration(260)
        self._focus_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def focusInEvent(self, event):  # noqa: D401 - Qt override
        self._animate_focus(1.0)
        super().focusInEvent(event)

    def focusOutEvent(self, event):  # noqa: D401 - Qt override
        self._animate_focus(0.0)
        super().focusOutEvent(event)

    def _animate_focus(self, target: float) -> None:
        self._focus_anim.stop()
        self._focus_anim.setStartValue(self._focus_progress)
        self._focus_anim.setEndValue(target)
        self._focus_anim.start()

    def paintEvent(self, event):  # noqa: D401 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)

        base_color = _color("#0d1117", 220)
        painter.setBrush(base_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 14, 14)

        border_color = QColor("#667eea")
        border_color.setAlphaF(0.15 + 0.45 * self._focus_progress)
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 14, 14)

        glow_color = QColor("#764ba2")
        glow_color.setAlphaF(0.2 * self._focus_progress)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow_color)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)

        super().paintEvent(event)

    def get_focus_progress(self) -> float:
        return self._focus_progress

    def set_focus_progress(self, value: float) -> None:
        self._focus_progress = value
        self.update()

    focusProgress = pyqtProperty(float, fget=get_focus_progress, fset=set_focus_progress)


class ModernTabWidget(QTabWidget):
    """Tab widget with a frosted pane and smooth indicator."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setDocumentMode(True)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid rgba(102, 126, 234, 0.35);
                border-radius: 18px;
                background: rgba(13, 17, 23, 0.65);
                padding: 18px 18px 12px 18px;
            }
            QTabBar::tab {
                background: rgba(48, 54, 61, 0.6);
                color: #f0f6fc;
                padding: 14px 28px;
                margin-right: 6px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                transition: all 220ms ease;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
            }
            QTabBar::tab:hover {
                background: rgba(102, 126, 234, 0.35);
            }
        """)


class AnimatedStatusLabel(QLabel):
    """Status label featuring a pulsing indicator and smooth color changes."""

    STATUS_COLORS: Dict[str, str] = {
        "ready": "#50fa7b",
        "running": "#50fa7b",
        "warning": "#f1fa8c",
        "error": "#ff5555",
        "stopped": "#ff79c6",
    }

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._pulse = 0.0
        self._indicator_color = QColor(self.STATUS_COLORS["ready"])
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.setContentsMargins(32, 0, 0, 0)

        self._pulse_anim = QPropertyAnimation(self, b"pulseProgress", self)
        self._pulse_anim.setDuration(1200)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.start()

    def paintEvent(self, event):  # noqa: D401 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPoint(self.rect().left() + 16, self.rect().center().y())

        pulse_radius = 8 + 4 * math.sin(self._pulse * math.pi)
        gradient = QRadialGradient(center, pulse_radius)
        base_color = QColor(self._indicator_color)
        gradient.setColorAt(0.0, base_color)
        fading = QColor(self._indicator_color)
        fading.setAlpha(40)
        gradient.setColorAt(1.0, fading)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(center, pulse_radius, pulse_radius)

        painter.setBrush(self._indicator_color)
        painter.drawEllipse(center, 6, 6)

        super().paintEvent(event)

    def set_status(self, status: str, message: str) -> None:
        color = QColor(self.STATUS_COLORS.get(status, "#50fa7b"))
        self._indicator_color = color
        self.setText(message)
        if status in {"running", "warning"}:
            if self._pulse_anim.state() != QPropertyAnimation.Running:
                self._pulse_anim.start()
        else:
            if self._pulse_anim.state() == QPropertyAnimation.Running:
                self._pulse_anim.stop()
                self._pulse_anim.start()
                self._pulse_anim.stop()
                self._pulse = 0.0
                self.update()

    def get_pulse_progress(self) -> float:
        return self._pulse

    def set_pulse_progress(self, value: float) -> None:
        self._pulse = value
        self.update()

    pulseProgress = pyqtProperty(float, fget=get_pulse_progress, fset=set_pulse_progress)

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
            self.resize(1680, 1020)
            self.setMinimumSize(1280, 820)
            self.main_layout = QVBoxLayout()
            self.main_layout.setContentsMargins(36, 28, 36, 28)
            self.main_layout.setSpacing(24)
            self.setLayout(self.main_layout)
            self.process = None
            self.log_file = None
            self.pending_action = None
            self.pending_edit = None
            self.pop_out_windows = []
            self.memory_file_path: Optional[Path] = None
            self._memory_last_mtime: Optional[float] = None
            self._log_colors = {
                "error": QColor("#ff5555"),
                "warning": QColor("#f1fa8c"),
                "success": QColor("#50fa7b"),
                "default": QColor("#f0f6fc"),
            }
            self._header_phase = 0.0

            self._fade_in_intro()

            self._build_ui()
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_logs)
            self.timer.start(1000)

            self._start_header_animation()
            self.apply_dark_mode()
            logger.info("GUI initialized successfully")
        except Exception as e:
            logger.error(f"GUI initialization failed: {e}")
            logger.error(traceback.format_exc())
            # Don't try to show QMessageBox here - let the main error handler deal with it
            # QMessageBox requires an event loop which may not be running yet
            raise

    def _build_ui(self):
        self._add_header()
        body_layout = QHBoxLayout()
        body_layout.setSpacing(24)
        self.main_layout.addLayout(body_layout)

        control_panel = self._create_control_panel()
        body_layout.addWidget(control_panel, 0)

        tabs_widget = self._create_main_tabs()
        body_layout.addWidget(tabs_widget, 1)

        self._add_status_bar()

    def _fade_in_intro(self) -> None:
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        self._fade_anim = QPropertyAnimation(effect, b"opacity", self)
        self._fade_anim.setDuration(820)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def _start_header_animation(self) -> None:
        self._header_timer = QTimer(self)
        self._header_timer.timeout.connect(self._tick_header_gradient)
        self._header_timer.start(90)

    def _tick_header_gradient(self) -> None:
        self._header_phase = (self._header_phase + 0.02) % 1.0
        wave = (math.sin(self._header_phase * 2 * math.pi) + 1) / 2
        color_a = _mix_hex("#667eea", "#764ba2", wave)
        color_b = _mix_hex("#764ba2", "#f093fb", 1 - wave * 0.6)
        if hasattr(self, "header"):
            self.header.setStyleSheet(self._header_style_template.format(color_a=color_a, color_b=color_b))

    def _add_header(self):
        """Add the gradient header banner."""
        self.header = QLabel("MCPM v5.0 – AI Code Co‑Pilot 🚀")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header.setMinimumHeight(82)
        self._header_style_template = """
            font-size: 38px;
            font-weight: 800;
            margin: 0 0 12px 0;
            letter-spacing: 2px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {color_a}, stop:0.5 #764ba2, stop:1 {color_b});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            color: {color_a};
        """
        self.header.setStyleSheet(self._header_style_template.format(color_a="#667eea", color_b="#f093fb"))
        self.main_layout.addWidget(self.header)

        subtitle = QLabel("A modern mission control for your MCP server")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: rgba(240, 246, 252, 0.75); font-size: 16px; margin-bottom: 16px;")
        self.main_layout.addWidget(subtitle)

    def _create_main_tabs(self) -> QWidget:
        """Construct the tab widget container."""
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)
        container.setLayout(container_layout)

        self.tabs = ModernTabWidget()
        self.tabs.addTab(self._create_explorer_tab(), "📁 File Explorer")
        self.tabs.addTab(self._create_diff_tab(), "🔍 Diff Viewer")
        self.tabs.addTab(self._create_logs_tab(), "📋 Live Logs")
        self.tabs.addTab(self._create_memory_tab(), "🧠 Memory Explorer")
        self.tabs.addTab(self._create_backups_tab(), "💾 Backups")

        container_layout.addWidget(self.tabs)
        return container

    def _create_control_panel(self):
        """Create the glassmorphic control center."""
        card = GlassCard()
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)
        card.setLayout(layout)

        title = QLabel("Control Center")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #f0f6fc;")
        layout.addWidget(title)

        dir_group = QVBoxLayout()
        dir_label = QLabel("📂 Project Directory")
        dir_label.setStyleSheet("color: rgba(240, 246, 252, 0.85); font-size: 13px; font-weight: 600;")
        dir_group.addWidget(dir_label)

        dir_row = QHBoxLayout()
        self.path_edit = AnimatedLineEdit("Select your project workspace…")
        browse = AnimatedButton("Browse", gradient=("#8a5cf6", "#a16ae8"))
        browse.clicked.connect(self.browse)
        dir_row.addWidget(self.path_edit)
        dir_row.addWidget(browse)
        dir_group.addLayout(dir_row)
        layout.addLayout(dir_group)

        provider_group = QVBoxLayout()
        provider_label = QLabel("🤖 Default LLM Provider")
        provider_label.setStyleSheet("color: rgba(240, 246, 252, 0.85); font-size: 13px; font-weight: 600;")
        provider_group.addWidget(provider_label)

        provider_row = QHBoxLayout()
        self.provider = QComboBox()
        self.provider.addItems(["grok", "openai", "claude", "ollama"])
        self.provider.setCurrentText("grok")
        self.provider.setStyleSheet("""
            QComboBox {
                background: rgba(13, 17, 23, 0.75);
                color: #f0f6fc;
                border: 1px solid rgba(102, 126, 234, 0.4);
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background: #0d1117;
                color: #f0f6fc;
                selection-background-color: #667eea;
                border-radius: 8px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)

        self.start_btn = AnimatedButton("▶ Start Server", gradient=("#50fa7b", "#5fff8a"))
        self.start_btn.clicked.connect(self.toggle_server)

        provider_row.addWidget(self.provider)
        provider_row.addWidget(self.start_btn)
        provider_group.addLayout(provider_row)
        layout.addLayout(provider_group)

        self.connection_status = AnimatedStatusLabel("🟢 Ready to connect")
        layout.addWidget(self.connection_status)

        tips = QLabel(
            "• Hover over cards to feel the depth\n"
            "• Use the Memory Explorer tab to inspect stored context\n"
            "• Logs update live – filter them in the Logs tab"
        )
        tips.setStyleSheet("color: rgba(240, 246, 252, 0.55); font-size: 11px; line-height: 1.5;")
        layout.addWidget(tips)
        layout.addStretch()

        return card

    def _add_status_bar(self) -> None:
        bar = GlassCard()
        bar_layout = QHBoxLayout()
        bar_layout.setContentsMargins(24, 12, 24, 12)
        bar_layout.setSpacing(18)
        bar.setLayout(bar_layout)

        self.memory_usage_label = QLabel("Memory file: —")
        self.memory_usage_label.setStyleSheet("color: rgba(240, 246, 252, 0.7); font-size: 12px;")

        self.log_summary_label = QLabel("Logs idle")
        self.log_summary_label.setStyleSheet("color: rgba(240, 246, 252, 0.7); font-size: 12px;")

        bar_layout.addWidget(self.memory_usage_label)
        bar_layout.addStretch()
        bar_layout.addWidget(self.log_summary_label)

        self.main_layout.addWidget(bar)

    def _create_explorer_tab(self):
        """Create the file explorer tab with glassmorphism."""
        card = GlassCard()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        card.setLayout(layout)

        header = QHBoxLayout()
        label = QLabel("📁 Repository Navigator")
        label.setStyleSheet("font-size: 18px; font-weight: 600; color: #f0f6fc;")
        pop_out_btn = AnimatedButton("Pop Out Preview", gradient=("#667eea", "#764ba2"))
        pop_out_btn.setMinimumWidth(200)
        pop_out_btn.clicked.connect(self.pop_out_preview)
        header.addWidget(label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        split = QSplitter()
        split.setOrientation(Qt.Orientation.Horizontal)
        split.setStyleSheet("QSplitter::handle { background: rgba(102, 126, 234, 0.35); width: 4px; }")

        tree_container = QWidget()
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(12)
        tree_container.setLayout(tree_layout)

        tree_caption = QLabel("Structure")
        tree_caption.setStyleSheet("color: rgba(240, 246, 252, 0.75); font-size: 13px;")
        tree_layout.addWidget(tree_caption)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Files")
        self.tree.itemClicked.connect(self.on_file_click)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: rgba(13, 17, 23, 0.85);
                color: #f0f6fc;
                border: 1px solid rgba(102, 126, 234, 0.35);
                border-radius: 14px;
                font-size: 13px;
                padding: 12px;
            }
            QTreeWidget::item { padding: 6px; }
            QTreeWidget::item:selected {
                background: rgba(102, 126, 234, 0.35);
                border-radius: 8px;
            }
            QTreeWidget::item:hover {
                background: rgba(102, 126, 234, 0.18);
            }
        """)
        tree_layout.addWidget(self.tree)

        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(12)
        preview_container.setLayout(preview_layout)

        preview_header = QLabel("📄 Focused Preview")
        preview_header.setStyleSheet("color: rgba(240, 246, 252, 0.85); font-size: 13px;")
        preview_layout.addWidget(preview_header)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Fira Code", 11))
        self.preview.setStyleSheet("""
            QTextEdit {
                background: rgba(13, 17, 23, 0.85);
                color: #f0f6fc;
                border: 1px solid rgba(118, 75, 162, 0.35);
                border-radius: 14px;
                padding: 16px;
                font-size: 11.5pt;
                line-height: 1.55;
            }
        """)
        self.preview_highlighter = PythonHighlighter(self.preview.document())
        preview_layout.addWidget(self.preview)

        split.addWidget(tree_container)
        split.addWidget(preview_container)
        split.setSizes([420, 1080])

        layout.addWidget(split)
        return card

    def _create_diff_tab(self):
        """Create the modern diff review tab."""
        card = GlassCard()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        card.setLayout(layout)

        header = QHBoxLayout()
        diff_label = QLabel("🔍 Pending Edit Review")
        diff_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #f0f6fc;")
        pop_out_btn = AnimatedButton("Open in Window", gradient=("#667eea", "#764ba2"))
        pop_out_btn.clicked.connect(self.pop_out_diff)
        header.addWidget(diff_label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Fira Code", 12))
        self.diff_view.setStyleSheet("""
            QTextEdit {
                background: rgba(13, 17, 23, 0.88);
                color: #f0f6fc;
                border: 1px solid rgba(102, 126, 234, 0.4);
                border-radius: 16px;
                padding: 20px;
                font-size: 12pt;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.diff_view)

        btns = QHBoxLayout()
        btns.setSpacing(16)
        self.approve_btn = AnimatedButton("✅ Approve Changes", gradient=("#50fa7b", "#5fff8a"))
        self.approve_btn.setMinimumHeight(54)
        self.approve_btn.clicked.connect(self.approve_edit)

        self.reject_btn = AnimatedButton("❌ Reject Changes", gradient=("#ff5555", "#ff6e6e"))
        self.reject_btn.setMinimumHeight(54)
        self.reject_btn.clicked.connect(self.reject_edit)

        btns.addWidget(self.approve_btn)
        btns.addWidget(self.reject_btn)
        layout.addLayout(btns)

        self._highlight_decision_buttons(False)
        return card

    def _highlight_decision_buttons(self, highlighted: bool) -> None:
        if not hasattr(self, "approve_btn"):
            return
        if highlighted:
            self.approve_btn.gradient = ("#5fff8a", "#8dffb8")
            self.reject_btn.gradient = ("#ff6e6e", "#ff8989")
        else:
            self.approve_btn.gradient = ("#50fa7b", "#5fff8a")
            self.reject_btn.gradient = ("#ff5555", "#ff6e6e")
        self.approve_btn.update()
        self.reject_btn.update()

    def _create_logs_tab(self):
        """Create the animated logs tab."""
        card = GlassCard()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        card.setLayout(layout)

        header = QHBoxLayout()
        log_label = QLabel("📋 Live Server Logs")
        log_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #f0f6fc;")
        pop_out_btn = AnimatedButton("Open in Window", gradient=("#667eea", "#764ba2"))
        pop_out_btn.clicked.connect(self.pop_out_logs)
        header.addWidget(log_label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(12)
        level_label = QLabel("Level")
        level_label.setStyleSheet("color: rgba(240, 246, 252, 0.7); font-size: 13px; font-weight: 600;")
        self.level = QComboBox()
        self.level.addItems(["All", "INFO", "WARNING", "ERROR"])
        self.level.setStyleSheet("""
            QComboBox {
                background: rgba(13, 17, 23, 0.78);
                color: #f0f6fc;
                border: 1px solid rgba(102, 126, 234, 0.35);
                border-radius: 12px;
                padding: 10px 14px;
            }
            QComboBox QAbstractItemView {
                background: #0d1117;
                color: #f0f6fc;
                selection-background-color: #667eea;
                border-radius: 8px;
            }
        """)

        search_label = QLabel("Search")
        search_label.setStyleSheet("color: rgba(240, 246, 252, 0.7); font-size: 13px; font-weight: 600;")
        self.search = AnimatedLineEdit("Search logs…")
        self.search.textChanged.connect(lambda: self.update_logs())
        self.level.currentIndexChanged.connect(lambda: self.update_logs())

        clear = AnimatedButton("Clear Filters", gradient=("#8a5cf6", "#a16ae8"))
        clear.clicked.connect(self.clear_filters)

        filters.addWidget(level_label)
        filters.addWidget(self.level)
        filters.addWidget(search_label)
        filters.addWidget(self.search)
        filters.addWidget(clear)
        layout.addLayout(filters)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Fira Code", 11))
        self.log_view.setStyleSheet("""
            QTextEdit {
                background: rgba(13, 17, 23, 0.88);
                color: #f0f6fc;
                border: 1px solid rgba(102, 126, 234, 0.35);
                border-radius: 16px;
                padding: 18px;
                font-size: 11.5pt;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.log_view)

        return card

    def _create_memory_tab(self):
        """Create the interactive memory explorer tab."""
        card = GlassCard()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        card.setLayout(layout)

        header = QHBoxLayout()
        label = QLabel("🧠 Memory Explorer")
        label.setStyleSheet("font-size: 18px; font-weight: 600; color: #f0f6fc;")
        refresh = AnimatedButton("Refresh", gradient=("#50fa7b", "#5fff8a"))
        refresh.setMinimumWidth(160)
        refresh.clicked.connect(lambda: self.update_memory_explorer(force=True))
        header.addWidget(label)
        header.addStretch()
        header.addWidget(refresh)
        layout.addLayout(header)

        description = QLabel("Visualise what the MCP backend remembers about your project.")
        description.setStyleSheet("color: rgba(240, 246, 252, 0.65); font-size: 13px;")
        layout.addWidget(description)

        self.memory_tree = QTreeWidget()
        self.memory_tree.setColumnCount(2)
        self.memory_tree.setHeaderLabels(["Key", "Value"])
        self.memory_tree.setStyleSheet("""
            QTreeWidget {
                background: rgba(13, 17, 23, 0.85);
                color: #f0f6fc;
                border: 1px solid rgba(102, 126, 234, 0.35);
                border-radius: 16px;
                padding: 12px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 6px;
            }
            QTreeWidget::item:selected {
                background: rgba(118, 75, 162, 0.35);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.memory_tree)

        self.memory_info = QLabel("No memory file detected yet.")
        self.memory_info.setStyleSheet("color: rgba(240, 246, 252, 0.6); font-size: 12px;")
        layout.addWidget(self.memory_info)

        return card

    def _create_backups_tab(self):
        """Create backups viewer tab"""
        card = GlassCard()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        card.setLayout(layout)

        backup_label = QLabel("💾 File Backups")
        backup_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #f0f6fc;")
        layout.addWidget(backup_label)

        self.backup_list = QListWidget()
        self.backup_list.setStyleSheet("""
            QListWidget {
                background: rgba(13, 17, 23, 0.85);
                color: #f0f6fc;
                border: 1px solid rgba(102, 126, 234, 0.35);
                border-radius: 16px;
                padding: 14px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background: rgba(102, 126, 234, 0.35);
            }
            QListWidget::item:hover {
                background: rgba(102, 126, 234, 0.18);
            }
        """)
        layout.addWidget(self.backup_list)

        return card

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
            self.memory_file_path = Path(dir_path) / ".fgd_memory.json"
            self._memory_last_mtime = None
            self.update_memory_explorer(force=True)
            self._update_memory_usage()

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
            self.connection_status.set_status("stopped", "🔴 Server stopped")
            self.start_btn.setText("▶ Start Server")
            self._highlight_decision_buttons(False)
            if hasattr(self, "log_summary_label"):
                self.log_summary_label.setText("Server stopped")
            self.process = None
        else:
            self.start_server()

    def start_server(self):
        dir_path = self.path_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            self.connection_status.set_status("error", "🔴 Invalid project directory")
            return

        provider = self.provider.currentText()
        self.memory_file_path = Path(dir_path) / ".fgd_memory.json"
        self._memory_last_mtime = None
        self._update_memory_usage()

        config = {
            "watch_dir": dir_path,
            "memory_file": str(self.memory_file_path),
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

        # Use absolute path to mcp_backend.py (in MCPM directory, not user's project)
        mcpm_root = Path(__file__).parent.resolve()
        backend_script = mcpm_root / "mcp_backend.py"

        if not backend_script.exists():
            logger.error(f"Backend script not found: {backend_script}")
            self.connection_status.set_status("error", "🚨 Backend script missing")
            QMessageBox.critical(self, "Missing Backend", f"Could not find mcp_backend.py at:\n{backend_script}")
            return

        logger.info(f"Starting backend: {backend_script}")
        logger.info(f"Config path: {config_path}")
        logger.info(f"Working directory: {mcpm_root}")

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(backend_script), str(config_path)],
                cwd=str(mcpm_root),  # Run from MCPM directory, not user's project
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as exc:
            logger.error(f"Failed to launch backend: {exc}")
            self.connection_status.set_status("error", "🚨 Failed to launch backend")
            QMessageBox.critical(self, "Launch Error", f"Could not start backend:\n{exc}")
            return

        # Start background threads to read subprocess output
        stdout_thread = threading.Thread(target=self._read_subprocess_stdout, daemon=True)
        stderr_thread = threading.Thread(target=self._read_subprocess_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        logger.info("Subprocess output monitoring threads started")

        self.connection_status.set_status("running", f"🟢 Running on {provider}")
        self.start_btn.setText("⏹ Stop Server")
        self.log_summary_label.setText("Awaiting log data…")
        self.update_memory_explorer(force=True)

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
                self.log_view.setTextColor(self._log_color_for_line(line))
                self.log_view.insertPlainText(line + "\n")

            if hasattr(self, "log_summary_label"):
                self.log_summary_label.setText(f"Showing {len(filtered)} log lines")

            self._update_memory_usage()
            self.update_memory_explorer()

            # Check for pending edits
            self.check_pending_edits()
        except Exception as e:
            logger.debug(f"Error updating logs: {e}")

    def update_memory_explorer(self, force: bool = False) -> None:
        if not hasattr(self, "memory_tree"):
            return
        if not self.memory_file_path:
            self.memory_tree.clear()
            self.memory_info.setText("No project selected yet.")
            return

        memory_path = self.memory_file_path
        if not memory_path.exists():
            if force:
                self.memory_tree.clear()
                self.memory_info.setText("Memory file not generated yet.")
            return

        try:
            stat = memory_path.stat()
            if not force and self._memory_last_mtime and stat.st_mtime <= self._memory_last_mtime:
                return

            data = json.loads(memory_path.read_text())
            self.memory_tree.clear()
            self._populate_memory_tree(data, self.memory_tree.invisibleRootItem())
            self.memory_tree.expandToDepth(1)
            self._memory_last_mtime = stat.st_mtime
            timestamp = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            self.memory_info.setText(f"Last updated: {timestamp}")
            self._update_memory_usage(stat.st_size)
        except Exception as exc:
            self.memory_tree.clear()
            self.memory_info.setText(f"Unable to read memory file: {exc}")

    def _populate_memory_tree(self, data, parent: Optional[QTreeWidgetItem]) -> None:
        if parent is None:
            return
        if isinstance(data, dict):
            for key, value in data.items():
                child = QTreeWidgetItem([str(key), self._format_memory_value(value)])
                parent.addChild(child)
                if isinstance(value, (dict, list)):
                    child.setFirstColumnSpanned(True)
                    self._populate_memory_tree(value, child)
        elif isinstance(data, list):
            for idx, value in enumerate(data):
                child = QTreeWidgetItem([f"[{idx}]", self._format_memory_value(value)])
                parent.addChild(child)
                if isinstance(value, (dict, list)):
                    child.setFirstColumnSpanned(True)
                    self._populate_memory_tree(value, child)

    def _format_memory_value(self, value) -> str:
        if isinstance(value, (dict, list)):
            return f"{type(value).__name__} ({len(value)})"
        if isinstance(value, str):
            trimmed = value.strip()
            if len(trimmed) > 80:
                trimmed = trimmed[:77] + "…"
            return trimmed
        return str(value)

    def _update_memory_usage(self, size_bytes: Optional[int] = None) -> None:
        if not hasattr(self, "memory_usage_label"):
            return
        if size_bytes is None and self.memory_file_path and self.memory_file_path.exists():
            size_bytes = self.memory_file_path.stat().st_size
        if not size_bytes:
            self.memory_usage_label.setText("Memory file: —")
            return
        if size_bytes < 1024:
            human = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            human = f"{size_bytes / 1024:.1f} KB"
        else:
            human = f"{size_bytes / (1024 * 1024):.2f} MB"
        self.memory_usage_label.setText(f"Memory file: {human}")

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
            self._highlight_decision_buttons(True)

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
                self._highlight_decision_buttons(False)
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
                self._highlight_decision_buttons(False)
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
                    stop:0 #0b0f2c, stop:0.4 #1c1f4a, stop:0.8 #2f1f4e, stop:1 #0b0f2c);
                color: #f0f6fc;
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QMessageBox {
                background: #0d1117;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 14px;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7f89ff, stop:1 #8a5cf6);
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 14px;
                margin: 4px;
            }
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 7px;
            }
        """)

    def closeEvent(self, event):
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
        if hasattr(self, "_header_timer") and self._header_timer.isActive():
            self._header_timer.stop()
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except Exception:
                pass
        for window in self.pop_out_windows:
            window.close()
        event.accept()

    def _log_color_for_line(self, line: str) -> QColor:
        """Return the cached color brush for a given log line."""
        line_lower = line.lower()
        if "error" in line_lower:
            return self._log_colors["error"]
        if "warning" in line_lower:
            return self._log_colors["warning"]
        if "✅" in line or "success" in line_lower:
            return self._log_colors["success"]
        return self._log_colors["default"]


def _run_app() -> tuple[int, Optional[QApplication]]:
    """Entry point wrapper that bootstraps the Qt application."""
    logger.info("Starting MCPM GUI...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Qt application arguments: {sys.argv}")

    app = QApplication(sys.argv)
    logger.info("QApplication created successfully")

    try:
        logger.info("Initializing FGDGUI window...")
        win = FGDGUI()
        logger.info("FGDGUI window initialized successfully")

        win.show()
        win.raise_()  # Bring window to front
        win.activateWindow()  # Give window focus
        logger.info("GUI window displayed, starting event loop...")

        exit_code = app.exec()
        logger.info(f"Event loop finished with exit code: {exit_code}")
        return exit_code, app
    except Exception as e:
        logger.error(f"Exception during GUI initialization: {e}")
        logger.error(traceback.format_exc())
        # Return app instance so error dialog can use event loop
        raise  # Re-raise so main block can handle it


def _show_startup_error(exc: Exception, app: Optional[QApplication] = None) -> None:
    """Display a fatal startup error message to the user."""
    message = (
        f"Application failed to start:\n{exc}\n\n"
        "Check mcpm_gui.log for details.\n\nPress OK to exit."
    )

    # Always print to console first
    print(f"\n{'=' * 60}\nFATAL ERROR:\n{exc}\n{traceback.format_exc()}\n{'=' * 60}")

    # If we have a QApplication instance, ensure event loop is available for the dialog
    if app is not None:
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Fatal Error")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()  # This creates a local event loop for the dialog
        except Exception as dialog_error:
            logger.error(f"Could not display error dialog: {dialog_error}")


if __name__ == "__main__":
    exit_code = 0
    app_instance = None

    logger.info("=" * 60)
    logger.info("MCPM GUI Starting")
    logger.info("=" * 60)

    try:
        exit_code, app_instance = _run_app()
        logger.info(f"Application exited with code: {exit_code}")
    except Exception as exc:
        logger.critical(f"Fatal error during startup: {exc}")
        logger.critical(traceback.format_exc())
        _show_startup_error(exc, app_instance)
        exit_code = 1
    finally:
        if exit_code != 0:
            print("\n" + "=" * 60)
            print("The application encountered an error and will now close.")
            print("Check mcpm_gui.log for detailed error information.")
            print("=" * 60)
            input("\nPress Enter to close...")

    logger.info("Application shutdown complete")
    sys.exit(exit_code)
