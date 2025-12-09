import sys
import os
import subprocess
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidgetItem, 
                               QHeaderView, QMessageBox, QWidget)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QRect
from PyQt5.QtGui import QColor, QFont, QPainter, QBrush, QPen, QLinearGradient, QCursor
from gui_pi import Ui_MainWindow
from config import ROOMS, POWER_THRESHOLDS
from electricity_calc import ElectricityCalculator, UsageTracker
from firebase_handler import FirebaseHandler, get_firebase
import math


class PowerChart(QWidget):
    """Custom bar chart widget for power consumption - clickable"""
    
    def __init__(self, parent=None, on_room_click=None):
        super().__init__(parent)
        self.data = []  # [(room_name, power), ...]
        self.colors = [
            QColor("#00d4ff"),  # Cyan
            QColor("#2ecc71"),  # Green
            QColor("#f39c12"),  # Orange
            QColor("#e74c3c"),  # Red
        ]
        self.bar_rects = []  # Store bar positions for click detection
        self.selected_index = -1
        self.on_room_click = on_room_click
        self.setAutoFillBackground(True)
    
    def set_data(self, data):
        """Set chart data: [(room_name, power), ...]"""
        self.data = data
        self.update()
    
    def mousePressEvent(self, event):
        """Handle click on bars"""
        pos = event.pos()
        for i, rect in enumerate(self.bar_rects):
            if rect.contains(pos):
                self.selected_index = i
                if self.on_room_click:
                    self.on_room_click(i)
                self.update()
                break
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Draw title inside
        painter.setPen(QPen(QColor("#778da9")))
        painter.setFont(QFont("Arial", 7))
        painter.drawText(0, 3, w, 14, Qt.AlignCenter, "CÔNG SUẤT (W)")
        
        if not self.data:
            return
        
        # Chart area
        margin_top = 18
        margin_bottom = 20
        margin_left = 8
        margin_right = 8
        
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom
        
        if len(self.data) == 0 or chart_h <= 0:
            return
        
        # Find max value
        max_val = max(p for _, p in self.data) if self.data else 1
        if max_val == 0:
            max_val = 1
        
        bar_width = chart_w // len(self.data) - 6
        bar_spacing = (chart_w - bar_width * len(self.data)) // (len(self.data) + 1)
        
        self.bar_rects = []
        
        for i, (name, power) in enumerate(self.data):
            # Calculate bar height
            bar_height = int((power / max_val) * chart_h * 0.85)
            if bar_height < 3:
                bar_height = 3
            
            x = margin_left + bar_spacing + i * (bar_width + bar_spacing)
            y = margin_top + chart_h - bar_height
            
            # Store rect for click detection
            self.bar_rects.append(QRect(x, y, bar_width, bar_height))
            
            # Create gradient
            gradient = QLinearGradient(x, y, x, y + bar_height)
            color = self.colors[i % len(self.colors)]
            
            # Highlight selected bar
            if i == self.selected_index:
                gradient.setColorAt(0, QColor("#ffffff"))
                gradient.setColorAt(0.3, color.lighter(150))
                gradient.setColorAt(1, color)
            else:
                gradient.setColorAt(0, color.lighter(120))
                gradient.setColorAt(1, color)
            
            # Draw bar
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_height, 3, 3)
            
            # Draw selection indicator
            if i == self.selected_index:
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(x-1, y-1, bar_width+2, bar_height+2, 4, 4)
            
            # Draw value on top
            painter.setPen(QPen(QColor("#e0e1dd")))
            painter.setFont(QFont("Arial", 7, QFont.Bold))
            value_text = f"{int(power)}"
            painter.drawText(x, y - 3, bar_width, 12, Qt.AlignCenter, value_text)
            
            # Draw room label below
            painter.setPen(QPen(QColor("#778da9")))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(x - 5, margin_top + chart_h + 2, bar_width + 10, 15, 
                           Qt.AlignCenter, name.replace("Phòng ", "P"))


