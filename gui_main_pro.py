#!/usr/bin/env python3
"""MCPM v6.0 GUI – Ultra-Modern Interface with Neo Cyber Design."""

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGraphicsBlurEffect,
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
    QDialog,
    QCheckBox,
)
from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QPoint,
    QPointF,
    QRectF,
    QSize,
    QTimer,
    Qt,
    pyqtProperty,
    pyqtSignal,
    QSettings,
    QAbstractAnimation,
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
    QKeySequence,
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

# Set up UTF-8 capable streams for emoji-friendly logging
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    # If reconfiguring the stream fails, continue with the default encoding
    pass

# Set up logging to file AND console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcpm_gui.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================================
# NEO CYBER COLOR PALETTE - Modern 2025 Design System
# ============================================================================
class NeoCyberColors:
    """Centralized color palette for the Neo Cyber design system."""

    # Primary colors
    PRIMARY = "#6366f1"      # Indigo - Main brand color
    SECONDARY = "#8b5cf6"    # Purple - Accent color
    SUCCESS = "#10b981"      # Emerald - Positive actions
    WARNING = "#f59e0b"      # Amber - Alerts
    ERROR = "#ef4444"        # Red - Errors
    INFO = "#3b82f6"         # Blue - Information

    # Backgrounds
    BG_DEEP = "#0a0a0f"      # Deepest background
    BG_CARD = "#18181b"      # Card background (Zinc-900)
    BG_ELEVATED = "#27272a"  # Elevated elements (Zinc-800)
    BG_GLASS = "rgba(24, 24, 27, 0.7)"  # Glassmorphism

    # Text colors
    TEXT_PRIMARY = "#fafafa"    # Zinc-50 - Main text
    TEXT_SECONDARY = "#a1a1aa"  # Zinc-400 - Secondary text
    TEXT_MUTED = "#71717a"      # Zinc-500 - Muted text

    # Borders
    BORDER_DEFAULT = "rgba(99, 102, 241, 0.2)"
    BORDER_HOVER = "rgba(99, 102, 241, 0.4)"
    BORDER_FOCUS = "rgba(99, 102, 241, 0.6)"

    # Syntax highlighting (modern palette)
    SYNTAX_KEYWORD = "#c792ea"     # Purple
    SYNTAX_STRING = "#c3e88d"      # Green
    SYNTAX_NUMBER = "#f78c6c"      # Orange
    SYNTAX_COMMENT = "#546e7a"     # Gray-blue
    SYNTAX_FUNCTION = "#82aaff"    # Blue
    SYNTAX_CLASS = "#ffcb6b"       # Yellow

COLORS = NeoCyberColors()

def _color(hex_color: str, alpha: int = 255) -> QColor:
    """Create a QColor from hex string with optional alpha."""
    # Handle rgba strings
    if hex_color.startswith("rgba"):
        # Extract rgba values
        parts = hex_color.replace("rgba(", "").replace(")", "").split(",")
        if len(parts) == 4:
            r, g, b = [int(x.strip()) for x in parts[:3]]
            a = int(float(parts[3].strip()) * 255)
            return QColor(r, g, b, a)

    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color


