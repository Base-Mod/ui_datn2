"""Test main window without database"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QCursor
from gui_pi import Ui_MainWindow

# Simple stylesheet
STYLESHEET = """
QMainWindow { background-color: #0d1b2a; }
QWidget { background-color: #0d1b2a; color: #e0e1dd; }
"""

class TestMainWindow(QMainWindow):
    def __init__(self):
        print("[DEBUG] TestMainWindow init started")
        super().__init__()
        
        print("[DEBUG] Setting up UI...")
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        print("[DEBUG] UI setup complete")
        
        self.setStyleSheet(STYLESHEET)
        self.setWindowTitle("Test Power Management")
        self.resize(480, 320)
        print("[DEBUG] Window setup complete")
        
        # Connect navigation buttons
        print("[DEBUG] Connecting buttons...")
        self.ui.pushButton_2.clicked.connect(lambda: print("HOME clicked"))
        self.ui.pushButton_3.clicked.connect(lambda: print("CONTROL clicked"))
        self.ui.pushButton.clicked.connect(lambda: print("REPORT clicked"))
        self.ui.pushButton_4.clicked.connect(lambda: print("SETUP clicked"))
        self.ui.exit.clicked.connect(self.close)
        print("[DEBUG] Buttons connected")
        
        # Timer
        print("[DEBUG] Starting timer...")
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(2000)
        print("[DEBUG] Timer started")
        
        self.ui.stackedWidget.setCurrentWidget(self.ui.HOME)
        print("[DEBUG] TestMainWindow init complete!")
    
    def on_timer(self):
        from PyQt5.QtCore import QDateTime
        now = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.statusBar().showMessage(f"Time: {now}")
        print(f"[TIMER] {now}")

if __name__ == '__main__':
    print("[MAIN] Starting test...")
    app = QApplication(sys.argv)
    print("[MAIN] QApplication created")
    
    window = TestMainWindow()
    print("[MAIN] Window created")
    
    window.show()
    print("[MAIN] Window shown, entering event loop...")
    
    ret = app.exec_()
    print(f"[MAIN] Exited with code: {ret}")
    sys.exit(ret)