class PieChart(QWidget):
    """Pie chart for room device breakdown"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # [(device_name, power, is_on), ...]
        self.room_name = ""
        self.colors = [
            QColor("#00d4ff"),
            QColor("#2ecc71"),
            QColor("#f39c12"),
            QColor("#9b59b6"),
        ]
        self.setAutoFillBackground(True)
    
    def set_data(self, room_name, data):
        """Set pie data: [(device_name, power, is_on), ...]"""
        self.room_name = room_name
        self.data = data
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Draw room name
        painter.setPen(QPen(QColor("#00d4ff")))
        painter.setFont(QFont("Arial", 7, QFont.Bold))
        title = self.room_name if self.room_name else "Chi tiết"
        painter.drawText(0, 3, w, 12, Qt.AlignCenter, title)
        
        if not self.data:
            painter.setPen(QPen(QColor("#778da9")))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(0, 16, w, h-16, Qt.AlignCenter, "Nhấp phòng\ntrên chart")
            return
        
        # Calculate total
        total = sum(p for _, p, on in self.data if on)
        if total == 0:
            painter.setPen(QPen(QColor("#778da9")))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(0, 16, w, 30, Qt.AlignCenter, "Tất cả OFF")
            self.draw_legend(painter, w, 50)
            return
        
        # Pie chart dimensions
        pie_size = min(w - 10, 65)
        pie_x = (w - pie_size) // 2
        pie_y = 16
        
        # Draw pie slices
        start_angle = 90 * 16  # Start from top
        for i, (name, power, is_on) in enumerate(self.data):
            if not is_on or power == 0:
                continue
            
            span_angle = int((power / total) * 360 * 16)
            
            color = self.colors[i % len(self.colors)]
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#0d1b2a"), 1))
            painter.drawPie(pie_x, pie_y, pie_size, pie_size, start_angle, span_angle)
            
            start_angle += span_angle
        
        # Draw legend
        self.draw_legend(painter, w, pie_y + pie_size + 4)
    
    def draw_legend(self, painter, w, start_y):
        """Draw device legend"""
        legend_x = 5
        painter.setFont(QFont("Arial", 6))
        
        for i, (name, power, is_on) in enumerate(self.data):
            y = start_y + i * 11
            color = self.colors[i % len(self.colors)] if is_on else QColor("#555")
            
            # Color box
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(legend_x, y, 7, 7)
            
            # Text
            painter.setPen(QPen(QColor("#e0e1dd") if is_on else QColor("#666")))
            status = f"{power}W" if is_on else "OFF"
            painter.drawText(legend_x + 9, y - 1, w - 15, 10, 
                           Qt.AlignLeft | Qt.AlignVCenter, f"{name}:{status}")


def hide_taskbar():
    """Hide taskbar on Raspberry Pi (LXDE/LXPanel)"""
    if sys.platform == 'linux':
        try:
            # Hide LXPanel (Raspberry Pi OS taskbar)
            subprocess.run(['lxpanelctl', 'exit'], check=False, capture_output=True)
        except:
            pass
        try:
            # Alternative: hide using xdotool
            subprocess.run(['xdotool', 'search', '--name', 'lxpanel', 'windowunmap'], 
                          check=False, capture_output=True)
        except:
            pass

def show_taskbar():
    """Show taskbar on Raspberry Pi"""
    if sys.platform == 'linux':
        try:
            # Restart LXPanel
            subprocess.Popen(['lxpanel', '--profile', 'LXDE-pi'], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass


# Professional Dark Theme Stylesheet for Power Management System (3.5" Pi Screen)
STYLESHEET = """
/* Main Window */
QMainWindow {
    background-color: #0d1b2a;
}

QWidget {
    background-color: #0d1b2a;
    color: #e0e1dd;
}

QWidget#centralwidget {
    background-color: #0d1b2a;
}

QWidget#verticalLayoutWidget {
    background-color: #1b263b;
    border-radius: 8px;
    margin: 5px;
}