def _mix_hex(color_a: str, color_b: str, progress: float) -> str:
    """Mix two hex colors with a progress value (0.0 to 1.0)."""
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

        # Keywords - Modern purple
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(_color(COLORS.SYNTAX_KEYWORD))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        for keyword in self.KEYWORDS:
            self.highlighting_rules.append((re.compile(rf"\b{keyword}\b"), keyword_format))

        # Builtins - Modern blue
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(_color(COLORS.SYNTAX_FUNCTION))
        for builtin in self.BUILTINS:
            self.highlighting_rules.append((re.compile(rf"\b{builtin}\b"), builtin_format))

        # Decorators - Secondary accent
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(_color(COLORS.SECONDARY))
        decorator_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"@[_A-Za-z][_A-Za-z0-9.]*"), decorator_format))

        # Classes - Yellow
        class_format = QTextCharFormat()
        class_format.setForeground(_color(COLORS.SYNTAX_CLASS))
        class_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"\bclass\s+([_A-Za-z][_A-Za-z0-9]*)"), class_format))

        # Functions - Blue
        function_format = QTextCharFormat()
        function_format.setForeground(_color(COLORS.SYNTAX_FUNCTION))
        self.highlighting_rules.append((re.compile(r"\bdef\s+([_A-Za-z][_A-Za-z0-9]*)"), function_format))

        # Numbers - Orange
        number_format = QTextCharFormat()
        number_format.setForeground(_color(COLORS.SYNTAX_NUMBER))
        self.highlighting_rules.append((re.compile(r"\b0[bB][01_]+\b"), number_format))
        self.highlighting_rules.append((re.compile(r"\b0[oO][0-7_]+\b"), number_format))
        self.highlighting_rules.append((re.compile(r"\b0[xX][0-9a-fA-F_]+\b"), number_format))
        self.highlighting_rules.append((re.compile(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?j?\b"), number_format))

        # Strings - Green
        single_string_format = QTextCharFormat()
        single_string_format.setForeground(_color(COLORS.SYNTAX_STRING))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), single_string_format))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), single_string_format))

        # Comments - Muted gray-blue
        comment_format = QTextCharFormat()
        comment_format.setForeground(_color(COLORS.SYNTAX_COMMENT))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r"#[^\n]*"), comment_format))

        # TODOs - Warning color
        todo_format = QTextCharFormat()
        todo_format.setForeground(_color(COLORS.WARNING))
        todo_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"#.*\b(TODO|FIXME|NOTE)\b.*"), todo_format))

        self.multi_line_string_format = QTextCharFormat()
        self.multi_line_string_format.setForeground(_color(COLORS.SYNTAX_STRING))

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
    """Ultra-modern gradient button with smooth hover effects and glass morphism."""

    def __init__(self, text: str, gradient: Optional[tuple[str, str]] = None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.gradient = gradient or (COLORS.PRIMARY, COLORS.SECONDARY)
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._gradient_shift = 0.0

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        self.setStyleSheet("color: white; border: none; padding: 0 24px;")

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
        try:
            self._gradient_shift = (self._gradient_shift + 0.01) % 1.0
            self.update()
        except Exception as e:
            logger.error(f"Error in gradient animation: {e}")

    def paintEvent(self, event):  # noqa: D401 - Qt override
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect().adjusted(4, 4, -4, -4)

            scale = 1.0 + 0.04 * self._hover_progress - 0.02 * self._press_progress
            painter.translate(rect.center())
            painter.scale(scale, scale)
            painter.translate(-rect.center())

            gradient = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomRight()))
            shift = self._gradient_shift
            gradient.setColorAt((shift + 0.0) % 1.0, QColor(self.gradient[0]))
            gradient.setColorAt((shift + 0.5) % 1.0, QColor(self.gradient[1]))
            gradient.setColorAt((shift + 1.0) % 1.0, QColor(self.gradient[0]))

            path = QPainterPath()
            path.addRoundedRect(QRectF(rect), 14, 14)

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
        except Exception as e:
            logger.error(f"Error in AnimatedButton paintEvent: {e}")
            super().paintEvent(event)

    def hideEvent(self, event):
        """Stop animation timer when hidden (P1 FIX: GUI-3 - prevent timer leak)."""
        if hasattr(self, '_gradient_timer') and self._gradient_timer:
            self._gradient_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        """Resume animation timer when shown (P1 FIX: GUI-3)."""
        if hasattr(self, '_gradient_timer') and self._gradient_timer:
            self._gradient_timer.start(60)
        super().showEvent(event)

    def closeEvent(self, event):
        """Clean up timer on close (P1 FIX: GUI-3)."""
        if hasattr(self, '_gradient_timer') and self._gradient_timer:
            self._gradient_timer.stop()
            self._gradient_timer.deleteLater()
        super().closeEvent(event)

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
    """Modern glassmorphic card with backdrop blur effect."""

    def __init__(self, parent: Optional[QWidget] = None, blur_enabled: bool = True):
        super().__init__(parent)
        self.blur_enabled = blur_enabled
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Modern, subtler shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setOffset(0, 8)
        shadow.setBlurRadius(24)
        shadow.setColor(_color("#000000", 100))
        self.setGraphicsEffect(shadow)
        self.setContentsMargins(0, 0, 0, 0)

    def paintEvent(self, event):  # noqa: D401 - Qt override
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect().adjusted(1, 1, -1, -1)

            # Modern glass gradient
            gradient = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomRight()))
            gradient.setColorAt(0.0, _color(COLORS.BG_CARD, 200))
            gradient.setColorAt(1.0, _color(COLORS.BG_ELEVATED, 180))

            # Border with modern accent color
            painter.setPen(QPen(_color(COLORS.BORDER_DEFAULT), 1.5))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, 16, 16)

            # Inner highlight for depth
            inner_rect = rect.adjusted(1, 1, -1, -1)
            painter.setPen(QPen(_color(COLORS.PRIMARY, 30), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(inner_rect, 15, 15)
        except Exception as e:
            logger.error(f"Error in GlassCard paintEvent: {e}")
            super().paintEvent(event)


class ToastNotification(QWidget):
    """Modern toast notification with slide-in animation."""

    def __init__(self, message: str, toast_type: str = "info", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.toast_type = toast_type
        self.message = message

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Icon based on type
        icon_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        icon_label = QLabel(icon_map.get(toast_type, "ℹ️"))
        icon_label.setFont(QFont("Segoe UI Emoji", 16))
        layout.addWidget(icon_label)

        # Message
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; font-size: 13px; font-weight: 500;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)

        self.setFixedWidth(350)
        self.adjustSize()

        # Auto-dismiss timer
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.timeout.connect(self.fade_out)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.start(4000)  # 4 seconds

        # Fade in animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in_anim.start()

    def fade_out(self):
        """Fade out and close."""
        fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        fade_out_anim.setDuration(300)
        fade_out_anim.setStartValue(1.0)
        fade_out_anim.setEndValue(0.0)
        fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        fade_out_anim.finished.connect(self.close)
        fade_out_anim.start()

    def paintEvent(self, event):  # noqa: D401 - Qt override
        """Draw the toast background."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Color based on type
            color_map = {
                "success": COLORS.SUCCESS,
                "error": COLORS.ERROR,
                "warning": COLORS.WARNING,
                "info": COLORS.INFO
            }
            bg_color = color_map.get(self.toast_type, COLORS.INFO)

            rect = self.rect()

            # Background with glassmorphism
            gradient = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomLeft()))
            gradient.setColorAt(0.0, _color(bg_color, 220))
            gradient.setColorAt(1.0, _color(bg_color, 200))

            painter.setPen(QPen(_color(bg_color, 255), 2))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)

            # Inner glow
            painter.setPen(QPen(_color("#ffffff", 80), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 10, 10)
        except Exception as e:
            logger.error(f"Error in ToastNotification paintEvent: {e}")
            super().paintEvent(event)


class LoadingOverlay(QWidget):
    """Modern loading spinner overlay (P1 FIX: GUI-11)."""

    def __init__(self, message: str = "Loading...", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.message = message
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Spinning animation
        self._rotation = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_rotation)
        self._timer.start(16)  # ~60fps

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Spinner label
        self.spinner_label = QLabel("⏳")
        self.spinner_label.setFont(QFont("Segoe UI Emoji", 48))
        self.spinner_label.setStyleSheet(f"color: {COLORS.PRIMARY}; background: transparent;")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spinner_label)

        # Message label
        self.text_label = QLabel(message)
        self.text_label.setFont(QFont("Inter", 14, QFont.Weight.DemiBold))
        self.text_label.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; background: transparent;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_label)

        self.setLayout(layout)

    def _advance_rotation(self):
        """Animate the spinner rotation."""
        self._rotation = (self._rotation + 6) % 360
        self.update()

    def show_loading(self):
        """Show the loading overlay covering the parent."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        QApplication.processEvents()  # Update UI immediately

    def set_message(self, message: str):
        """Update the loading message."""
        self.message = message
        self.text_label.setText(message)
        QApplication.processEvents()

    def closeEvent(self, event):
        """Clean up timer on close."""
        if hasattr(self, '_timer') and self._timer:
            self._timer.stop()
            self._timer.deleteLater()
        super().closeEvent(event)

    def paintEvent(self, event):
        """Draw the loading overlay background."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Semi-transparent dark background
            painter.fillRect(self.rect(), _color("#000000", 180))

            # Draw rotating spinner
            painter.save()
            center = self.spinner_label.rect().center()
            global_center = self.spinner_label.mapTo(self, center)
            painter.translate(global_center)
            painter.rotate(self._rotation)

            # Draw spinning arc
            pen = QPen(QColor(COLORS.PRIMARY), 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(-20, -20, 40, 40, 0, 240 * 16)  # 240 degree arc

            painter.restore()
        except Exception as e:
            logger.debug(f"Error in LoadingOverlay paintEvent: {e}")


class AnimatedLineEdit(QLineEdit):
    """Modern line edit with smooth focus glow animation."""

    def __init__(self, placeholder: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._focus_progress = 0.0
        self.setPlaceholderText(placeholder)
        self.setFont(QFont("Inter", 11))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"color: {COLORS.TEXT_PRIMARY}; padding: 14px 18px; background: transparent; border: none;")

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
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect().adjusted(2, 2, -2, -2)

            # Modern dark background
            base_color = _color(COLORS.BG_DEEP, 240)
            painter.setBrush(base_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 12, 12)

            # Animated border with new primary color
            border_color = QColor(COLORS.PRIMARY)
            border_color.setAlphaF(0.2 + 0.5 * self._focus_progress)
            painter.setPen(QPen(border_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 12, 12)

            # Inner glow on focus
            glow_color = QColor(COLORS.SECONDARY)
            glow_color.setAlphaF(0.15 * self._focus_progress)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_color)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)

            super().paintEvent(event)
        except Exception as e:
            logger.error(f"Error in AnimatedLineEdit paintEvent: {e}")
            super().paintEvent(event)

    def get_focus_progress(self) -> float:
        return self._focus_progress

    def set_focus_progress(self, value: float) -> None:
        self._focus_progress = value
        self.update()

    focusProgress = pyqtProperty(float, fget=get_focus_progress, fset=set_focus_progress)


class ModernTabWidget(QTabWidget):
    """Ultra-modern tab widget with smooth gradients and hover effects."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setDocumentMode(True)
        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 16px;
                background: {COLORS.BG_GLASS};
                padding: 20px;
            }}
            QTabBar::tab {{
                background: {COLORS.BG_ELEVATED};
                color: {COLORS.TEXT_SECONDARY};
                padding: 16px 32px;
                margin-right: 8px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                transition: all 0.3s ease;
            }}
            QTabBar::tab:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS.PRIMARY}, stop:1 {COLORS.SECONDARY});
                color: white;
            }}
            QTabBar::tab:hover {{
                background: {COLORS.BORDER_HOVER};
                color: {COLORS.TEXT_PRIMARY};
            }}
        """)


class AnimatedStatusLabel(QLabel):
    """Modern status label with pulsing indicator and color-coded states."""

    STATUS_COLORS: Dict[str, str] = {
        "ready": COLORS.SUCCESS,
        "running": COLORS.SUCCESS,
        "warning": COLORS.WARNING,
        "error": COLORS.ERROR,
        "stopped": COLORS.SECONDARY,
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
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            center = QPointF(self.rect().left() + 16, self.rect().center().y())

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
        except Exception as e:
            logger.error(f"Error in AnimatedStatusLabel paintEvent: {e}")
            super().paintEvent(event)

    def set_status(self, status: str, message: str) -> None:
        color = QColor(self.STATUS_COLORS.get(status, "#50fa7b"))
        self._indicator_color = color
        self.setText(message)
        if status in {"running", "warning"}:
            if self._pulse_anim.state() != QAbstractAnimation.State.Running:
                self._pulse_anim.start()
        else:
            if self._pulse_anim.state() == QAbstractAnimation.State.Running:
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

        # Close button - use modern NeoCyberColors
        close_btn = QPushButton("✕ Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS.ERROR}, stop:1 #dc2626);
                color: {COLORS.TEXT_PRIMARY};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Inter', sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f87171, stop:1 {COLORS.ERROR});
                transform: translateY(-1px);
            }}
        """)
        layout.addWidget(close_btn)

        self.apply_dark_mode()

    def apply_dark_mode(self):
        """Apply modern Neo Cyber color scheme to match main GUI."""
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS.BG_DEEP},
                    stop:0.5 #0f0f14,
                    stop:1 {COLORS.BG_DEEP});
                color: {COLORS.TEXT_PRIMARY};
                font-family: 'Inter', sans-serif;
            }}
            QTextEdit {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                padding: 16px;
                font-family: 'Fira Code', 'Consolas', monospace;
                font-size: 11pt;
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border: 1.5px solid {COLORS.PRIMARY};
            }}
        """)

# --------------------------------------------------------------------------- #
# -------------------------- MAIN GUI --------------------------------------- #
# --------------------------------------------------------------------------- #
class FGDGUI(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.setWindowTitle("MCPM v6.0 – Neo Cyber AI Co‑Pilot ✨")
            self.resize(1720, 1080)
            self.setMinimumSize(1366, 900)
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
            self._log_lock = threading.Lock()  # Thread-safe file writes
            self._log_colors = {
                "error": QColor(COLORS.ERROR),
                "warning": QColor(COLORS.WARNING),
                "success": QColor(COLORS.SUCCESS),
                "default": QColor(COLORS.TEXT_PRIMARY),
            }
            self._header_phase = 0.0
            self._toast_notifications: List[ToastNotification] = []

            # Settings for session persistence
            self.settings = QSettings("MCPM", "NeoCyberGUI")
            self._load_session()

            self._fade_in_intro()

            self._build_ui()
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_logs)
            self.timer.timeout.connect(self.check_backend_health)  # HEALTH MONITORING
            self.timer.start(1000)

            # P1 FIX (GUI-15): Separate slower timer for memory explorer to reduce unnecessary tree redraws
            self.memory_timer = QTimer()
            self.memory_timer.timeout.connect(lambda: self.update_memory_explorer(force=False))
            self.memory_timer.start(5000)  # Every 5 seconds instead of every 1 second

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
        try:
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(0.0)
            self.setGraphicsEffect(effect)
            self._fade_anim = QPropertyAnimation(effect, b"opacity", self)
            self._fade_anim.setDuration(820)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            # Clean up the graphics effect after animation completes
            self._fade_anim.finished.connect(lambda: self.setGraphicsEffect(None))
            self._fade_anim.start()
        except Exception as e:
            logger.error(f"Error in fade-in animation: {e}")

    def _start_header_animation(self) -> None:
        self._header_timer = QTimer(self)
        self._header_timer.timeout.connect(self._tick_header_gradient)
        self._header_timer.start(90)

    def _tick_header_gradient(self) -> None:
        try:
            self._header_phase = (self._header_phase + 0.015) % 1.0
            wave = (math.sin(self._header_phase * 2 * math.pi) + 1) / 2
            color_a = _mix_hex(COLORS.PRIMARY, COLORS.SECONDARY, wave)
            color_b = _mix_hex(COLORS.SECONDARY, COLORS.INFO, 1 - wave * 0.5)
            animated_color = _mix_hex(color_a, color_b, 0.5)
            if hasattr(self, "header") and hasattr(self, "_header_style_template"):
                self.header.setStyleSheet(self._header_style_template.format(color=animated_color))
        except Exception as e:
            logger.error(f"Error in header gradient animation: {e}")

    def _load_session(self):
        """Load saved session settings."""
        try:
            last_dir = self.settings.value("last_directory", "")
            last_provider = self.settings.value("last_provider", "grok")
            self._last_directory = last_dir
            self._last_provider = last_provider
        except Exception as e:
            logger.warning(f"Could not load session: {e}")
            self._last_directory = ""
            self._last_provider = "grok"

    def _save_session(self):
        """Save session settings."""
        try:
            if hasattr(self, 'path_edit'):
                self.settings.setValue("last_directory", self.path_edit.text())
            if hasattr(self, 'provider'):
                self.settings.setValue("last_provider", self.provider.currentText())
        except Exception as e:
            logger.warning(f"Could not save session: {e}")

    def show_toast(self, message: str, toast_type: str = "info"):
        """Show a toast notification (P1 FIX: GUI-2 - proper repositioning)."""
        try:
            toast = ToastNotification(message, toast_type, self)
            self._toast_notifications.append(toast)
            self._reposition_toasts()  # Reposition all toasts
            toast.show()

            # Auto-remove after 4 seconds and reposition remaining
            def remove_toast():
                if toast in self._toast_notifications:
                    self._toast_notifications.remove(toast)
                    toast.close()
                    self._reposition_toasts()  # Reposition remaining toasts

            QTimer.singleShot(4000, remove_toast)
        except Exception as e:
            logger.error(f"Error showing toast: {e}")

    def _reposition_toasts(self):
        """Reposition all visible toasts (P1 FIX: GUI-2)."""
        try:
            y_offset = self.height() - 20
            for toast in reversed(self._toast_notifications):
                if toast and not toast.isHidden():
                    y_offset -= toast.height()
                    x = self.width() - toast.width() - 20
                    global_pos = self.mapToGlobal(QPoint(x, y_offset))
                    toast.move(global_pos)
                    y_offset -= 10  # Gap between toasts
        except Exception as e:
            logger.debug(f"Error repositioning toasts: {e}")

    def _add_header(self):
        """Add the ultra-modern gradient header banner."""
        self.header = QLabel("MCPM v6.0 – Neo Cyber AI Co‑Pilot ✨")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header.setMinimumHeight(90)

        header_font = self.header.font()
        header_font.setPointSize(42)
        header_font.setWeight(QFont.Weight.Black)
        header_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
        header_font.setFamily("Inter")
        self.header.setFont(header_font)
        self.header.setContentsMargins(0, 0, 0, 16)

        self._header_style_template = """
            color: {color};
        """
        initial_color = _mix_hex(COLORS.PRIMARY, COLORS.SECONDARY, 0.5)
        self.header.setStyleSheet(self._header_style_template.format(color=initial_color))
        self.main_layout.addWidget(self.header)

        subtitle = QLabel("Ultra-Modern Mission Control • Real-Time Intelligence • Seamless Integration")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = subtitle.font()
        subtitle_font.setPointSize(15)
        subtitle_font.setFamily("Inter")
        subtitle.setFont(subtitle_font)
        subtitle.setContentsMargins(0, 0, 0, 20)
        subtitle.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY};")
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

        title = QLabel("⚡ Control Center")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS.TEXT_PRIMARY}; font-family: 'Inter';")
        layout.addWidget(title)

        dir_group = QVBoxLayout()
        dir_label = QLabel("📂 Project Directory")
        dir_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        dir_group.addWidget(dir_label)

        dir_row = QHBoxLayout()
        self.path_edit = AnimatedLineEdit("Select your project workspace…")
        # Restore last directory if available
        if hasattr(self, '_last_directory') and self._last_directory:
            self.path_edit.setText(self._last_directory)
        browse = AnimatedButton("Browse", gradient=(COLORS.SECONDARY, COLORS.INFO))
        browse.clicked.connect(self.browse)
        dir_row.addWidget(self.path_edit)
        dir_row.addWidget(browse)
        dir_group.addLayout(dir_row)
        layout.addLayout(dir_group)

        provider_group = QVBoxLayout()
        provider_label = QLabel("🤖 Default LLM Provider")
        provider_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        provider_group.addWidget(provider_label)

        provider_row = QHBoxLayout()
        self.provider = QComboBox()
        self.provider.addItems(["grok", "openai", "claude", "ollama"])
        self.provider.setCurrentText(self._last_provider if hasattr(self, '_last_provider') else "grok")
        self.provider.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS.BG_DEEP};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                padding: 14px 18px;
                font-size: 13px;
            }}
            QComboBox QAbstractItemView {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
                selection-background-color: {COLORS.PRIMARY};
                border-radius: 10px;
                padding: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)

        self.start_btn = AnimatedButton("▶ Start Server", gradient=(COLORS.SUCCESS, "#16c784"))
        self.start_btn.clicked.connect(self.toggle_server)

        provider_row.addWidget(self.provider)
        provider_row.addWidget(self.start_btn)
        provider_group.addLayout(provider_row)
        layout.addLayout(provider_group)

        self.connection_status = AnimatedStatusLabel("🟢 Ready to connect")
        layout.addWidget(self.connection_status)

        tips = QLabel(
            "💡 Pro Tips:\n"
            "• Press Ctrl+K for quick commands\n"
            "• Memory Explorer tracks project context\n"
            "• Live logs update automatically"
        )
        tips.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; font-size: 12px; line-height: 1.6; font-family: 'Inter';")
        layout.addWidget(tips)
        layout.addStretch()

        return card

    def _add_status_bar(self) -> None:
        bar = GlassCard()
        bar_layout = QHBoxLayout()
        bar_layout.setContentsMargins(24, 12, 24, 12)
        bar_layout.setSpacing(18)
        bar.setLayout(bar_layout)

        self.memory_usage_label = QLabel("💾 Memory file: —")
        self.memory_usage_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 12px; font-family: 'Inter';")

        self.log_summary_label = QLabel("📊 Logs idle")
        self.log_summary_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 12px; font-family: 'Inter';")

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
        label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS.TEXT_PRIMARY}; font-family: 'Inter';")
        pop_out_btn = AnimatedButton("🔍 Pop Out Preview", gradient=(COLORS.PRIMARY, COLORS.SECONDARY))
        pop_out_btn.setMinimumWidth(200)
        pop_out_btn.clicked.connect(self.pop_out_preview)
        header.addWidget(label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        split = QSplitter()
        split.setOrientation(Qt.Orientation.Horizontal)
        split.setStyleSheet(f"QSplitter::handle {{ background: {COLORS.BORDER_HOVER}; width: 3px; border-radius: 2px; }}")

        tree_container = QWidget()
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(12)
        tree_container.setLayout(tree_layout)

        tree_caption = QLabel("📂 Structure")
        tree_caption.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        tree_layout.addWidget(tree_caption)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Files")
        self.tree.itemClicked.connect(self.on_file_click)
        self.tree.itemExpanded.connect(self.on_tree_item_expanded)  # P1 FIX: GUI-16 lazy loading
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                font-size: 13px;
                font-family: 'Inter';
                padding: 12px;
            }}
            QTreeWidget::item {{ padding: 8px; }}
            QTreeWidget::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.PRIMARY}, stop:1 {COLORS.SECONDARY});
                color: white;
                border-radius: 8px;
            }}
            QTreeWidget::item:hover {{
                background: {COLORS.BG_ELEVATED};
                border-radius: 8px;
            }}
        """)
        tree_layout.addWidget(self.tree)

        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(12)
        preview_container.setLayout(preview_layout)

        preview_header = QLabel("📄 Code Preview")
        preview_header.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        preview_layout.addWidget(preview_header)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Fira Code", 11))
        self.preview.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS.BG_DEEP};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                padding: 16px;
                font-size: 11.5pt;
                line-height: 1.6;
                font-family: 'Fira Code', 'Consolas', monospace;
            }}
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
        diff_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS.TEXT_PRIMARY}; font-family: 'Inter';")
        pop_out_btn = AnimatedButton("🪟 Open in Window", gradient=(COLORS.PRIMARY, COLORS.SECONDARY))
        pop_out_btn.clicked.connect(self.pop_out_diff)
        header.addWidget(diff_label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Fira Code", 12))
        self.diff_view.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                padding: 20px;
                font-size: 12pt;
                line-height: 1.7;
                font-family: 'Fira Code', 'Consolas', monospace;
            }}
        """)
        layout.addWidget(self.diff_view)

        btns = QHBoxLayout()
        btns.setSpacing(16)
        self.approve_btn = AnimatedButton("✅ Approve Changes", gradient=(COLORS.SUCCESS, "#16c784"))
        self.approve_btn.setMinimumHeight(56)
        self.approve_btn.clicked.connect(self.approve_edit)

        self.reject_btn = AnimatedButton("❌ Reject Changes", gradient=(COLORS.ERROR, "#f87171"))
        self.reject_btn.setMinimumHeight(56)
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
            self.approve_btn.gradient = ("#16c784", "#34d399")
            self.reject_btn.gradient = ("#f87171", "#fca5a5")
        else:
            self.approve_btn.gradient = (COLORS.SUCCESS, "#16c784")
            self.reject_btn.gradient = (COLORS.ERROR, "#f87171")
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
        log_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS.TEXT_PRIMARY}; font-family: 'Inter';")
        pop_out_btn = AnimatedButton("🪟 Open in Window", gradient=(COLORS.PRIMARY, COLORS.SECONDARY))
        pop_out_btn.clicked.connect(self.pop_out_logs)
        header.addWidget(log_label)
        header.addStretch()
        header.addWidget(pop_out_btn)
        layout.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(12)
        level_label = QLabel("🎚️ Level")
        level_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        self.level = QComboBox()
        self.level.addItems(["All", "INFO", "WARNING", "ERROR"])
        self.level.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS.BG_DEEP};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QComboBox QAbstractItemView {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
                selection-background-color: {COLORS.PRIMARY};
                border-radius: 8px;
                padding: 2px;
            }}
        """)

        search_label = QLabel("🔍 Search")
        search_label.setStyleSheet(f"color: {COLORS.TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        self.search = AnimatedLineEdit("Search logs…")
        self.search.textChanged.connect(lambda: self.update_logs())
        self.level.currentIndexChanged.connect(lambda: self.update_logs())

        clear = AnimatedButton("Clear", gradient=(COLORS.SECONDARY, COLORS.INFO))
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
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS.BG_DEEP};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                padding: 18px;
                font-size: 11.5pt;
                line-height: 1.6;
                font-family: 'Fira Code', 'Consolas', monospace;
            }}
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
        label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS.TEXT_PRIMARY}; font-family: 'Inter';")
        refresh = AnimatedButton("🔄 Refresh", gradient=(COLORS.SUCCESS, "#16c784"))
        refresh.setMinimumWidth(160)
        refresh.clicked.connect(lambda: self.update_memory_explorer(force=True))
        header.addWidget(label)
        header.addStretch()
        header.addWidget(refresh)
        layout.addLayout(header)

        description = QLabel("Visualize what the MCP backend remembers about your project")
        description.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(description)

        self.memory_tree = QTreeWidget()
        self.memory_tree.setColumnCount(2)
        self.memory_tree.setHeaderLabels(["Key", "Value"])
        self.memory_tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                padding: 12px;
                font-size: 13px;
                font-family: 'Inter';
            }}
            QTreeWidget::item {{
                padding: 8px;
            }}
            QTreeWidget::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.SECONDARY}, stop:1 {COLORS.PRIMARY});
                color: white;
                border-radius: 6px;
            }}
            QTreeWidget::item:hover {{
                background: {COLORS.BG_ELEVATED};
            }}
        """)
        layout.addWidget(self.memory_tree)

        self.memory_info = QLabel("No memory file detected yet")
        self.memory_info.setStyleSheet(f"color: {COLORS.TEXT_MUTED}; font-size: 12px;")
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
        backup_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS.TEXT_PRIMARY}; font-family: 'Inter';")
        layout.addWidget(backup_label)

        self.backup_list = QListWidget()
        self.backup_list.setStyleSheet(f"""
            QListWidget {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
                border: 1.5px solid {COLORS.BORDER_DEFAULT};
                border-radius: 12px;
                padding: 14px;
                font-size: 13px;
                font-family: 'Inter';
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 8px;
            }}
            QListWidget::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.PRIMARY}, stop:1 {COLORS.SECONDARY});
                color: white;
            }}
            QListWidget::item:hover {{
                background: {COLORS.BG_ELEVATED};
            }}
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

    def _add_tree_items(self, parent, path, lazy=True):
        """Add tree items with optional lazy loading (P1 FIX: GUI-16)."""
        try:
            for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                if p.name.startswith('.') or p.name in ['node_modules', '__pycache__', '.git', '__MACOSX']:
                    continue
                item = QTreeWidgetItem([p.name])
                item.setData(0, Qt.ItemDataRole.UserRole, str(p))
                parent.addChild(item)

                if p.is_dir():
                    if lazy:
                        # Add placeholder for lazy loading
                        placeholder = QTreeWidgetItem(["..."])
                        item.addChild(placeholder)
                        # Store path for lazy loading
                        item.setData(0, Qt.ItemDataRole.UserRole + 1, str(p))
                    else:
                        # Load immediately (non-lazy)
                        self._add_tree_items(item, p, lazy=True)
        except Exception as e:
            logger.warning(f"Error adding tree items for {path}: {e}")

    def on_tree_item_expanded(self, item):
        """Load children when item expanded - lazy loading (P1 FIX: GUI-16)."""
        try:
            # Check if this item has placeholder children
            if item.childCount() == 1 and item.child(0).text(0) == "...":
                # Remove placeholder
                item.removeChild(item.child(0))

                # Load actual children
                path_str = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if path_str:
                    path = Path(path_str)
                    if path.exists() and path.is_dir():
                        self._add_tree_items(item, path, lazy=True)
        except Exception as e:
            logger.warning(f"Error expanding tree item: {e}")

    def on_file_click(self, item, column):
        """Handle file click with loading indicator (P1 FIX: GUI-11)."""
        try:
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            if file_path and Path(file_path).is_file():
                path = Path(file_path)
                file_size = path.stat().st_size

                if file_size > 500_000:
                    self.preview.setPlainText(f"File too large to preview: {file_size / 1024:.1f} KB")
                    return

                # Show loading indicator for files > 100KB
                loader = None
                if file_size > 100_000:
                    loader = LoadingOverlay(f"Loading {path.name}...", self)
                    loader.show_loading()

                try:
                    content = path.read_text(encoding='utf-8')
                    self.preview.setPlainText(content)
                except UnicodeDecodeError:
                    self.preview.setPlainText("[Binary file - cannot preview]")
                finally:
                    if loader:
                        loader.close()
        except Exception as e:
            logger.error(f"Error previewing file: {e}")
            self.preview.setPlainText(f"Error: {str(e)}")

    def _read_subprocess_stdout(self):
        """Background thread to read subprocess stdout and write to log file."""
        try:
            # Use readline() instead of iteration to avoid blocking indefinitely
            while self.process and self.process.poll() is None:
                try:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace')
                    if self.log_file:
                        with self._log_lock:  # Thread-safe file writes
                            with open(self.log_file, 'a') as f:
                                f.write(decoded)
                                f.flush()
                except Exception as e:
                    logger.error(f"Error writing stdout to log: {e}")
                    break
        except Exception as e:
            logger.debug(f"Stdout reader stopped: {e}")

    def _read_subprocess_stderr(self):
        """Background thread to read subprocess stderr and write to log file."""
        try:
            # Use readline() instead of iteration to avoid blocking indefinitely
            while self.process and self.process.poll() is None:
                try:
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace')
                    if self.log_file:
                        with self._log_lock:  # Thread-safe file writes
                            with open(self.log_file, 'a') as f:
                                f.write(decoded)
                                f.flush()
                except Exception as e:
                    logger.error(f"Error writing stderr to log: {e}")
                    break
        except Exception as e:
            logger.debug(f"Stderr reader stopped: {e}")

    def toggle_server(self):
        if self.process and self.process.poll() is None:
            logger.info("Stopping MCP backend process...")

            # Store reference before cleanup to avoid race with daemon threads
            process_to_stop = self.process
            process_to_stop.terminate()

            try:
                # Wait up to 5 seconds for clean shutdown
                process_to_stop.wait(timeout=5)
                logger.info("Process terminated cleanly")
            except subprocess.TimeoutExpired:
                logger.warning("Process didn't stop in 5s, forcing kill...")
                process_to_stop.kill()
                try:
                    process_to_stop.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.error("Process refused to die after kill!")

            # Now safe to set to None (daemon threads will exit on pipe close)
            self.process = None

            self.connection_status.set_status("stopped", "🔴 Server stopped")
            self.start_btn.setText("▶ Start Server")
            self._highlight_decision_buttons(False)
            if hasattr(self, "log_summary_label"):
                self.log_summary_label.setText("Server stopped")
        else:
            self.start_server()

    def start_server(self):
        """Start the backend server with loading indicator (P1 FIX: GUI-11)."""
        dir_path = self.path_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            self.connection_status.set_status("error", "🔴 Invalid project directory")
            return

        # Show loading indicator while starting server
        loader = LoadingOverlay("Starting backend server...", self)
        loader.show_loading()

        try:
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
                        "grok": {"model": "grok-3", "base_url": "https://api.x.ai/v1"},
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
                    stdin=subprocess.PIPE,
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
        finally:
            # Close loading indicator
            loader.close()

    def update_logs(self):
        if not self.log_file or not self.log_file.exists():
            return
        try:
            # Initialize tracking variables on first run
            if not hasattr(self, '_log_last_pos'):
                self._log_last_pos = 0
                self._log_last_level = "All"
                self._log_last_search = ""

            level = self.level.currentText()
            search = self.search.text().lower()

            # Check if filters changed - if so, we need to rebuild
            filters_changed = (level != self._log_last_level or search != self._log_last_search)

            if filters_changed:
                # Filters changed - do a full rebuild
                self._log_last_level = level
                self._log_last_search = search
                self._log_last_pos = 0
                self.log_view.clear()

                # Read entire file and apply filters
                lines = self.log_file.read_text().splitlines()
                for line in lines:
                    if level != "All" and level not in line:
                        continue
                    if search and search not in line.lower():
                        continue

                    cursor = self.log_view.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.log_view.setTextCursor(cursor)
                    self.log_view.setTextColor(self._log_color_for_line(line))
                    self.log_view.insertPlainText(line + "\n")

                self._log_last_pos = self.log_file.stat().st_size
            else:
                # Filters unchanged - only read new lines (PERFORMANCE FIX)
                file_size = self.log_file.stat().st_size

                # Only process if file has grown
                if file_size > self._log_last_pos:
                    with open(self.log_file, 'r') as f:
                        f.seek(self._log_last_pos)
                        new_lines = f.readlines()
                        self._log_last_pos = f.tell()

                    # Append only new filtered lines
                    for line in new_lines:
                        line = line.rstrip('\n')
                        if level != "All" and level not in line:
                            continue
                        if search and search not in line.lower():
                            continue

                        cursor = self.log_view.textCursor()
                        cursor.movePosition(QTextCursor.MoveOperation.End)
                        self.log_view.setTextCursor(cursor)
                        self.log_view.setTextColor(self._log_color_for_line(line))
                        self.log_view.insertPlainText(line + "\n")

            if hasattr(self, "log_summary_label"):
                total_lines = self.log_view.document().lineCount()
                self.log_summary_label.setText(f"Showing {total_lines} log lines")

            self._update_memory_usage()
            # P1 FIX (GUI-15): update_memory_explorer now called from separate slower timer
            # Removed from here to reduce unnecessary tree redraws

            # Check for pending edits
            self.check_pending_edits()
        except Exception as e:
            logger.debug(f"Error updating logs: {e}")

    def check_backend_health(self):
        """Monitor backend process health and detect crashes (P0 FIX: GUI-18)."""
        if not self.process:
            return

        try:
            # Check if process is still running
            poll_result = self.process.poll()

            if poll_result is not None:
                # Process has terminated!
                logger.error(f"Backend process crashed with exit code: {poll_result}")

                # Update UI to reflect crashed state
                if hasattr(self, 'connection_status'):
                    self.connection_status.set_status("error", f"🔴 Crashed (exit code {poll_result})")

                if hasattr(self, 'start_btn'):
                    self.start_btn.setText("▶ Start Server")

                # Show toast notification
                self.show_toast(
                    f"Backend process crashed (exit code {poll_result}). Check logs for details.",
                    "error"
                )

                # Clean up
                self.process = None

        except Exception as e:
            logger.debug(f"Error checking backend health: {e}")

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

                project_dir = Path(dir_path).expanduser()
                if not project_dir.exists():
                    QMessageBox.warning(self, "Error", f"Directory does not exist: {project_dir}")
                    return

                if not project_dir.is_dir():
                    QMessageBox.warning(self, "Error", f"Path is not a directory: {project_dir}")
                    return

                # Write approval decision
                approval_file = project_dir / ".fgd_approval.json"
                approval_data = {
                    "approved": True,
                    "filepath": self.pending_edit['filepath'],
                    "old_text": self.pending_edit['old_text'],
                    "new_text": self.pending_edit['new_text'],
                    "timestamp": datetime.now().isoformat()
                }
                try:
                    approval_file.write_text(json.dumps(approval_data, indent=2))
                except OSError as exc:
                    QMessageBox.warning(self, "Error", f"Failed to write approval file: {exc}")
                    return

                # Delete pending edit file to signal completion
                pending_file = project_dir / ".fgd_pending_edit.json"
                if pending_file.exists():
                    try:
                        pending_file.unlink()
                    except OSError as exc:
                        logger.warning(f"Failed to remove pending edit file: {exc}")

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
        """Apply the ultra-modern Neo Cyber dark theme."""
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS.BG_DEEP}, stop:0.5 #0f0f14, stop:1 {COLORS.BG_DEEP});
                color: {COLORS.TEXT_PRIMARY};
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 13px;
            }}
            QMessageBox {{
                background: {COLORS.BG_CARD};
                color: {COLORS.TEXT_PRIMARY};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 12px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS.PRIMARY}, stop:1 {COLORS.SECONDARY});
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS.INFO}, stop:1 {COLORS.SECONDARY});
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 12px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.PRIMARY}, stop:1 {COLORS.SECONDARY});
                border-radius: 6px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.INFO}, stop:1 {COLORS.SECONDARY});
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

    def hideEvent(self, event):
        """Stop timers when window is hidden (P1 FIX: GUI-4 - prevent CPU waste)."""
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        if hasattr(self, '_header_timer') and self._header_timer:
            self._header_timer.stop()
        if hasattr(self, 'memory_timer') and self.memory_timer:
            self.memory_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        """Resume timers when window is shown (P1 FIX: GUI-4)."""
        super().showEvent(event)
        if hasattr(self, 'timer') and self.timer:
            self.timer.start(1000)
        if hasattr(self, '_header_timer') and self._header_timer:
            self._header_timer.start(90)
        if hasattr(self, 'memory_timer') and self.memory_timer:
            self.memory_timer.start(5000)

    def closeEvent(self, event):
        """Clean shutdown of all resources."""
        logger.info("Application closing, cleaning up...")

        # Save session settings
        self._save_session()

        # Stop timers (P1 FIX: GUI-4 - proper cleanup)
        if hasattr(self, "timer") and self.timer:
            self.timer.stop()
            self.timer.deleteLater()
        if hasattr(self, "_header_timer") and self._header_timer:
            self._header_timer.stop()
            self._header_timer.deleteLater()
        # P1 FIX (GUI-15): Stop memory timer
        if hasattr(self, "memory_timer") and self.memory_timer:
            self.memory_timer.stop()
            self.memory_timer.deleteLater()

        # Stop subprocess with proper cleanup
        if self.process:
            logger.info("Terminating MCP backend...")
            self.process.terminate()

            try:
                self.process.wait(timeout=5)
                logger.info("Backend stopped cleanly")
            except subprocess.TimeoutExpired:
                logger.warning("Backend didn't stop in 5s, forcing kill...")
                self.process.kill()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.error("Backend refused to die!")
            except Exception as e:
                logger.error(f"Error stopping backend: {e}")

        # Close pop-out windows
        for window in self.pop_out_windows:
            try:
                window.close()
            except Exception as e:
                logger.debug(f"Error closing pop-out window: {e}")

        event.accept()
        logger.info("Application closed")

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


