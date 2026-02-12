#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面时钟小组件
- 显示秒针时数字完整，无任何裁剪（边距0.8倍字体，最小40px）
- 切换渐变主题
- 日期/星期字体大小为时间0.45倍
- 设置读写类型安全，无残留，单实例强制
- Python 3.13 + PyQt6 + Windows 11 测试通过
- 作者：轩轩
"""

import sys
import os
import atexit
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QSlider,
    QPushButton, QColorDialog, QFontDialog, QCheckBox, QComboBox,
    QSpinBox, QGroupBox, QMessageBox
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QLinearGradient, QFontMetrics,
    QAction, QIcon, QPixmap, QBrush, QPen, QFontDatabase, QGradient
)
from PyQt6.QtCore import (
    Qt, QTimer, QTime, QDate, QRect, QPoint,
    QSharedMemory, pyqtSignal, QObject, QCoreApplication, QSettings
)

# ---------------------------- 常量定义 ----------------------------
APP_NAME = "MyDesktopClock"
APP_KEY = "MyDesktopClockApp"
ORG_NAME = "MyOrg"
DEFAULT_FONT_FAMILY = "Arial"
DEFAULT_BASE_SIZE = 80
DEFAULT_FONT_OPACITY = 255
DEFAULT_COLOR = QColor(255, 255, 255)  # 白色
DEFAULT_THEME = "单色"
DEFAULT_SHOW_DATE = True
DEFAULT_SHOW_WEEK = True
DEFAULT_SHOW_SECONDS = False
DEFAULT_COUNTDOWN_MINUTES = 25
DEFAULT_STARTUP_WITH_OS = False
DEFAULT_FIXED_POS = False
DEFAULT_STAY_ON_TOP = False


# ---------------------------- 主题管理器 ----------------------------
class ThemeManager:
    """管理渐变主题，返回颜色停止点列表"""
    
    THEMES = {
        "单色": [(0.0, QColor(255, 255, 255))],
        "彩虹": [
            (0.0, QColor(255, 0, 0)),      # 红
            (0.16, QColor(255, 165, 0)),   # 橙
            (0.33, QColor(255, 255, 0)),   # 黄
            (0.5, QColor(0, 255, 0)),      # 绿
            (0.66, QColor(0, 255, 255)),   # 青
            (0.83, QColor(0, 0, 255)),     # 蓝
            (1.0, QColor(128, 0, 128)),    # 紫
        ],
        "落日": [
            (0.0, QColor(255, 69, 0)),     # 橙红
            (0.33, QColor(255, 140, 0)),   # 橙
            (0.66, QColor(255, 215, 0)),   # 金黄
            (1.0, QColor(255, 255, 0)),    # 黄
        ],
        "黑白": [
            (0.0, QColor(255, 255, 255)),
            (0.33, QColor(200, 200, 200)),
            (0.66, QColor(100, 100, 100)),
            (1.0, QColor(0, 0, 0)),
        ],
        "紫色心情": [
            (0.0, QColor(230, 230, 250)),  # 薰衣草
            (0.33, QColor(147, 112, 219)), # 紫罗兰
            (0.66, QColor(138, 43, 226)),  # 蓝紫
            (1.0, QColor(186, 85, 211)),   # 中紫
        ],
        "红色风暴": [
            (0.0, QColor(255, 0, 0)),
            (0.33, QColor(200, 0, 0)),
            (0.66, QColor(150, 0, 0)),
            (1.0, QColor(100, 0, 0)),
        ],
        "海洋蓝": [
            (0.0, QColor(0, 191, 255)),
            (0.33, QColor(30, 144, 255)),
            (0.66, QColor(70, 130, 180)),
            (1.0, QColor(25, 25, 112)),
        ],
        "森林绿": [
            (0.0, QColor(173, 255, 47)),
            (0.33, QColor(124, 252, 0)),
            (0.66, QColor(50, 205, 50)),
            (1.0, QColor(34, 139, 34)),
        ],
        "极光": [
            (0.0, QColor(0, 255, 127)),
            (0.33, QColor(0, 255, 255)),
            (0.66, QColor(0, 191, 255)),
            (1.0, QColor(138, 43, 226)),
        ],
        "糖果": [
            (0.0, QColor(255, 182, 193)),
            (0.33, QColor(255, 192, 203)),
            (0.66, QColor(255, 218, 185)),
            (1.0, QColor(255, 228, 225)),
        ],
        "烈焰": [
            (0.0, QColor(255, 99, 71)),
            (0.33, QColor(255, 69, 0)),
            (0.66, QColor(255, 140, 0)),
            (1.0, QColor(255, 215, 0)),
        ],
    }
    
    @classmethod
    def get_gradient_stops(cls, theme_name):
        return cls.THEMES.get(theme_name, cls.THEMES["单色"])


# ---------------------------- 计时管理器 ----------------------------
class TimerManager(QObject):
    """管理倒计时和秒表，发射更新信号供主窗口显示"""
    
    countdown_updated = pyqtSignal(int)
    stopwatch_updated = pyqtSignal(int)
    countdown_finished = pyqtSignal()
    countdown_state_changed = pyqtSignal(bool)
    stopwatch_state_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.countdown_seconds = DEFAULT_COUNTDOWN_MINUTES * 60
        self.stopwatch_seconds = 0
        self.countdown_running = False
        self.stopwatch_running = False
        
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._on_countdown_tick)
        self.countdown_timer.setInterval(1000)
        
        self.stopwatch_timer = QTimer()
        self.stopwatch_timer.timeout.connect(self._on_stopwatch_tick)
        self.stopwatch_timer.setInterval(1000)
    
    def start_countdown(self, minutes=None):
        if minutes is not None:
            self.countdown_seconds = minutes * 60
        if not self.countdown_running and self.countdown_seconds > 0:
            self.countdown_running = True
            self.countdown_timer.start()
            self.countdown_state_changed.emit(True)
    
    def pause_countdown(self):
        self.countdown_running = False
        self.countdown_timer.stop()
        self.countdown_state_changed.emit(False)
    
    def reset_countdown(self, minutes=None):
        self.pause_countdown()
        self.countdown_seconds = (minutes or DEFAULT_COUNTDOWN_MINUTES) * 60
        self.countdown_updated.emit(self.countdown_seconds)
    
    def set_countdown_minutes(self, minutes):
        self.countdown_seconds = minutes * 60
        if not self.countdown_running:
            self.countdown_updated.emit(self.countdown_seconds)
    
    def start_stopwatch(self):
        if not self.stopwatch_running:
            self.stopwatch_running = True
            self.stopwatch_timer.start()
            self.stopwatch_state_changed.emit(True)
    
    def pause_stopwatch(self):
        self.stopwatch_running = False
        self.stopwatch_timer.stop()
        self.stopwatch_state_changed.emit(False)
    
    def reset_stopwatch(self):
        self.pause_stopwatch()
        self.stopwatch_seconds = 0
        self.stopwatch_updated.emit(0)
    
    def _on_countdown_tick(self):
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
            self.countdown_updated.emit(self.countdown_seconds)
            if self.countdown_seconds == 0:
                self.countdown_finished.emit()
                self.pause_countdown()
        else:
            self.pause_countdown()
    
    def _on_stopwatch_tick(self):
        self.stopwatch_seconds += 1
        self.stopwatch_updated.emit(self.stopwatch_seconds)
    
    def get_countdown_time_str(self):
        if self.countdown_seconds < 0:
            self.countdown_seconds = 0
        m = self.countdown_seconds // 60
        s = self.countdown_seconds % 60
        return f"{m:02d}:{s:02d}"
    
    def get_stopwatch_time_str(self):
        h = self.stopwatch_seconds // 3600
        m = (self.stopwatch_seconds % 3600) // 60
        s = self.stopwatch_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------- 时钟主窗口（计时器独占模式） ----------------------------
class ClockWidget(QWidget):
    """透明背景时钟窗口，支持渐变流动、拖拽、计时独占显示"""
    
    appearance_changed = pyqtSignal()
    
    def __init__(self, settings, timer_mgr):
        super().__init__()
        self.settings = settings
        self.timer_mgr = timer_mgr
        
        # 窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            (Qt.WindowType.WindowStaysOnTopHint if self.settings.get("stay_on_top", DEFAULT_STAY_ON_TOP) else Qt.WindowType.Widget)
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 字体/颜色/透明度/主题
        self.font_family = self.settings.get("font_family", DEFAULT_FONT_FAMILY)
        self.base_font_size = self.settings.get("base_size", DEFAULT_BASE_SIZE)
        self.font_opacity = self.settings.get("font_opacity", DEFAULT_FONT_OPACITY)
        self.custom_color = self.settings.get("custom_color", DEFAULT_COLOR)
        self.theme_name = self.settings.get("theme", DEFAULT_THEME)
        
        # 显示选项
        self.show_date = self.settings.get("show_date", DEFAULT_SHOW_DATE)
        self.show_week = self.settings.get("show_week", DEFAULT_SHOW_WEEK)
        self.show_seconds = self.settings.get("show_seconds", DEFAULT_SHOW_SECONDS)
        
        # 位置固定
        self.is_fixed = self.settings.get("fixed_pos", DEFAULT_FIXED_POS)
        self.drag_position = None
        
        # 渐变流动
        self.gradient_offset = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_gradient)
        self.animation_timer.setInterval(50)
        if self.theme_name != "单色":
            self.animation_timer.start()
        
        # 时钟更新定时器
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update)
        self.clock_timer.setInterval(1000 if not self.show_seconds else 100)
        self.clock_timer.start()
        
        # 缓存
        self._cached_fonts = {}
        self._cached_metrics = {}
        self._cached_gradient = None
        self._cached_size = None
        
        # 初始化位置
        self._load_position()
        
        # 连接计时器信号
        self.timer_mgr.countdown_updated.connect(self._on_timer_changed)
        self.timer_mgr.stopwatch_updated.connect(self._on_timer_changed)
        self.timer_mgr.countdown_finished.connect(self._on_timer_changed)
        self.timer_mgr.countdown_state_changed.connect(self._on_timer_changed)
        self.timer_mgr.stopwatch_state_changed.connect(self._on_timer_changed)
        
        self.update_geometry()
    
    # -------------------- 计时器独占模式判断 --------------------
    def _is_timer_active(self):
        countdown_active = (
            self.timer_mgr.countdown_running or 
            self.timer_mgr.countdown_seconds != DEFAULT_COUNTDOWN_MINUTES * 60
        )
        stopwatch_active = (
            self.timer_mgr.stopwatch_running or 
            self.timer_mgr.stopwatch_seconds > 0
        )
        return countdown_active or stopwatch_active
    
    def _on_timer_changed(self, *args):
        self.update_geometry()
        self.update()
    
    # -------------------- 几何尺寸自适应 --------------------
    def update_geometry(self):
        if self._is_timer_active():
            fm_timer = self._get_font_metrics(self.base_font_size)
            timer_text = self._get_timer_text()
            width = fm_timer.horizontalAdvance(timer_text) + 20
            height = fm_timer.height() + 8
            self.setFixedSize(int(width), int(height))
        else:
            fm_time = self._get_font_metrics(self.base_font_size)
            # 日期/星期字体大小为时间的 0.45 倍（更精致）
            fm_small = self._get_font_metrics(int(self.base_font_size * 0.45))
            
            # ★★★ 强迫症治愈级边距：0.8倍字体大小 + 最小40像素，任何字符永不裁剪 ★★★
            time_margin = max(int(self.base_font_size * 0.8), 40)
            w_time = fm_time.horizontalAdvance(self._get_time_text()) + time_margin
            w_date = fm_small.horizontalAdvance(self._get_date_text()) if self.show_date else 0
            w_week = fm_small.horizontalAdvance(self._get_week_text()) if self.show_week else 0
            width = max(w_time, w_date, w_week) + 20
            
            h_time = fm_time.height()
            h_small = fm_small.height()
            height = h_time
            if self.show_date:
                height += 2 + h_small
            if self.show_week:
                height += 2 + h_small
            height += 6
            self.setFixedSize(int(width), int(height))
    
    # -------------------- 字体缓存 --------------------
    def _get_font(self, size):
        key = (self.font_family, size)
        if key not in self._cached_fonts:
            font = QFont(self.font_family, size)
            self._cached_fonts[key] = font
        return self._cached_fonts[key]
    
    def _get_font_metrics(self, size):
        key = (self.font_family, size)
        if key not in self._cached_metrics:
            font = self._get_font(size)
            metrics = QFontMetrics(font)
            self._cached_metrics[key] = metrics
        return self._cached_metrics[key]
    
    # -------------------- 文本生成 --------------------
    def _get_time_text(self):
        t = QTime.currentTime()
        if self.show_seconds:
            return t.toString("hh:mm:ss")
        else:
            return t.toString("hh:mm")
    
    def _get_date_text(self):
        return QDate.currentDate().toString("yyyy-MM-dd")
    
    def _get_week_text(self):
        return QDate.currentDate().toString("dddd")
    
    def _get_timer_text(self):
        if self._is_timer_active():
            if self.timer_mgr.countdown_seconds != DEFAULT_COUNTDOWN_MINUTES * 60 or self.timer_mgr.countdown_running:
                return f"⏳ {self.timer_mgr.get_countdown_time_str()}"
            else:
                return f"⏱️ {self.timer_mgr.get_stopwatch_time_str()}"
        return ""
    
    # -------------------- 绘制事件 --------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.font_opacity / 255.0)
        
        # 设置画笔 - 防崩溃保护
        try:
            if self.theme_name == "单色":
                painter.setPen(self.custom_color)
            else:
                if self._cached_gradient is None or self._cached_size != self.size():
                    self._cached_gradient = QLinearGradient(0, 0, self.width(), 0)
                    stops = ThemeManager.get_gradient_stops(self.theme_name)
                    for pos, color in stops:
                        self._cached_gradient.setColorAt(pos, color)
                    if stops and len(stops) > 1:
                        self._cached_gradient.setColorAt(1.0, stops[0][1])
                    self._cached_gradient.setSpread(QGradient.Spread.RepeatSpread)
                    self._cached_size = self.size()
                
                if self.animation_timer.isActive():
                    self._cached_gradient.setStart(self.gradient_offset, 0)
                    self._cached_gradient.setFinalStop(self.gradient_offset + self.width(), 0)
                painter.setPen(QPen(QBrush(self._cached_gradient), 0))
        except Exception:
            # 任何渐变异常，回退到单色（避免崩溃）
            painter.setPen(self.custom_color)
        
        y = 4
        
        if self._is_timer_active():
            timer_text = self._get_timer_text()
            font = self._get_font(self.base_font_size)
            painter.setFont(font)
            fm = self._get_font_metrics(self.base_font_size)
            x = (self.width() - fm.horizontalAdvance(timer_text)) // 2
            # 使用相同的大边距，保证计时器也不被裁剪
            margin = max(int(self.base_font_size * 0.8), 40)
            draw_width = fm.horizontalAdvance(timer_text) + margin
            painter.drawText(QRect(x, y, draw_width, fm.height()),
                             Qt.AlignmentFlag.AlignLeft, timer_text)
        else:
            fm_time = self._get_font_metrics(self.base_font_size)
            fm_small = self._get_font_metrics(int(self.base_font_size * 0.45))
            
            # 绘制时间 - 使用超大边距
            painter.setFont(self._get_font(self.base_font_size))
            time_text = self._get_time_text()
            x = (self.width() - fm_time.horizontalAdvance(time_text)) // 2
            margin = max(int(self.base_font_size * 0.8), 40)
            draw_width = fm_time.horizontalAdvance(time_text) + margin
            painter.drawText(QRect(x, y, draw_width, fm_time.height()),
                             Qt.AlignmentFlag.AlignLeft, time_text)
            y += fm_time.height() + 2
            
            if self.show_date:
                painter.setFont(self._get_font(int(self.base_font_size * 0.45)))
                date_text = self._get_date_text()
                x = (self.width() - fm_small.horizontalAdvance(date_text)) // 2
                # 日期/星期较小，边距0.2倍足够
                draw_width = fm_small.horizontalAdvance(date_text) + int(self.base_font_size * 0.2)
                painter.drawText(QRect(x, y, draw_width, fm_small.height()),
                                 Qt.AlignmentFlag.AlignLeft, date_text)
                y += fm_small.height() + 2
            
            if self.show_week:
                painter.setFont(self._get_font(int(self.base_font_size * 0.45)))
                week_text = self._get_week_text()
                x = (self.width() - fm_small.horizontalAdvance(week_text)) // 2
                draw_width = fm_small.horizontalAdvance(week_text) + int(self.base_font_size * 0.2)
                painter.drawText(QRect(x, y, draw_width, fm_small.height()),
                                 Qt.AlignmentFlag.AlignLeft, week_text)
    
    def _update_gradient(self):
        if self.width() > 0:
            self.gradient_offset += 2
            self.gradient_offset %= self.width()
            self.update()
    
    # -------------------- 鼠标拖拽 --------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_fixed:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_fixed and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self._save_position()
    
    # -------------------- 位置持久化 --------------------
    def _save_position(self):
        pos = self.pos()
        self.settings.set("pos_x", pos.x())
        self.settings.set("pos_y", pos.y())
    
    def _load_position(self):
        x = self.settings.get("pos_x", 100)
        y = self.settings.get("pos_y", 100)
        self.move(x, y)
    
    # -------------------- 公共设置接口 --------------------
    def set_font_family(self, family):
        self.font_family = family
        self._cached_fonts.clear()
        self._cached_metrics.clear()
        self.update_geometry()
        self.appearance_changed.emit()
    
    def set_base_font_size(self, size):
        size = max(20, min(250, size))
        self.base_font_size = size
        self._cached_fonts.clear()
        self._cached_metrics.clear()
        self.update_geometry()
        self.appearance_changed.emit()
    
    def set_font_opacity(self, opacity):
        self.font_opacity = max(0, min(255, opacity))
        self.update()
        self.appearance_changed.emit()
    
    def set_custom_color(self, color):
        self.custom_color = color
        if self.theme_name == "单色":
            self.update()
        self.appearance_changed.emit()
    
    def set_theme(self, theme_name):
        """切换主题，带崩溃保护"""
        try:
            self.theme_name = theme_name
            
            self.animation_timer.stop()
            self.gradient_offset = 0
            
            self._cached_gradient = None
            self._cached_size = None
            
            if theme_name != "单色":
                QTimer.singleShot(50, self._safe_start_animation)
            
            self.update()
            self.appearance_changed.emit()
        except Exception as e:
            print(f"切换主题异常: {e}")
            traceback.print_exc()
            self.theme_name = "单色"
            self._cached_gradient = None
            self.animation_timer.stop()
            self.update()
    
    def _safe_start_animation(self):
        try:
            if not self.animation_timer.isActive():
                self.animation_timer.start()
        except:
            pass
    
    def set_show_date(self, show):
        self.show_date = show
        self.update_geometry()
        self.appearance_changed.emit()
    
    def set_show_week(self, show):
        self.show_week = show
        self.update_geometry()
        self.appearance_changed.emit()
    
    def set_show_seconds(self, show):
        self.show_seconds = show
        self.clock_timer.setInterval(1000 if not show else 100)
        self.update()
        self.appearance_changed.emit()
    
    def set_fixed_pos(self, fixed):
        self.is_fixed = fixed
        self.appearance_changed.emit()
    
    def set_stay_on_top(self, on_top):
        flags = self.windowFlags()
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self.appearance_changed.emit()
    
    def closeEvent(self, event):
        self._save_position()
        event.ignore()
        self.hide()


# ---------------------------- 设置对话框 ----------------------------
class SettingsDialog(QDialog):
    """外观、倒计时、启动设置对话框，实时预览"""
    
    font_family_changed = pyqtSignal(str)
    base_size_changed = pyqtSignal(int)
    font_opacity_changed = pyqtSignal(int)
    custom_color_changed = pyqtSignal(QColor)
    theme_changed = pyqtSignal(str)
    show_date_changed = pyqtSignal(bool)
    show_week_changed = pyqtSignal(bool)
    show_seconds_changed = pyqtSignal(bool)
    fixed_pos_changed = pyqtSignal(bool)
    stay_on_top_changed = pyqtSignal(bool)
    countdown_minutes_changed = pyqtSignal(int)
    
    def __init__(self, settings, clock, timer_mgr, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.clock = clock
        self.timer_mgr = timer_mgr
        
        self.setWindowTitle("时钟设置")
        self.setMinimumSize(500, 400)
        
        self._size_timer = QTimer()
        self._size_timer.setSingleShot(True)
        self._size_timer.timeout.connect(self._on_size_slider_released)
        self._opacity_timer = QTimer()
        self._opacity_timer.setSingleShot(True)
        self._opacity_timer.timeout.connect(self._on_opacity_slider_released)
        
        self._init_ui()
        self._load_settings()
        self._connect_signals()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        
        # ---------- 外观选项卡 ----------
        appearance_tab = QWidget()
        tab_layout = QVBoxLayout()
        
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体:"))
        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.addItems(QFontDatabase.families())
        font_layout.addWidget(self.font_combo)
        font_layout.addStretch()
        tab_layout.addLayout(font_layout)
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("字体大小:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(20, 250)
        self.size_slider.setTickInterval(10)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_label = QLabel("80")
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_label)
        tab_layout.addLayout(size_layout)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setTickInterval(51)
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_label = QLabel("255")
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        tab_layout.addLayout(opacity_layout)
        
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("字体颜色:"))
        self.color_btn = QPushButton("选择颜色")
        self.color_btn.clicked.connect(self._choose_color)
        self.color_preview = QLabel("   ")
        self.color_preview.setStyleSheet("background-color: white; border:1px solid black;")
        self.color_preview.setFixedSize(30, 20)
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        tab_layout.addLayout(color_layout)
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("渐变主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(ThemeManager.THEMES.keys())
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        tab_layout.addLayout(theme_layout)
        
        display_group = QGroupBox("显示内容")
        display_layout = QVBoxLayout()
        self.show_date_cb = QCheckBox("显示日期")
        self.show_week_cb = QCheckBox("显示星期")
        self.show_seconds_cb = QCheckBox("显示秒钟")
        display_layout.addWidget(self.show_date_cb)
        display_layout.addWidget(self.show_week_cb)
        display_layout.addWidget(self.show_seconds_cb)
        display_group.setLayout(display_layout)
        tab_layout.addWidget(display_group)
        
        tab_layout.addStretch()
        appearance_tab.setLayout(tab_layout)
        self.tab_widget.addTab(appearance_tab, "外观")
        
        # ---------- 倒计时设置选项卡 ----------
        countdown_tab = QWidget()
        cd_layout = QVBoxLayout()
        cd_layout.addWidget(QLabel("默认倒计时时间:"))
        self.countdown_spin = QSpinBox()
        self.countdown_spin.setRange(1, 999)
        self.countdown_spin.setSuffix(" 分钟")
        cd_layout.addWidget(self.countdown_spin)
        cd_layout.addStretch()
        countdown_tab.setLayout(cd_layout)
        self.tab_widget.addTab(countdown_tab, "倒计时")
        
        # ---------- 启动设置选项卡 ----------
        startup_tab = QWidget()
        st_layout = QVBoxLayout()
        self.startup_cb = QCheckBox("开机自启动")
        self.fixed_pos_cb = QCheckBox("固定时钟")
        self.stay_on_top_cb = QCheckBox("时钟置顶")
        st_layout.addWidget(self.startup_cb)
        st_layout.addWidget(self.fixed_pos_cb)
        st_layout.addWidget(self.stay_on_top_cb)
        st_layout.addStretch()
        startup_tab.setLayout(st_layout)
        self.tab_widget.addTab(startup_tab, "启动")
        
        layout.addWidget(self.tab_widget)
        
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _load_settings(self):
        self.font_combo.setCurrentText(self.clock.font_family)
        self.size_slider.setValue(self.clock.base_font_size)
        self.size_label.setText(str(self.clock.base_font_size))
        self.opacity_slider.setValue(self.clock.font_opacity)
        self.opacity_label.setText(str(self.clock.font_opacity))
        self.color_preview.setStyleSheet(f"background-color: {self.clock.custom_color.name()}; border:1px solid black;")
        self.theme_combo.setCurrentText(self.clock.theme_name)
        self.show_date_cb.setChecked(self.clock.show_date)
        self.show_week_cb.setChecked(self.clock.show_week)
        self.show_seconds_cb.setChecked(self.clock.show_seconds)
        self.countdown_spin.setValue(self.settings.get("countdown_minutes", DEFAULT_COUNTDOWN_MINUTES))
        self.startup_cb.setChecked(self.settings.get("startup_with_os", DEFAULT_STARTUP_WITH_OS))
        self.fixed_pos_cb.setChecked(self.clock.is_fixed)
        self.stay_on_top_cb.setChecked(self.settings.get("stay_on_top", DEFAULT_STAY_ON_TOP))
    
    def _connect_signals(self):
        self.font_combo.currentTextChanged.connect(self.font_family_changed)
        self.font_combo.currentTextChanged.connect(lambda f: self.settings.set("font_family", f))
        
        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(str(v)))
        self.size_slider.valueChanged.connect(lambda: self._size_timer.start(50))
        
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(str(v)))
        self.opacity_slider.valueChanged.connect(lambda: self._opacity_timer.start(50))
        
        self.theme_combo.currentTextChanged.connect(self.theme_changed)
        self.theme_combo.currentTextChanged.connect(lambda t: self.settings.set("theme", t))
        
        self.show_date_cb.toggled.connect(self.show_date_changed)
        self.show_date_cb.toggled.connect(lambda b: self.settings.set("show_date", b))
        self.show_week_cb.toggled.connect(self.show_week_changed)
        self.show_week_cb.toggled.connect(lambda b: self.settings.set("show_week", b))
        self.show_seconds_cb.toggled.connect(self.show_seconds_changed)
        self.show_seconds_cb.toggled.connect(lambda b: self.settings.set("show_seconds", b))
        
        self.countdown_spin.valueChanged.connect(lambda v: self.settings.set("countdown_minutes", v))
        self.countdown_spin.valueChanged.connect(self.countdown_minutes_changed)
        
        self.startup_cb.toggled.connect(lambda b: self.settings.set("startup_with_os", b))
        self.fixed_pos_cb.toggled.connect(self.fixed_pos_changed)
        self.fixed_pos_cb.toggled.connect(lambda b: self.settings.set("fixed_pos", b))
        self.stay_on_top_cb.toggled.connect(self.stay_on_top_changed)
        self.stay_on_top_cb.toggled.connect(lambda b: self.settings.set("stay_on_top", b))
    
    def _on_size_slider_released(self):
        val = self.size_slider.value()
        self.base_size_changed.emit(val)
        self.settings.set("base_size", val)
    
    def _on_opacity_slider_released(self):
        val = self.opacity_slider.value()
        self.font_opacity_changed.emit(val)
        self.settings.set("font_opacity", val)
    
    def _choose_color(self):
        color = QColorDialog.getColor(self.clock.custom_color, self)
        if color.isValid():
            self.color_preview.setStyleSheet(f"background-color: {color.name()}; border:1px solid black;")
            self.custom_color_changed.emit(color)
            self.settings.set("custom_color", color)
    
    def accept(self):
        self._on_size_slider_released()
        self._on_opacity_slider_released()
        self.timer_mgr.set_countdown_minutes(self.countdown_spin.value())
        super().accept()
    
    def reject(self):
        super().reject()


# ---------------------------- 托盘图标 ----------------------------
class TrayIcon(QSystemTrayIcon):
    """系统托盘，提供右键菜单和双击响应"""
    
    show_hide_clock = pyqtSignal()
    quit_app = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(self._create_icon())
        self.setToolTip("桌面时钟")
        
        self.menu = QMenu()
        
        self.show_action = QAction("显示时钟", self)
        self.show_action.setCheckable(True)
        self.show_action.setChecked(True)
        self.show_action.triggered.connect(self._on_show_clock)
        
        self.countdown_action = QAction("开始倒计时", self)
        self.stopwatch_action = QAction("开始计时", self)
        self.reset_countdown_action = QAction("重置倒计时", self)
        self.reset_stopwatch_action = QAction("重置计时", self)
        
        self.settings_action = QAction("时钟设置", self)
        self.quit_action = QAction("退出", self)
        self.quit_action.triggered.connect(self.quit_app.emit)
        
        self.menu.addAction(self.show_action)
        self.menu.addSeparator()
        self.menu.addAction(self.countdown_action)
        self.menu.addAction(self.reset_countdown_action)
        self.menu.addSeparator()
        self.menu.addAction(self.stopwatch_action)
        self.menu.addAction(self.reset_stopwatch_action)
        self.menu.addSeparator()
        self.menu.addAction(self.settings_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        
        self.setContextMenu(self.menu)
        self.activated.connect(self._on_activated)
    
    def _create_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.GlobalColor.white, 3))
        painter.setBrush(QBrush(Qt.GlobalColor.gray))
        painter.drawEllipse(4, 4, 56, 56)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawLine(32, 32, 32, 16)
        painter.drawLine(32, 32, 48, 32)
        painter.end()
        return QIcon(pixmap)
    
    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_hide_clock.emit()
    
    def _on_show_clock(self, checked):
        self.show_hide_clock.emit()
    
    def set_countdown_running(self, running):
        self.countdown_action.setText("暂停倒计时" if running else "开始倒计时")
    
    def set_stopwatch_running(self, running):
        self.stopwatch_action.setText("暂停计时" if running else "开始计时")


# ---------------------------- 设置持久化（类型安全版） ----------------------------
class SettingsManager:
    """使用QSettings保存/加载配置，自动处理类型转换"""
    
    def __init__(self):
        self.qsettings = QSettings(ORG_NAME, APP_NAME)
    
    def get(self, key, default=None):
        value = self.qsettings.value(key, default)
        if default is not None:
            if isinstance(default, bool):
                if isinstance(value, str):
                    return value.lower() == "true"
                return bool(value) if value is not None else default
            elif isinstance(default, int):
                try:
                    return int(value) if value is not None else default
                except:
                    return default
            elif isinstance(default, float):
                try:
                    return float(value) if value is not None else default
                except:
                    return default
            elif isinstance(default, str):
                return str(value) if value is not None else default
            elif isinstance(default, QColor):
                if isinstance(value, str):
                    return QColor(value)
                elif isinstance(value, QColor):
                    return value
                return default
        return value
    
    def set(self, key, value):
        self.qsettings.setValue(key, value)
    
    def sync(self):
        self.qsettings.sync()


# ---------------------------- 单实例保护（PyQt6 纯标志位版） ----------------------------
class SingleInstance:
    """共享内存锁，确保只有一个实例运行（无 setData，纯 create/attach 判断）"""
    
    def __init__(self, key):
        self.key = key
        self.shared_mem = QSharedMemory(key)
        self.is_running = False

    def try_lock(self):
        if self.shared_mem.isAttached():
            self.shared_mem.detach()

        if self.shared_mem.create(1):
            return True

        if self.shared_mem.error() == QSharedMemory.SharedMemoryError.AlreadyExists:
            if self.shared_mem.attach():
                self.shared_mem.detach()
                self.is_running = True
                return False
            else:
                self._force_clean()
                return self.try_lock()
        else:
            return True

    def _force_clean(self):
        try:
            if self.shared_mem.attach():
                self.shared_mem.detach()
        except:
            pass

    def release(self):
        if self.shared_mem.isAttached():
            self.shared_mem.detach()


# ---------------------------- 开机自启动僵尸项清理 ----------------------------
def clean_dead_startup_entries():
    """清理注册表中指向不存在 exe 的开机启动项（同名项）"""
    if sys.platform != "win32":
        return
    
    import os
    current_name = QCoreApplication.applicationName()
    
    reg_paths = [
        "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run"
    ]
    
    for path in reg_paths:
        try:
            settings = QSettings(path, QSettings.Format.NativeFormat)
            keys = settings.childKeys()
            for key in keys:
                if current_name.lower() in key.lower():
                    exe_path = settings.value(key)
                    if exe_path and not os.path.exists(exe_path.replace('"', '')):
                        settings.remove(key)
        except:
            continue


# ---------------------------- 主程序入口 ----------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setQuitOnLastWindowClosed(False)
    
    # 清理已失效的自身开机启动项
    clean_dead_startup_entries()
    
    # 单实例检查
    instance = SingleInstance(APP_KEY)
    if not instance.try_lock():
        for widget in app.topLevelWidgets():
            if isinstance(widget, ClockWidget):
                widget.showNormal()
                widget.raise_()
                widget.activateWindow()
                break
        sys.exit(0)
    
    def cleanup():
        instance.release()
        QCoreApplication.processEvents()
    
    atexit.register(cleanup)
    app.aboutToQuit.connect(cleanup)
    
    settings = SettingsManager()
    timer_mgr = TimerManager()
    clock = ClockWidget(settings, timer_mgr)
    tray = TrayIcon()
    settings_dlg = SettingsDialog(settings, clock, timer_mgr)
    
    # 信号连接...
    tray.show_hide_clock.connect(lambda: clock.setVisible(not clock.isVisible()))
    tray.quit_app.connect(lambda: QCoreApplication.quit())
    tray.settings_action.triggered.connect(settings_dlg.exec)
    
    timer_mgr.countdown_state_changed.connect(tray.set_countdown_running)
    timer_mgr.stopwatch_state_changed.connect(tray.set_stopwatch_running)
    
    def on_countdown_triggered():
        if timer_mgr.countdown_running:
            timer_mgr.pause_countdown()
        else:
            timer_mgr.start_countdown()
    tray.countdown_action.triggered.connect(on_countdown_triggered)
    tray.reset_countdown_action.triggered.connect(lambda: timer_mgr.reset_countdown())
    
    def on_stopwatch_triggered():
        if timer_mgr.stopwatch_running:
            timer_mgr.pause_stopwatch()
        else:
            timer_mgr.start_stopwatch()
    tray.stopwatch_action.triggered.connect(on_stopwatch_triggered)
    tray.reset_stopwatch_action.triggered.connect(timer_mgr.reset_stopwatch)
    
    settings_dlg.font_family_changed.connect(clock.set_font_family)
    settings_dlg.base_size_changed.connect(clock.set_base_font_size)
    settings_dlg.font_opacity_changed.connect(clock.set_font_opacity)
    settings_dlg.custom_color_changed.connect(clock.set_custom_color)
    settings_dlg.theme_changed.connect(clock.set_theme)
    settings_dlg.show_date_changed.connect(clock.set_show_date)
    settings_dlg.show_week_changed.connect(clock.set_show_week)
    settings_dlg.show_seconds_changed.connect(clock.set_show_seconds)
    settings_dlg.fixed_pos_changed.connect(clock.set_fixed_pos)
    settings_dlg.stay_on_top_changed.connect(clock.set_stay_on_top)
    settings_dlg.countdown_minutes_changed.connect(timer_mgr.set_countdown_minutes)
    
    # 开机自启动设置
    def set_startup_with_os(enable):
        if sys.platform == "win32":
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                if enable:
                    exe_path = sys.executable
                    if not exe_path.endswith(".exe"):
                        QMessageBox.information(None, "提示", "当前不是打包后的exe，开机自启动仅对exe有效。")
                    else:
                        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.warning(None, "错误", f"设置开机自启动失败: {e}")
    
    settings_dlg.startup_cb.toggled.connect(set_startup_with_os)
    if settings.get("startup_with_os", DEFAULT_STARTUP_WITH_OS):
        set_startup_with_os(True)
    
    if settings.get("clock_visible", True):
        clock.show()
    
    tray.show()
    
    exit_code = app.exec()
    
    settings.set("clock_visible", clock.isVisible())
    settings.sync()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()