/* Sidebar Navigation Buttons */
QPushButton#pushButton_2, QPushButton#pushButton_3, 
QPushButton#pushButton, QPushButton#pushButton_4 {
    background-color: #1b263b;
    color: #778da9;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 15px 10px;
    font-size: 10px;
    font-weight: bold;
    text-align: center;
    margin: 2px 0px;
}

QPushButton#pushButton_2:hover, QPushButton#pushButton_3:hover,
QPushButton#pushButton:hover, QPushButton#pushButton_4:hover {
    background-color: #415a77;
    color: #e0e1dd;
    border-left: 3px solid #00d4ff;
}

QPushButton#pushButton_2:checked, QPushButton#pushButton_3:checked,
QPushButton#pushButton:checked, QPushButton#pushButton_4:checked,
QPushButton#pushButton_2:pressed, QPushButton#pushButton_3:pressed,
QPushButton#pushButton:pressed, QPushButton#pushButton_4:pressed {
    background-color: #415a77;
    color: #00d4ff;
    border-left: 3px solid #00d4ff;
}

/* Stacked Widget Pages */
QStackedWidget {
    background-color: #1b263b;
    border-radius: 12px;
    border: 1px solid #415a77;
}

QStackedWidget > QWidget {
    background-color: #1b263b;
}

QWidget#HOME, QWidget#CONTROL, QWidget#REPORT, QWidget#page {
    background-color: #1b263b;
    border-radius: 12px;
}

/* Labels */
QLabel {
    background-color: transparent;
    color: #e0e1dd;
}

/* Exit Button */
QPushButton#exit {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ff6b6b, stop:1 #e63946);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton#exit:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ff8585, stop:1 #ff5a5f);
}

QPushButton#exit:pressed {
    background: #c0392b;
}

/* Device Control Buttons - Toggle Style */
QPushButton#pushButton_5, QPushButton#pushButton_6 {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4a6fa5, stop:1 #415a77);
    color: #e0e1dd;
    border: 2px solid #778da9;
    border-radius: 20px;
    font-size: 11px;
    font-weight: bold;
    padding: 10px 25px;
    min-width: 55px;
}

QPushButton#pushButton_5:hover, QPushButton#pushButton_6:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #00e5ff, stop:1 #00d4ff);
    border-color: #00d4ff;
    color: #0d1b2a;
}

QPushButton#pushButton_5:pressed, QPushButton#pushButton_6:pressed {
    background: #00b8d4;
}

/* PREV/NEXT Buttons */
QPushButton#pushButton_7, QPushButton#pushButton_8 {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1b263b, stop:1 #0d1b2a);
    color: #00d4ff;
    border: 2px solid #00d4ff;
    border-radius: 6px;
    font-size: 9px;
    font-weight: bold;
    padding: 6px 12px;
}

QPushButton#pushButton_7:hover, QPushButton#pushButton_8:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #00e5ff, stop:1 #00d4ff);
    color: #0d1b2a;
    border-color: #00e5ff;
}

QPushButton#pushButton_7:pressed, QPushButton#pushButton_8:pressed {
    background: #00b8d4;
}

/* Table Widget */
QTableWidget {
    background-color: #0d1b2a;
    color: #e0e1dd;
    border: 1px solid #415a77;
    border-radius: 8px;
    gridline-color: #1b263b;
    font-size: 9px;
    selection-background-color: #00d4ff;
    selection-color: #0d1b2a;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #1b263b;
}

QTableWidget::item:selected {
    background-color: #00d4ff;
    color: #0d1b2a;
}

QHeaderView::section {
    background-color: #415a77;
    color: #e0e1dd;
    padding: 6px;
    border: none;
    font-weight: bold;
    font-size: 8px;
}

QTableCornerButton::section {
    background-color: #415a77;
}

/* Menu Bar - Hidden for small screen */
QMenuBar {
    background-color: #0d1b2a;
    color: #e0e1dd;
    max-height: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #1b263b;
    color: #00d4ff;
    font-size: 9px;
    font-weight: bold;
    border-top: 1px solid #415a77;
    padding: 2px 10px;
}

