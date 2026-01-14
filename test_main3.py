"""Test main window with threading"""
import sys
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer
from gui_pi import Ui_MainWindow
from line_chart import PowerLineChart
from db_manager import DatabaseManager

DB_CONFIG = {
    "host": "47.128.66.94",
    "user": "root",
    "password": "fbd3b9f31da4a89d",
    "database": "power_management"
}

STYLESHEET = """
QMainWindow { background-color: #0d1b2a; }
QWidget { background-color: #0d1b2a; color: #e0e1dd; }
"""

class TestMainWindow(QMainWindow):
    def __init__(self):
        print("[DEBUG] Init started")
        super().__init__()
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setStyleSheet(STYLESHEET)
        self.setWindowTitle("Test Power Management")
        self.resize(480, 320)
        
        # Database
        self.db = None
        self.db_connected = False
        self.is_connecting = True
        
        print("[DEBUG] Starting db thread...")
        self.db_thread = threading.Thread(target=self.connect_db)
        self.db_thread.daemon = True
        self.db_thread.start()
        print("[DEBUG] DB thread started")
        
        # Buttons
        self.ui.pushButton_2.clicked.connect(lambda: self.switch_page(self.ui.HOME))
        self.ui.pushButton_3.clicked.connect(lambda: self.switch_page(self.ui.CONTROL))
        self.ui.pushButton.clicked.connect(lambda: self.switch_page(self.ui.REPORT))
        self.ui.pushButton_4.clicked.connect(lambda: self.switch_page(self.ui.page))
        self.ui.exit.clicked.connect(self.close)
        
        # Line chart
        self.line_chart = PowerLineChart(self.ui.chartWidget)
        self.line_chart.setGeometry(0, 0, self.ui.chartWidget.width(), self.ui.chartWidget.height())
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(2000)
        
        self.ui.stackedWidget.setCurrentWidget(self.ui.HOME)
        print("[DEBUG] Init complete!")
    
    def connect_db(self):
        try:
            print("[BG] Connecting to database...")
            self.db = DatabaseManager(**DB_CONFIG)
            if self.db.connect():
                print("[BG] Database connected successfully")
                self.db_connected = True
            else:
                print("[BG] Failed to connect")
        except Exception as e:
            print(f"[BG] Error: {e}")
        finally:
            self.is_connecting = False
    
    def switch_page(self, page):
        self.ui.stackedWidget.setCurrentWidget(page)
    
    def on_timer(self):
        from PyQt5.QtCore import QDateTime
        now = QDateTime.currentDateTime().toString("hh:mm:ss")
        
        if self.is_connecting:
            self.statusBar().showMessage(f"{now} | Connecting...")
        elif self.db_connected:
            self.statusBar().showMessage(f"{now} | DB Connected")
        else:
            self.statusBar().showMessage(f"{now} | DB Failed")

if __name__ == '__main__':
    print("[MAIN] Starting...")
    app = QApplication(sys.argv)
    window = TestMainWindow()
    window.show()
    print("[MAIN] Entering event loop...")
    sys.exit(app.exec_())