def _qt_exception_hook(exc_type, exc_value, exc_traceback):
    """Global exception hook for Qt event loop crashes."""
    logger.critical("=" * 60)
    logger.critical("UNHANDLED EXCEPTION IN QT EVENT LOOP")
    logger.critical("=" * 60)
    logger.critical(f"Type: {exc_type.__name__}")
    logger.critical(f"Value: {exc_value}")
    logger.critical("Traceback:")
    logger.critical(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    logger.critical("=" * 60)

    # Call the default exception hook
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def _run_app() -> tuple[int, Optional[QApplication]]:
    """Entry point wrapper that bootstraps the Qt application."""
    # Install global exception hook
    sys.excepthook = _qt_exception_hook

    logger.info("Starting MCPM GUI...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Qt application arguments: {sys.argv}")

    app = QApplication(sys.argv)
    logger.info("QApplication created successfully")

    # Install Qt message handler to suppress non-critical warnings
    def qt_message_handler(msg_type, context, message):
        """Suppress Qt warnings about unknown properties and other non-critical messages."""
        if any(ignore in message for ignore in ['Unknown property', 'transition']):
            return  # Silently ignore these warnings
        # For other messages, log normally
        if msg_type >= QtMsgType.QtWarningMsg:
            logger.warning(f"Qt {msg_type}: {message}")

    from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
    qInstallMessageHandler(qt_message_handler)

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
        logger.error(f"Exception during GUI initialization or event loop: {e}")
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