/* Scrollbar */
QScrollBar:vertical {
    background-color: #0d1b2a;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #415a77;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00d4ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Hide taskbar on Pi
        hide_taskbar()
        
        # Apply professional stylesheet
        self.setStyleSheet(STYLESHEET)
        
        # Set window properties for 3.5" Pi screen - TRUE FULLSCREEN
        self.setWindowTitle("Power Management System")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()  # True fullscreen mode
        
        # Hide mouse cursor for touch screen
        self.setCursor(QCursor(Qt.BlankCursor))
        QApplication.setOverrideCursor(QCursor(Qt.BlankCursor))
        
        # Initialize Firebase handler (main data source)
        self.firebase = get_firebase()
        print(f"[FIREBASE] Connected: {self.firebase.is_connected()}, Simulation: {self.firebase.simulation_mode}")
        
        # Set callback for remote control from Firebase (app/web)
        self.firebase.set_device_change_callback(self.on_firebase_device_change)
        
        # Initialize electricity calculator
        self.calculator = ElectricityCalculator()
        self.tracker = UsageTracker()
        
        # Load thresholds from Firebase
        fb_thresholds = self.firebase.get_thresholds()
        if fb_thresholds:
            self.power_thresholds = fb_thresholds
        else:
            self.power_thresholds = POWER_THRESHOLDS.copy()
        
        # Load tier prices from Firebase
        tier_prices, vat = self.firebase.get_tier_prices()
        if tier_prices and len(tier_prices) == 6:
            self.calculator.update_tier_prices(tier_prices, vat / 100.0 if vat else 0.08)
        
        # Room navigation
        self.rooms = ROOMS
        self.current_room_index = 0
        self.current_room = self.rooms[0]
        
        # Connect navigation buttons
        self.ui.pushButton_2.clicked.connect(self.show_home)
        self.ui.pushButton_3.clicked.connect(self.show_control)
        self.ui.pushButton.clicked.connect(self.show_report)
        self.ui.pushButton_4.clicked.connect(self.show_setup)
        
        # Connect device control buttons
        self.ui.pushButton_5.clicked.connect(self.toggle_device1)
        self.ui.pushButton_6.clicked.connect(self.toggle_device2)
        self.ui.pushButton_7.clicked.connect(self.prev_room)
        self.ui.pushButton_8.clicked.connect(self.next_room)
        
        # Connect exit button
        self.ui.exit.clicked.connect(self.close)
        
        # Setup report table
        self.setup_report_table()
        
        # Setup threshold settings first (needed for chart)
        self.setup_thresholds()
        
        # Setup power chart
        self.setup_power_chart()
        
        # Setup pie chart
        self.setup_pie_chart()
        
        # Setup status bar with time
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)
        
        # Sync device states from Firebase at startup
        self.sync_devices_from_firebase()
        
        # Initialize UI
        self.update_room_display()
        self.ui.stackedWidget.setCurrentWidget(self.ui.HOME)
        self.update_nav_buttons()
        
        # Scale UI after show
        QTimer.singleShot(100, self.scale_ui)
    
    def sync_devices_from_firebase(self):
        """Sync device states from Firebase at startup (async)"""
        def do_sync():
            try:
                fb_states = self.firebase.sync_device_states_from_firebase()
                if fb_states:
                    print("[STARTUP] Loaded device states from Firebase")
            except Exception as e:
                print(f"[ERROR] Sync from Firebase failed: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=do_sync, daemon=True)
        thread.start()
    
    def scale_ui(self):
        """Scale UI elements to fit screen"""
        screen = self.geometry()
        w = screen.width()
        h = screen.height()
        
        # Calculate scale factors (design was 480x320)
        scale_x = w / 480
        scale_y = h / 320
        
        # Scale sidebar
        sidebar_w = int(70 * scale_x)
        self.ui.verticalLayoutWidget.setGeometry(QRect(0, 0, sidebar_w, int(290 * scale_y)))
        
        # Scale stacked widget (main content area)
        content_x = sidebar_w + 5
        content_w = w - content_x - 5
        content_h = h - 30  # Leave space for status bar
        self.ui.stackedWidget.setGeometry(QRect(content_x, 0, content_w, content_h))
    
    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        self.scale_ui()
    
    def show_home(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.HOME)
        self.update_nav_buttons()
    
    def show_control(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.CONTROL)
        self.update_nav_buttons()
    
    def show_report(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.REPORT)
        self.update_nav_buttons()
    
    def show_setup(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.page)
        self.update_nav_buttons()
    
    def update_nav_buttons(self):
        current = self.ui.stackedWidget.currentWidget()
        # Reset all button styles using stored styles
        buttons = [self.ui.pushButton_2, self.ui.pushButton_3, 
                   self.ui.pushButton, self.ui.pushButton_4]
        pages = [self.ui.HOME, self.ui.CONTROL, self.ui.REPORT, self.ui.page]
        
        for btn, page in zip(buttons, pages):
            if current == page:
                btn.setStyleSheet(self.ui.menuButtonActiveStyle)
            else:
                btn.setStyleSheet(self.ui.menuButtonStyle)
    
    def toggle_device1(self):
        room_id = self.current_room['id']
        device = self.current_room['devices'][0]
        
        # Toggle device via Firebase
        success = self.firebase.toggle_device(room_id, device['id'])
        if success:
            state = self.firebase.get_device_state(room_id, device['id'])
            self.update_device1_ui(state)
            print(f"[UI] Toggle device1: Room {room_id}, Device {device['id']} -> {'ON' if state else 'OFF'}")
    
    def toggle_device2(self):
        room_id = self.current_room['id']
        device = self.current_room['devices'][1]
        
        # Toggle device via Firebase
        success = self.firebase.toggle_device(room_id, device['id'])
        if success:
            state = self.firebase.get_device_state(room_id, device['id'])
            self.update_device2_ui(state)
            print(f"[UI] Toggle device2: Room {room_id}, Device {device['id']} -> {'ON' if state else 'OFF'}")
    
    def on_firebase_device_change(self, room_id: int, device_id: int, state: bool):
        """
        Handle device state change from Firebase (remote control from app/web)
        This is called when someone controls device via Firebase
        """
        print(f"[UI] Firebase remote control: Room {room_id}, Device {device_id} -> {'ON' if state else 'OFF'}")
        
        # Update UI if this is the current room being displayed
        if room_id == self.current_room['id']:
            devices = self.current_room['devices']
            if device_id == devices[0]['id']:
                self.update_device1_ui(state)
            elif len(devices) > 1 and device_id == devices[1]['id']:
                self.update_device2_ui(state)
    
    def prev_room(self):
        self.current_room_index = (self.current_room_index - 1) % len(self.rooms)
        self.current_room = self.rooms[self.current_room_index]
        self.update_room_display()
    
    def next_room(self):
        self.current_room_index = (self.current_room_index + 1) % len(self.rooms)
        self.current_room = self.rooms[self.current_room_index]
        self.update_room_display()
    
    def update_device1_ui(self, state):
        """Update Device 1 button and status label"""
        if state:
            self.ui.pushButton_5.setText("ON")
            self.ui.pushButton_5.setStyleSheet(
                "background-color: #2ecc71; color: white; border: none; "
                "border-radius: 15px; font-size: 12px; font-weight: bold;")
            self.ui.device1Status.setText("ON")
            self.ui.device1Status.setStyleSheet(
                "color: #2ecc71; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        else:
            self.ui.pushButton_5.setText("OFF")
            self.ui.pushButton_5.setStyleSheet(
                "background-color: #e74c3c; color: white; border: none; "
                "border-radius: 15px; font-size: 12px; font-weight: bold;")
            self.ui.device1Status.setText("OFF")
            self.ui.device1Status.setStyleSheet(
                "color: #e74c3c; font-size: 12px; font-weight: bold; background: transparent; border: none;")
    
    def update_device2_ui(self, state):
        """Update Device 2 button and status label"""
        if state:
            self.ui.pushButton_6.setText("ON")
            self.ui.pushButton_6.setStyleSheet(
                "background-color: #2ecc71; color: white; border: none; "
                "border-radius: 15px; font-size: 12px; font-weight: bold;")
            self.ui.device2Status.setText("ON")
            self.ui.device2Status.setStyleSheet(
                "color: #2ecc71; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        else:
            self.ui.pushButton_6.setText("OFF")
            self.ui.pushButton_6.setStyleSheet(
                "background-color: #e74c3c; color: white; border: none; "
                "border-radius: 15px; font-size: 12px; font-weight: bold;")
            self.ui.device2Status.setText("OFF")
            self.ui.device2Status.setStyleSheet(
                "color: #e74c3c; font-size: 12px; font-weight: bold; background: transparent; border: none;")
    
    def update_room_display(self):
        """Update control page for current room"""
        room_id = self.current_room['id']
        self.ui.name_ctl_3.setText(str(room_id))
        
        # Update device labels
        devices = self.current_room['devices']
        if len(devices) >= 1:
            self.ui.label_8.setText(devices[0]['name'])
            state1 = self.firebase.get_device_state(room_id, devices[0]['id'])
            self.update_device1_ui(state1)
        
        if len(devices) >= 2:
            self.ui.label_9.setText(devices[1]['name'])
            state2 = self.firebase.get_device_state(room_id, devices[1]['id'])
            self.update_device2_ui(state2)
    
    def setup_report_table(self):
        # Setup table columns - now wider (195px)
        self.ui.REPORTTB.setColumnCount(3)
        self.ui.REPORTTB.setHorizontalHeaderLabels(["Phòng", "Thiết bị", "W"])
        
        # Set column widths
        self.ui.REPORTTB.setColumnWidth(0, 45)
        self.ui.REPORTTB.setColumnWidth(1, 90)
        self.ui.REPORTTB.setColumnWidth(2, 45)
        
        # Hide row numbers, compact rows
        self.ui.REPORTTB.verticalHeader().setVisible(False)
        self.ui.REPORTTB.verticalHeader().setDefaultSectionSize(18)
        self.ui.REPORTTB.horizontalHeader().setStretchLastSection(True)
        
        self.update_report_table()
    
    def setup_power_chart(self):
        """Setup the power chart widget"""
        # Replace the placeholder widget with our custom chart
        self.power_chart = PowerChart(self.ui.chartWidget, on_room_click=self.on_room_selected)
        self.power_chart.setGeometry(0, 0, 
                                     self.ui.chartWidget.width(), 
                                     self.ui.chartWidget.height())
        self.selected_room_index = -1
        self.update_power_chart()
    
    def setup_pie_chart(self):
        """Setup the pie chart widget"""
        self.pie_chart = PieChart(self.ui.pieWidget)
        self.pie_chart.setGeometry(0, 0,
                                   self.ui.pieWidget.width(),
                                   self.ui.pieWidget.height())
    
    def setup_thresholds(self):
        """Setup threshold settings"""
        self.warning_threshold = POWER_THRESHOLDS['warning']
        self.critical_threshold = POWER_THRESHOLDS['critical']
        
        # Room thresholds (default 200W each)
        self.room_thresholds = [200, 200, 200, 200]
        
        # Set initial values for global thresholds
        self.ui.warningThresholdInput.setValue(self.warning_threshold)
        self.ui.criticalThresholdInput.setValue(self.critical_threshold)
        
        # Set initial values for room thresholds
        for i, spin in enumerate(self.ui.roomThresholdInputs):
            spin.setValue(self.room_thresholds[i])
        
        # Connect save buttons
        self.ui.saveThresholdBtn.clicked.connect(self.save_thresholds)
        self.ui.saveTierBtn.clicked.connect(self.save_tier_prices)
    
    def save_thresholds(self):
        """Save threshold settings"""
        self.warning_threshold = self.ui.warningThresholdInput.value()
        self.critical_threshold = self.ui.criticalThresholdInput.value()
        
        # Save room thresholds
        for i, spin in enumerate(self.ui.roomThresholdInputs):
            self.room_thresholds[i] = spin.value()
        
        # Sync to Firebase
        self.firebase.set_thresholds(self.warning_threshold, self.critical_threshold)
        
        # Visual feedback
        self.ui.saveThresholdBtn.setText("Da luu")
        QTimer.singleShot(1500, lambda: self.ui.saveThresholdBtn.setText("Luu nguong"))
    
    def save_tier_prices(self):
        """Save electricity tier prices"""
        # Get tier prices from inputs
        tier_prices = []
        for spin in self.ui.tierInputs:
            tier_prices.append(spin.value())
        
        # Get VAT
        vat = self.ui.vatInput.value() / 100.0
        
        # Update the calculator with new prices
        self.calculator.update_tier_prices(tier_prices, vat)
        
        # Sync to Firebase
        self.firebase.set_tier_prices(tier_prices, self.ui.vatInput.value())
        
        # Visual feedback
        self.ui.saveTierBtn.setText("Da luu")
        QTimer.singleShot(1500, lambda: self.ui.saveTierBtn.setText("Luu gia dien"))
    
    def on_room_selected(self, room_index):
        """Handle room selection from bar chart"""
        self.selected_room_index = room_index
        self.update_pie_chart()
    
    def update_pie_chart(self):
        """Update pie chart for selected room"""
        if self.selected_room_index < 0 or self.selected_room_index >= len(self.rooms):
            self.pie_chart.set_data("", [])
            return
        
        room = self.rooms[self.selected_room_index]
        pie_data = []
        
        for device in room['devices']:
            state = self.firebase.get_device_state(room['id'], device['id'])
            # Đọc power từ Firebase
            power = self.firebase.get_device_power(room['id'], device['id'])
            pie_data.append((device['name'], power, state))
        
        self.pie_chart.set_data(room['name'], pie_data)
    
    def update_power_chart(self):
        """Update power chart with current room power data"""
        chart_data = []
        total_power = 0
        room_warnings = []
        
        for i, room in enumerate(self.rooms):
            room_power = self.firebase.get_room_power(room['id'])
            chart_data.append((room['name'], room_power))
            total_power += room_power
            
            # Check room threshold
            if i < len(self.room_thresholds) and room_power > self.room_thresholds[i]:
                room_warnings.append(f"P{i+1}:{int(room_power)}W")
        
        self.power_chart.set_data(chart_data)
        self.ui.totalPowerLabel.setText(f"Tổng: {int(total_power)} W")
        
        # Check thresholds and update warning
        self.check_power_threshold(total_power, room_warnings)
    
    def update_report_table(self):
        """Update report table with current device states"""
        # Count total rows needed
        total_rows = sum(len(room['devices']) for room in self.rooms)
        self.ui.REPORTTB.setRowCount(total_rows)
        
        row = 0
        for room in self.rooms:
            room_short = room['name'].replace("Phòng ", "P")
            for device in room['devices']:
                state = self.firebase.get_device_state(room['id'], device['id'])
                # Đọc power từ Firebase thay vì config
                power = self.firebase.get_device_power(room['id'], device['id']) if state else 0
                
                # Room column
                room_item = QTableWidgetItem(room_short)
                room_item.setForeground(QColor("#778da9"))
                self.ui.REPORTTB.setItem(row, 0, room_item)
                
                # Device column with status color
                device_item = QTableWidgetItem(device['name'])
                if state:
                    device_item.setForeground(QColor("#2ecc71"))
                else:
                    device_item.setForeground(QColor("#778da9"))
                self.ui.REPORTTB.setItem(row, 1, device_item)
                
                # Power column
                power_item = QTableWidgetItem(str(int(power)))
                power_item.setForeground(QColor("#00d4ff") if power > 0 else QColor("#778da9"))
                self.ui.REPORTTB.setItem(row, 2, power_item)
                row += 1
    
    def update_status(self):
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss dd/MM")
        total_power = self.firebase.get_active_power()
        
        # Estimate monthly cost
        estimate = self.calculator.estimate_monthly_cost(total_power)
        monthly_cost = estimate['estimated_cost'] / 1000  # Convert to thousands
        
        self.statusBar().showMessage(
            f" {current_time} | P: {total_power:.0f}W | ~{monthly_cost:.0f}k VNĐ/tháng")
        
        # Update report table and chart periodically
        self.update_report_table()
        self.update_power_chart()
        self.update_pie_chart()
        
        # Sync to Firebase every 5 seconds
        self.sync_to_firebase(total_power, monthly_cost * 1000)
    
    def sync_to_firebase(self, total_power, monthly_cost):
        """Sync power data to Firebase"""
        try:
            # Prepare room power data
            room_powers = {}
            for room in self.rooms:
                room_power = self.firebase.get_room_power(room['id'])
                room_powers[f"room{room['id']}"] = {
                    'name': room['name'],
                    'power': room_power,
                    'devices': {}
                }
                # Add device states và đọc power từ Firebase
                for device in room['devices']:
                    state = self.firebase.get_device_state(room['id'], device['id'])
                    device_power = self.firebase.get_device_power(room['id'], device['id']) if state else 0
                    room_powers[f"room{room['id']}"]['devices'][f"device{device['id']}"] = {
                        'name': device['name'],
                        'state': state,
                        'power': device_power
                    }
            
            # Update power data
            self.firebase.update_power_data(room_powers, total_power)
            
            # Update energy usage
            energy_kwh = self.tracker.get_total_energy() if hasattr(self.tracker, 'get_total_energy') else 0
            self.firebase.update_energy_usage(energy_kwh, monthly_cost)
            
        except Exception as e:
            print(f"[Firebase] Sync error: {e}")
    
    def check_power_threshold(self, total_power, room_warnings=None):
        """Check power against thresholds and show warnings"""
        # Check for room-specific warnings first
        if room_warnings and len(room_warnings) > 0:
            warning_text = "⚠ " + ", ".join(room_warnings[:2])  # Show max 2 rooms
            self.ui.warningLabel.setText(warning_text)
            self.ui.warningLabel.setStyleSheet(
                "color: #00d4ff; font-size: 9px; font-weight: bold;")
        elif total_power >= self.critical_threshold:
            # Critical warning - red
            self.ui.warningLabel.setText(f"⚠ NGUY HIỂM: {int(total_power)}W!")
            self.ui.warningLabel.setStyleSheet(
                "color: #e74c3c; font-size: 9px; font-weight: bold; "
                "background-color: rgba(231, 76, 60, 0.3); border-radius: 4px;")
            self.ui.totalPowerLabel.setStyleSheet(
                "color: #e74c3c; font-size: 10px; font-weight: bold;")
        elif total_power >= self.warning_threshold:
            # Warning - orange
            self.ui.warningLabel.setText(f"⚠ CẢNH BÁO: {int(total_power)}W")
            self.ui.warningLabel.setStyleSheet(
                "color: #f39c12; font-size: 9px; font-weight: bold; "
                "background-color: rgba(243, 156, 18, 0.2); border-radius: 4px;")
            self.ui.totalPowerLabel.setStyleSheet(
                "color: #f39c12; font-size: 10px; font-weight: bold;")
        else:
            # Normal - green
            self.ui.warningLabel.setText("✓ Bình thường")
            self.ui.warningLabel.setStyleSheet(
                "color: #2ecc71; font-size: 9px; font-weight: bold;")
            self.ui.totalPowerLabel.setStyleSheet(
                "color: #00d4ff; font-size: 10px; font-weight: bold;")
    
    def closeEvent(self, event):
        """Clean up on close"""
        # Disconnect Firebase
        self.firebase.disconnect()
        # Restore taskbar on Pi
        show_taskbar()
        # Restore mouse cursor
        QApplication.restoreOverrideCursor()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
