"""Test basic PyQt5 window"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Window")
        self.resize(400, 300)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Label
        self.label = QLabel("Hello World!")
        layout.addWidget(self.label)
        
        # Button
        btn = QPushButton("Click Me")
        btn.clicked.connect(self.on_click)
        layout.addWidget(btn)
        
        # Timer
        self.counter = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(1000)
        
        print("Window initialized!")
    
    def on_click(self):
        print("Button clicked!")
        self.label.setText("Button was clicked!")
    
    def on_timer(self):
        self.counter += 1
        print(f"Timer tick: {self.counter}")
        self.statusBar().showMessage(f"Counter: {self.counter}")

if __name__ == '__main__':
    print("Starting test app...")
    app = QApplication(sys.argv)
    print("QApplication created")
    
    window = TestWindow()
    print("Window created")
    
    window.show()
    print("Window shown, entering event loop...")
    
    ret = app.exec_()
    print(f"Event loop exited with code: {ret}")
    sys.exit(ret)
