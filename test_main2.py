"""Test main window with line chart"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QRect
from gui_pi import Ui_MainWindow
from line_chart import PowerLineChart

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
        
        # Buttons
        self.ui.pushButton_2.clicked.connect(lambda: self.switch_page(self.ui.HOME))
        self.ui.pushButton_3.clicked.connect(lambda: self.switch_page(self.ui.CONTROL))
        self.ui.pushButton.clicked.connect(lambda: self.switch_page(self.ui.REPORT))
        self.ui.pushButton_4.clicked.connect(lambda: self.switch_page(self.ui.page))
        self.ui.exit.clicked.connect(self.close)
        
        # Line chart
        print("[DEBUG] Creating line chart...")
        try:
            self.line_chart = PowerLineChart(self.ui.chartWidget)
            self.line_chart.setGeometry(0, 0, self.ui.chartWidget.width(), self.ui.chartWidget.height())
            print("[DEBUG] Line chart created OK")
        except Exception as e:
            print(f"[ERROR] Line chart failed: {e}")
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(2000)
        
        self.ui.stackedWidget.setCurrentWidget(self.ui.HOME)
        print("[DEBUG] Init complete!")
    
    def switch_page(self, page):
        self.ui.stackedWidget.setCurrentWidget(page)
        print(f"Switched to {page.objectName()}")
    
    def on_timer(self):
        from PyQt5.QtCore import QDateTime
        now = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.statusBar().showMessage(f"Time: {now}")

if __name__ == '__main__':
    print("[MAIN] Starting...")
    app = QApplication(sys.argv)
    window = TestMainWindow()
    window.show()
    print("[MAIN] Entering event loop...")
    sys.exit(app.exec_())
