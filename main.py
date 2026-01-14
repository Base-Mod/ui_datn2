import sys
import os
import threading
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidgetItem, QWidget, 
                             QComboBox, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                             QSpinBox, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QRect
from PyQt5.QtGui import QColor, QFont, QCursor
from gui_pi import Ui_MainWindow
from db_manager import DatabaseManager
from line_chart import PowerLineChart

# Global Exception Hook to catch crashes
def exception_hook(exctype, value, tb):
    print("CRITICAL ERROR: Uncaught exception")
    traceback.print_exception(exctype, value, tb)
    with open("crash_log.txt", "a") as f:
        f.write("\n\n--- Crash at " + str(QDateTime.currentDateTime().toString()) + " ---\n")
        traceback.print_exception(exctype, value, tb, file=f)
    # Don't exit immediately, let user see console if possible
    input("Press Enter to exit...")
    sys.exit(1)

sys.excepthook = exception_hook

# Offline mode flag - set to skip database connection
OFFLINE_MODE = os.environ.get('OFFLINE_MODE', 'false').lower() == 'true'

class AlertOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Make it appear as an overlay on top of everything
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        # Large font for visibility
        self.label.setFont(QFont("Arial", 20, QFont.Bold))
        layout.addWidget(self.label)
        self.hide()

    def show_message(self, text, style):
        self.label.setText(text)
        self.label.setStyleSheet(style)
        self.adjustSize()
        
        # Center relative to parent (MainWindow)
        if self.parent():
            parent_geo = self.parent().geometry()
            # Calculate center position
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
        self.show()
        self.raise_()

# --- Database Configuration ---
DB_CONFIG = {
    "host": "47.128.66.94",
    "user": "root",
    "password": "fbd3b9f31da4a89d",
    "database": "power_management"
}

# --- System Functions ---
def hide_taskbar():
    if sys.platform == 'linux':
        try:
            import subprocess
            subprocess.run(['lxpanelctl', 'exit'], check=False, capture_output=True)
        except:
            pass

