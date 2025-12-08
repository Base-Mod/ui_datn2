import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidgetItem, 
                               QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QColor, QFont
from gui_pi import Ui_MainWindow
from config import ROOMS
from modbus_handler import ModbusHandler
from electricity_calc import ElectricityCalculator, UsageTracker


# Professional Dark Theme Stylesheet for Power Management System (3.5" Pi Screen)
STYLESHEET = """
/* Main Window */
QMainWindow {
    background-color: #1a1a2e;
}

QWidget#centralwidget {
    background-color: #1a1a2e;
}

/* Sidebar Navigation Buttons */
QPushButton#pushButton_2, QPushButton#pushButton_3, 
QPushButton#pushButton, QPushButton#pushButton_4 {
    background-color: #16213e;
    color: #eee;
    border: none;
    border-radius: 5px;
    padding: 8px;
    font-size: 8px;
    font-weight: bold;
    text-align: center;
    margin: 2px 3px;
}

QPushButton#pushButton_2:hover, QPushButton#pushButton_3:hover,
QPushButton#pushButton:hover, QPushButton#pushButton_4:hover {
    background-color: #0f3460;
}

QPushButton#pushButton_2:checked, QPushButton#pushButton_3:checked,
QPushButton#pushButton:checked, QPushButton#pushButton_4:checked,
QPushButton#pushButton_2:pressed, QPushButton#pushButton_3:pressed,
QPushButton#pushButton:pressed, QPushButton#pushButton_4:pressed {
    background-color: #e94560;
}

/* Stacked Widget Pages */
QStackedWidget {
    background-color: #16213e;
    border-radius: 10px;
}

QWidget#HOME, QWidget#CONTROL, QWidget#REPORT, QWidget#page {
    background-color: #16213e;
    border-radius: 10px;
}

/* Labels */
QLabel {
    color: #eee;
}

/* Exit Button */
QPushButton#exit {
    background-color: #e94560;
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 10px;
    font-weight: bold;
}

QPushButton#exit:hover {
    background-color: #ff6b6b;
}

/* Device Control Buttons */
QPushButton#pushButton_5, QPushButton#pushButton_6 {
    background-color: #0f3460;
    color: #eee;
    border: 2px solid #e94560;
    border-radius: 15px;
    font-size: 10px;
    font-weight: bold;
    padding: 5px 15px;
}

QPushButton#pushButton_5:hover, QPushButton#pushButton_6:hover {
    background-color: #e94560;
}

/* Next Button */
QPushButton#pushButton_7 {
    background-color: #0f3460;
    color: #eee;
    border: 1px solid #e94560;
    border-radius: 4px;
    font-size: 8px;
    font-weight: bold;
}

QPushButton#pushButton_7:hover {
    background-color: #e94560;
}

/* Table Widget */
QTableWidget {
    background-color: #1a1a2e;
    color: #eee;
    border: 1px solid #0f3460;
    border-radius: 5px;
    gridline-color: #0f3460;
    font-size: 9px;
}

QTableWidget::item {
    padding: 4px;
    border-bottom: 1px solid #0f3460;
}

QTableWidget::item:selected {
    background-color: #e94560;
}

QHeaderView::section {
    background-color: #0f3460;
    color: #eee;
    padding: 5px;
    border: none;
    font-weight: bold;
    font-size: 8px;
}

/* Menu Bar - Hidden for small screen */
QMenuBar {
    background-color: #1a1a2e;
    color: #eee;
    max-height: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #1a1a2e;
    color: #00d9ff;
    font-size: 8px;
    max-height: 18px;
}

/* Scrollbar */
QScrollBar:vertical {
    background-color: #1a1a2e;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #0f3460;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #e94560;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Apply professional stylesheet
        self.setStyleSheet(STYLESHEET)
        
        # Set window properties for 3.5" Pi screen
        self.setWindowTitle("Power Management System")
        self.setFixedSize(480, 320)
        self.setWindowFlags(Qt.FramelessWindowHint)  # Fullscreen borderless for Pi
        
        # Initialize Modbus handler
        self.modbus = ModbusHandler()
        self.modbus.connect()
        
        # Initialize electricity calculator
        self.calculator = ElectricityCalculator()
        self.tracker = UsageTracker()
        
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
        
        # Setup status bar with time
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)
        
        # Initialize UI
        self.update_room_display()
        self.ui.stackedWidget.setCurrentWidget(self.ui.HOME)
        self.update_nav_buttons()
    
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
        # Reset all button styles
        buttons = [self.ui.pushButton_2, self.ui.pushButton_3, 
                   self.ui.pushButton, self.ui.pushButton_4]
        pages = [self.ui.HOME, self.ui.CONTROL, self.ui.REPORT, self.ui.page]
        
        for btn, page in zip(buttons, pages):
            if current == page:
                btn.setStyleSheet("background-color: #e94560; color: white;")
            else:
                btn.setStyleSheet("")
    
    def toggle_device1(self):
        room_id = self.current_room['id']
        device = self.current_room['devices'][0]
        
        success = self.modbus.toggle_device(room_id, device['id'])
        if success:
            state = self.modbus.get_device_state(room_id, device['id'])
            if state:
                self.ui.pushButton_5.setText("ON")
                self.ui.pushButton_5.setStyleSheet(
                    "background-color: #00c853; color: white; border: 2px solid #00c853;")
            else:
                self.ui.pushButton_5.setText("OFF")
                self.ui.pushButton_5.setStyleSheet(
                    "background-color: #e94560; color: white; border: 2px solid #e94560;")
    
    def toggle_device2(self):
        room_id = self.current_room['id']
        device = self.current_room['devices'][1]
        
        success = self.modbus.toggle_device(room_id, device['id'])
        if success:
            state = self.modbus.get_device_state(room_id, device['id'])
            if state:
                self.ui.pushButton_6.setText("ON")
                self.ui.pushButton_6.setStyleSheet(
                    "background-color: #00c853; color: white; border: 2px solid #00c853;")
            else:
                self.ui.pushButton_6.setText("OFF")
                self.ui.pushButton_6.setStyleSheet(
                    "background-color: #e94560; color: white; border: 2px solid #e94560;")
    
    def prev_room(self):
        self.current_room_index = (self.current_room_index - 1) % len(self.rooms)
        self.current_room = self.rooms[self.current_room_index]
        self.update_room_display()
    
    def next_room(self):
        self.current_room_index = (self.current_room_index + 1) % len(self.rooms)
        self.current_room = self.rooms[self.current_room_index]
        self.update_room_display()
    
    def update_room_display(self):
        """Update control page for current room"""
        room_id = self.current_room['id']
        self.ui.name_ctl_3.setText(str(room_id))
        
        # Update device labels
        devices = self.current_room['devices']
        if len(devices) >= 1:
            self.ui.label_8.setText(devices[0]['name'])
            state1 = self.modbus.get_device_state(room_id, devices[0]['id'])
            self.ui.pushButton_5.setText("ON" if state1 else "OFF")
            if state1:
                self.ui.pushButton_5.setStyleSheet(
                    "background-color: #00c853; color: white; border: 2px solid #00c853;")
            else:
                self.ui.pushButton_5.setStyleSheet("")
        
        if len(devices) >= 2:
            self.ui.label_9.setText(devices[1]['name'])
            state2 = self.modbus.get_device_state(room_id, devices[1]['id'])
            self.ui.pushButton_6.setText("ON" if state2 else "OFF")
            if state2:
                self.ui.pushButton_6.setStyleSheet(
                    "background-color: #00c853; color: white; border: 2px solid #00c853;")
            else:
                self.ui.pushButton_6.setStyleSheet("")
    
    def setup_report_table(self):
        # Setup table columns
        self.ui.REPORTTB.setColumnCount(4)
        self.ui.REPORTTB.setHorizontalHeaderLabels(
            ["Phòng", "Thiết bị", "Trạng thái", "P (W)"])
        
        # Set column widths
        header = self.ui.REPORTTB.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        self.update_report_table()
    
    def update_report_table(self):
        """Update report table with current device states"""
        # Count total rows needed
        total_rows = sum(len(room['devices']) for room in self.rooms)
        self.ui.REPORTTB.setRowCount(total_rows)
        
        row = 0
        for room in self.rooms:
            for device in room['devices']:
                state = self.modbus.get_device_state(room['id'], device['id'])
                power = device['power'] if state else 0
                
                self.ui.REPORTTB.setItem(row, 0, QTableWidgetItem(room['name']))
                self.ui.REPORTTB.setItem(row, 1, QTableWidgetItem(device['name']))
                
                status_item = QTableWidgetItem("ON" if state else "OFF")
                if state:
                    status_item.setForeground(QColor("#00c853"))
                else:
                    status_item.setForeground(QColor("#e94560"))
                self.ui.REPORTTB.setItem(row, 2, status_item)
                
                self.ui.REPORTTB.setItem(row, 3, QTableWidgetItem(str(power)))
                row += 1
    
    def update_status(self):
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss dd/MM")
        total_power = self.modbus.get_active_power()
        
        # Estimate monthly cost
        estimate = self.calculator.estimate_monthly_cost(total_power)
        monthly_cost = estimate['estimated_cost'] / 1000  # Convert to thousands
        
        self.statusBar().showMessage(
            f" {current_time} | P: {total_power:.0f}W | ~{monthly_cost:.0f}k VNĐ/tháng")
        
        # Update report table periodically
        self.update_report_table()
    
    def closeEvent(self, event):
        """Clean up on close"""
        self.modbus.disconnect()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