def show_taskbar():
    if sys.platform == 'linux':
        try:
            import subprocess
            subprocess.Popen(['lxpanel', '--profile', 'LXDE-pi'], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

# Professional Dark Theme Stylesheet
STYLESHEET = """
QMainWindow { background-color: #0d1b2a; }
QWidget { background-color: #0d1b2a; color: #e0e1dd; }
QWidget#centralwidget { background-color: #0d1b2a; }
QWidget#verticalLayoutWidget { background-color: #1b263b; border-radius: 8px; margin: 5px; }

/* Sidebar Navigation Buttons */
QPushButton#pushButton_2, QPushButton#pushButton_3, 
QPushButton#pushButton, QPushButton#pushButton_4 {
    background-color: #1b263b; color: #778da9; border: none;
    border-left: 3px solid transparent; border-radius: 0px;
    padding: 15px 10px; font-size: 10px; font-weight: bold;
    text-align: center; margin: 2px 0px;
}
QPushButton#pushButton_2:hover, QPushButton#pushButton_3:hover,
QPushButton#pushButton:hover, QPushButton#pushButton_4:hover {
    background-color: #415a77; color: #e0e1dd; border-left: 3px solid #00d4ff;
}
QPushButton#pushButton_2:checked, QPushButton#pushButton_3:checked,
QPushButton#pushButton:checked, QPushButton#pushButton_4:checked,
QPushButton#pushButton_2:pressed, QPushButton#pushButton_3:pressed,
QPushButton#pushButton:pressed, QPushButton#pushButton_4:pressed {
    background-color: #415a77; color: #00d4ff; border-left: 3px solid #00d4ff;
}

/* Stacked Widget */
QStackedWidget { background-color: #1b263b; border-radius: 12px; border: 1px solid #415a77; }
QStackedWidget > QWidget { background-color: #1b263b; }
QWidget#HOME, QWidget#CONTROL, QWidget#REPORT, QWidget#page { background-color: #1b263b; border-radius: 12px; }

/* Labels & Buttons */
QLabel { background-color: transparent; color: #e0e1dd; }
QPushButton#exit {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6b6b, stop:1 #e63946);
    color: white; border: none; border-radius: 12px; font-size: 12px; font-weight: bold;
}
QPushButton#exit:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff8585, stop:1 #ff5a5f); }

/* Control Buttons */
QPushButton#pushButton_5, QPushButton#pushButton_6 {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a6fa5, stop:1 #415a77);
    color: #e0e1dd; border: 2px solid #778da9; border-radius: 20px;
    font-size: 11px; font-weight: bold; padding: 10px 25px; min-width: 55px;
}
QPushButton#pushButton_5:hover, QPushButton#pushButton_6:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00e5ff, stop:1 #00d4ff);
    border-color: #00d4ff; color: #0d1b2a;
}
QPushButton#pushButton_5:pressed, QPushButton#pushButton_6:pressed { background: #00b8d4; }

/* Table Widget */
QTableWidget {
    background-color: #0d1b2a; color: #e0e1dd; border: 1px solid #415a77;
    border-radius: 8px; gridline-color: #1b263b; font-size: 9px;
    selection-background-color: #00d4ff; selection-color: #0d1b2a;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #1b263b; }
QHeaderView::section {
    background-color: #415a77; color: #e0e1dd; padding: 6px;
    border: none; font-weight: bold; font-size: 8px;
}

/* ComboBox */
QComboBox {
    background-color: #1b263b; color: #e0e1dd; border: 1px solid #415a77;
    border-radius: 6px; padding: 5px; font-size: 9px;
}
QComboBox:hover { border-color: #00d4ff; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #1b263b; color: #e0e1dd; selection-background-color: #00d4ff;
}

/* SpinBox & LineEdit */
QSpinBox, QLineEdit {
    background-color: #1b263b; color: #e0e1dd; border: 1px solid #415a77;
    border-radius: 6px; padding: 5px; font-size: 9px;
}
QSpinBox:focus, QLineEdit:focus { border-color: #00d4ff; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        try:
            print("[DEBUG] MainWindow initialization started")
            super().__init__()
            
            print("[DEBUG] Setting up UI...")
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
            print("[DEBUG] UI setup complete")
            
            hide_taskbar()
            self.setStyleSheet(STYLESHEET)
            
            # Setup Alert Overlay
            self.alert_overlay = AlertOverlay(self)
            
            # Window setup
            self.setWindowTitle("Power Management System")
            if sys.platform == 'linux':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
                self.showFullScreen()
                self.setCursor(QCursor(Qt.BlankCursor))
                QApplication.setOverrideCursor(QCursor(Qt.BlankCursor))
            else:
                self.resize(480, 320)
            print("[DEBUG] Window setup complete")
            
            # --- Database Connection ---
            self.db = None
            self.db_connected = False
            self.is_connecting = False
            
            # Kết nối database ngay khi khởi động
            print("[DEBUG] Connecting to database...")
            self.connect_db_sync()
            
            # --- Local State Initialization ---
            self.pending_devices = []  # List of devices from pending_commands
            self.current_slave_index = 0
            self.current_slave_id = None
            self.settings = {}
            self.selected_report_slave_id = None
            print("[DEBUG] State initialized")
            
            # Connect Navigation
            print("[DEBUG] Connecting navigation buttons...")
            self.ui.pushButton_2.clicked.connect(self.show_home)
            self.ui.pushButton_3.clicked.connect(self.show_control)
            self.ui.pushButton.clicked.connect(self.show_report)
            self.ui.pushButton_4.clicked.connect(self.show_setup)
            
            # Connect Controls
            self.ui.pushButton_5.clicked.connect(self.toggle_device1)
            self.ui.pushButton_6.clicked.connect(self.toggle_device2)
            self.ui.pushButton_7.clicked.connect(self.prev_slave)
            self.ui.pushButton_8.clicked.connect(self.next_slave)
            self.ui.exit.clicked.connect(self.close)
            print("[DEBUG] Buttons connected")
            
            # Setup Components
            print("[DEBUG] Setting up components...")
            self.setup_control_page()
            self.setup_report_page()
            self.setup_setup_page()
            print("[DEBUG] Components setup complete")
            
            # Timer for periodic updates
            print("[DEBUG] Starting timer...")
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_status)
            self.timer.start(2000)  # Update every 2 seconds
            print("[DEBUG] Timer started")
            
            # Startup
            print("[DEBUG] Setting startup page...")
            self.ui.stackedWidget.setCurrentWidget(self.ui.HOME)
            self.update_nav_buttons()
            QTimer.singleShot(100, self.scale_ui)
            print("[DEBUG] MainWindow initialization complete!")
            
        except Exception as e:
            print(f"[CRITICAL ERROR] MainWindow initialization failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    def connect_db_sync(self):
        """Connect to database synchronously"""
        try:
            print("[DB] Connecting to database...")
            self.db = DatabaseManager(**DB_CONFIG)
            
            if self.db.connect():
                print("[DB] Database connected successfully")
                self.db_connected = True
                self.load_data()
            else:
                print("[DB] Failed to connect to database - will retry...")
                self.db_connected = False
                # Thử kết nối lại sau 5 giây
                QTimer.singleShot(5000, self.retry_db_connection)
        except Exception as e:
            print(f"[DB] Database connection error: {e}")
            self.db_connected = False
            # Thử kết nối lại sau 5 giây
            QTimer.singleShot(5000, self.retry_db_connection)

    def retry_db_connection(self):
        """Retry database connection"""
        if self.db_connected:
            return
        print("[DB] Retrying database connection...")
        self.connect_db_sync()

    def connect_db(self):
        """Run database connection in background thread - DEPRECATED on Python 3.14"""
        try:
            print("[BG] Connecting to database...")
            self.db = DatabaseManager(**DB_CONFIG)
            
            # Connect with retry logic or just direct connect
            if self.db.connect():
                print("[BG] Database connected successfully")
                self.db_connected = True
                # self.load_data() - DO NOT CALL GUI UPDATE FROM BG THREAD
            else:
                print("[BG] Failed to connect to database")
                self.db_connected = False
        except Exception as e:
            print(f"[BG] Database connection error: {e}")
            self.db_connected = False
        finally:
            self.is_connecting = False


    def scale_ui(self):
        screen = self.geometry()
        w = screen.width()
        h = screen.height()
        scale_x = w / 480
        scale_y = h / 320
        
        sidebar_w = int(70 * scale_x)
        self.ui.verticalLayoutWidget.setGeometry(QRect(0, 0, sidebar_w, int(290 * scale_y)))
        
        content_x = sidebar_w + 5
        content_w = w - content_x - 5
        content_h = h - 30
        self.ui.stackedWidget.setGeometry(QRect(content_x, 0, content_w, content_h))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_ui()

    def show_home(self): self.switch_page(self.ui.HOME)
    def show_control(self): self.switch_page(self.ui.CONTROL)
    def show_report(self): 
        self.switch_page(self.ui.REPORT)
        self.update_report_page()
    def show_setup(self): self.switch_page(self.ui.page)
    
    def switch_page(self, page):
        self.ui.stackedWidget.setCurrentWidget(page)
        self.update_nav_buttons()

    def update_nav_buttons(self):
        current = self.ui.stackedWidget.currentWidget()
        buttons = [self.ui.pushButton_2, self.ui.pushButton_3, 
                   self.ui.pushButton, self.ui.pushButton_4]
        pages = [self.ui.HOME, self.ui.CONTROL, self.ui.REPORT, self.ui.page]
        
        for btn, page in zip(buttons, pages):
            if current == page:
                btn.setStyleSheet(self.ui.menuButtonActiveStyle if hasattr(self.ui, 'menuButtonActiveStyle') else "")
            else:
                btn.setStyleSheet(self.ui.menuButtonStyle if hasattr(self.ui, 'menuButtonStyle') else "")

    # ==================== DATA LOADING ====================
    
    def load_data(self):
        """Load all data from database"""
        if not self.db_connected:
            return
        
        # Load pending devices
        self.pending_devices = self.db.get_pending_devices()
        print(f"[INFO] Loaded {len(self.pending_devices)} devices from pending_commands")
        
        # Load settings
        self.settings = self.db.get_settings()
        print(f"[INFO] Loaded settings: Warning={self.settings['threshold_warning']}W")
        
        # Set current slave if devices exist
        if self.pending_devices:
            self.current_slave_id = self.pending_devices[0]['slave_id']
            self.update_control_display()
        
        # Update all displays
        self.update_home_display()
        self.update_setup_display()

    # ==================== CONTROL PAGE ====================
    
    def setup_control_page(self):
        """Initialize control page UI"""
        # Ẩn phần công suất device vì không cần dùng
        if hasattr(self.ui, 'device1PowerLabel'):
            self.ui.device1PowerLabel.hide()
        if hasattr(self.ui, 'device1PowerInput'):
            self.ui.device1PowerInput.hide()
        if hasattr(self.ui, 'device2PowerLabel'):
            self.ui.device2PowerLabel.hide()
        if hasattr(self.ui, 'device2PowerInput'):
            self.ui.device2PowerInput.hide()
    
    def update_control_display(self):
        """Update control page with current slave device info"""
        if not self.pending_devices or self.current_slave_index >= len(self.pending_devices):
            return
        
        device = self.pending_devices[self.current_slave_index]
        self.current_slave_id = device['slave_id']
        
        # Update slave ID label
        self.ui.name_ctl_3.setText(f"Slave {device['slave_id']}")
        
        # Update device0 (typically device ID 0)
        self.ui.label_8.setText("Device 0")
        self.update_device_ui(0, device['device0'])
        
        # Update device1 (typically device ID 1)
        self.ui.label_9.setText("Device 1")
        self.update_device_ui(1, device['device1'])
        
        # Update power and energy display if available
        sensor_data = self.db.get_latest_sensor_data(device['slave_id']) if self.db_connected else {}
        power = sensor_data.get('power', 0)
        energy = sensor_data.get('energy', 0)
        self.ui.roomPowerValue.setText(f"{power} W")
        self.ui.roomEnergyValue.setText(f"{energy / 100:.2f} kWh")
    
    def prev_slave(self):
        if not self.pending_devices:
            return
        self.current_slave_index = (self.current_slave_index - 1) % len(self.pending_devices)
        self.update_control_display()

    def next_slave(self):
        if not self.pending_devices:
            return
        self.current_slave_index = (self.current_slave_index + 1) % len(self.pending_devices)
        self.update_control_display()

    # --- Device Control Logic ---
    def toggle_device1(self):
        """Toggle device0 state"""
        if not self.db_connected or self.current_slave_id is None:
            return
        
        device = self.pending_devices[self.current_slave_index]
        new_state = 0 if device['device0'] == 1 else 1
        
        # Update database
        if self.db.update_device_command(self.current_slave_id, device0=new_state):
            print(f"[INFO] Updated Slave {self.current_slave_id} device0 to {new_state}")
            device['device0'] = new_state
            self.update_device_ui(0, new_state)

    def toggle_device2(self):
        """Toggle device1 state"""
        if not self.db_connected or self.current_slave_id is None:
            return
        
        device = self.pending_devices[self.current_slave_index]
        new_state = 0 if device['device1'] == 1 else 1
        
        # Update database
        if self.db.update_device_command(self.current_slave_id, device1=new_state):
            print(f"[INFO] Updated Slave {self.current_slave_id} device1 to {new_state}")
            device['device1'] = new_state
            self.update_device_ui(1, new_state)

    def update_device_ui(self, device_idx, state):
        """Update device button and status UI"""
        is_on = (state == 1)
        
        if device_idx == 0:
            btn, lbl = self.ui.pushButton_5, self.ui.device1Status
        else:
            btn, lbl = self.ui.pushButton_6, self.ui.device2Status
            
        if is_on:
            btn.setText("ON")
            btn.setStyleSheet("background-color: #2ecc71; color: white; border: none; border-radius: 15px; font-weight: bold;")
            lbl.setText("ON")
            lbl.setStyleSheet("color: #2ecc71; font-weight: bold;")
        else:
            btn.setText("OFF")
            btn.setStyleSheet("background-color: #e74c3c; color: white; border: none; border-radius: 15px; font-weight: bold;")
            lbl.setText("OFF")
            lbl.setStyleSheet("color: #e74c3c; font-weight: bold;")

    # ==================== REPORT PAGE ====================
    
    def setup_report_page(self):
        """Initialize report page with line chart and slave selector"""
        try:
            # Ẩn pieWidget vì không dùng
            if hasattr(self.ui, 'pieWidget'):
                self.ui.pieWidget.hide()
            
            # Mở rộng bảng để chiếm không gian pieWidget
            if hasattr(self.ui, 'REPORTTB'):
                self.ui.REPORTTB.setGeometry(210, 22, 195, 248)
                self.ui.REPORTTB.setColumnCount(2)
                self.ui.REPORTTB.setHorizontalHeaderLabels(["Thời gian", "Công suất"])
                self.ui.REPORTTB.setColumnWidth(0, 95)
                self.ui.REPORTTB.setColumnWidth(1, 80)
                self.ui.REPORTTB.verticalHeader().setVisible(False)
            
            # Create line chart
            print("[DEBUG] Creating line chart...")
            self.line_chart = PowerLineChart(self.ui.chartWidget)
            self.line_chart.setGeometry(0, 0, self.ui.chartWidget.width(), self.ui.chartWidget.height())
            print("[DEBUG] Line chart created")
        except Exception as e:
            print(f"[ERROR] Failed to create line chart: {e}")
        
    def update_report_page(self):
        """Update report page with power data"""
        if not self.db_connected:
            return
        
        # Get available slaves
        all_slaves = self.db.get_all_slaves()
        
        if not all_slaves:
            print("[WARN] No slaves found in modbus_data")
            return
        
        # Use first slave if none selected
        if self.selected_report_slave_id is None:
            self.selected_report_slave_id = all_slaves[0]
        
        # Load power data for selected slave (reg 40002 = Power)
        power_data = self.db.get_power_data(self.selected_report_slave_id, reg=40002, hours=24)
        
        print(f"[INFO] Loaded {len(power_data)} power data points for slave {self.selected_report_slave_id}")
        
        # Update line chart
        self.line_chart.set_data(power_data)
        
        # Update table with latest data
        self.update_report_table(power_data)
        
        # Update total power
        if power_data:
            total_power = sum(d['value'] for d in power_data)
            avg_power = total_power // len(power_data)
            max_power = max(d['value'] for d in power_data)
            self.ui.totalPowerLabel.setText(f"TB: {avg_power}W | Max: {max_power}W")
        else:
            self.ui.totalPowerLabel.setText("Không có dữ liệu")
    
    def update_report_table(self, power_data):
        """Update REPORTTB with power consumption summary"""
        if not power_data:
            self.ui.REPORTTB.setRowCount(0)
            return
        
        # Show last 15 data points in table (newest first)
        display_data = power_data[-15:][::-1] if len(power_data) > 15 else power_data[::-1]
        
        self.ui.REPORTTB.setRowCount(len(display_data))
        
        for i, data_point in enumerate(display_data):
            ts = data_point['ts']
            value = data_point['value']
            
            # Format timestamp
            if hasattr(ts, 'strftime'):
                time_str = ts.strftime("%H:%M:%S")
            else:
                time_str = str(ts)
            
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            
            value_item = QTableWidgetItem(f"{value} W")
            value_item.setTextAlignment(Qt.AlignCenter)
            
            # Highlight high values
            if value > 100:
                value_item.setForeground(QColor("#f39c12"))
            elif value > 200:
                value_item.setForeground(QColor("#e74c3c"))
            else:
                value_item.setForeground(QColor("#2ecc71"))
            
            self.ui.REPORTTB.setItem(i, 0, time_item)
            self.ui.REPORTTB.setItem(i, 1, value_item)

    # ==================== SETUP PAGE ====================
    
    def setup_setup_page(self):
        """Initialize setup page UI for tier prices and thresholds"""
        try:
            # Connect save buttons
            if hasattr(self.ui, 'saveThresholdBtn'):
                self.ui.saveThresholdBtn.clicked.connect(self.save_settings)
                print("[DEBUG] saveThresholdBtn connected")
            else:
                print("[WARN] saveThresholdBtn not found in UI")
            
            if hasattr(self.ui, 'saveTierBtn'):
                self.ui.saveTierBtn.clicked.connect(self.save_settings)
                print("[DEBUG] saveTierBtn connected")
            else:
                print("[WARN] saveTierBtn not found in UI")
        except Exception as e:
            print(f"[ERROR] Failed to setup setup page: {e}")
    
    def update_setup_display(self):
        """Load settings into UI"""
        if not self.settings:
            return
        
        # Update threshold inputs
        if hasattr(self.ui, 'warningThresholdInput'):
            self.ui.warningThresholdInput.setValue(self.settings.get('threshold_warning', 500))
        
        if hasattr(self.ui, 'criticalThresholdInput'):
            self.ui.criticalThresholdInput.setValue(self.settings.get('threshold_critical', 1000))
        
        # Update tier prices (6 prices) - sử dụng tierInputs list từ gui_pi.py
        tier_prices = self.settings.get('tier_prices', [1984, 2050, 2380, 2998, 3350, 3460])
        if hasattr(self.ui, 'tierInputs') and self.ui.tierInputs:
            for i, spin in enumerate(self.ui.tierInputs):
                if i < len(tier_prices):
                    spin.setValue(tier_prices[i])
        
        # Update VAT
        if hasattr(self.ui, 'vatInput'):
            self.ui.vatInput.setValue(self.settings.get('vat', 8))
    
    def save_settings(self):
        """Save settings from UI to database"""
        if not self.db_connected:
            return
        
        new_settings = {}
        
        # Read thresholds
        if hasattr(self.ui, 'warningThresholdInput'):
            new_settings['threshold_warning'] = self.ui.warningThresholdInput.value()
        
        if hasattr(self.ui, 'criticalThresholdInput'):
            new_settings['threshold_critical'] = self.ui.criticalThresholdInput.value()
        
        # Read tier prices từ tierInputs list
        tier_prices = []
        if hasattr(self.ui, 'tierInputs') and self.ui.tierInputs:
            for spin in self.ui.tierInputs:
                tier_prices.append(spin.value())
        
        if tier_prices:
            new_settings['tier_prices'] = tier_prices
        
        # Read VAT
        if hasattr(self.ui, 'vatInput'):
            new_settings['vat'] = self.ui.vatInput.value()
        
        # Update database
        if self.db.update_settings(new_settings):
            print("[INFO] Settings saved successfully")
            self.settings.update(new_settings)
            
            # Show feedback
            if hasattr(self.ui, 'saveThresholdBtn'):
                self.ui.saveThresholdBtn.setText("✓ Đã lưu")
                QTimer.singleShot(1500, lambda: self.ui.saveThresholdBtn.setText("Lưu cài đặt"))

    # ==================== HOME PAGE ====================
    
    def update_home_display(self):
        """Update home page with system overview"""
        if not self.db_connected:
            return
        
        # Calculate total power from all slaves
        total_power = 0
        
        for device in self.pending_devices:
            sensor_data = self.db.get_latest_sensor_data(device['slave_id'])
            total_power += sensor_data.get('power', 0)
        
        # Update total power label
        if hasattr(self.ui, 'totalPowerLabel'):
            self.ui.totalPowerLabel.setText(f"Tổng: {total_power} W")
        
        # Update warning status
        warning_threshold = self.settings.get('threshold_warning', 500)
        critical_threshold = self.settings.get('threshold_critical', 1000)
        
        if hasattr(self.ui, 'warningLabel'):
            if total_power >= critical_threshold:
                # Update status label
                self.ui.warningLabel.setText(f"⚠ NGUY HIỂM: {total_power}W")
                self.ui.warningLabel.setStyleSheet("color: #e74c3c; font-weight: bold;")
                
                # Show overlay
                style = """
                    QLabel {
                        background-color: rgba(231, 76, 60, 0.9);
                        color: white;
                        border-radius: 10px;
                        padding: 20px 40px;
                        border: 2px solid #c0392b;
                    }
                """
                self.alert_overlay.show_message(f"⚠️ CẢNH BÁO NGUY HIỂM\nQUÁ TẢI: {total_power}W", style)
                
            elif total_power >= warning_threshold:
                # Update status label
                self.ui.warningLabel.setText(f"⚠ CẢNH BÁO: {total_power}W")
                self.ui.warningLabel.setStyleSheet("color: #f39c12; font-weight: bold;")
                
                # Show overlay
                style = """
                    QLabel {
                        background-color: rgba(243, 156, 18, 0.9);
                        color: white;
                        border-radius: 10px;
                        padding: 20px 40px;
                        border: 2px solid #d35400;
                    }
                """
                self.alert_overlay.show_message(f"⚠️ CẢNH BÁO TIÊU THỤ CAO\nCÔNG SUẤT: {total_power}W", style)
            else:
                self.ui.warningLabel.setText("✓ Bình thường")
                self.ui.warningLabel.setStyleSheet("color: #2ecc71; font-weight: bold;")
                self.alert_overlay.hide()

    # ==================== PERIODIC UPDATE ====================

    def update_status(self):
        """Periodic status update"""
        now = QDateTime.currentDateTime().toString("hh:mm:ss dd/MM")

        if not self.db_connected:
            self.statusBar().showMessage(f" {now} | Đang kết nối DB...")
            # Thử kết nối lại nếu chưa kết nối
            self.retry_db_connection()
            return
        
        try:
            # Reload data from database
            self.pending_devices = self.db.get_pending_devices()
            
            # Update displays based on current page
            current_page = self.ui.stackedWidget.currentWidget()
            
            if current_page == self.ui.HOME:
                self.update_home_display()
            elif current_page == self.ui.CONTROL:
                self.update_control_display()
            elif current_page == self.ui.REPORT:
                self.update_report_page()
            
            # Update status bar
            device_count = len(self.pending_devices)
            self.statusBar().showMessage(f" {now} | {device_count} Devices | DB Connected")
        except Exception as e:
            print(f"[ERROR] Update loop failed: {e}")
            self.db_connected = False # Assume DB lost

    def closeEvent(self, event):
        """Cleanup on close"""
        if self.db_connected and self.db:
            self.db.disconnect()
        show_taskbar()
        QApplication.restoreOverrideCursor()
        event.accept()

if __name__ == '__main__':
    try:
        print("[MAIN] Starting application...")
        app = QApplication(sys.argv)
        print("[MAIN] QApplication created")
        
        print("[MAIN] Creating MainWindow...")
        window = MainWindow()
        print("[MAIN] MainWindow created successfully")
        
        print("[MAIN] Showing window...")
        window.show()
        print("[MAIN] Window shown. Entering event loop...")
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"[MAIN ERROR] Application failed: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
