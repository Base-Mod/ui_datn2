"""
Custom Line Chart Widget for Power Consumption Over Time
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QBrush, QPen, QLinearGradient
from datetime import datetime


class PowerLineChart(QWidget):
    """Line chart for displaying power consumption over time"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # [(timestamp, power_value), ...]
        self.line_color = QColor("#00d4ff")
        self.fill_color = QColor("#00d4ff")
        self.fill_color.setAlpha(50)
        self.setAutoFillBackground(True)
        self.max_points = 100  # Limit displayed points for performance
        
    def set_data(self, data):
        """
        Set chart data
        Args:
            data: List of tuples [(timestamp, value), ...] or dicts [{'ts': datetime, 'value': int}, ...]
        """
        if not data:
            self.data = []
            self.update()
            return
        
        # Convert to standardized format if needed
        if isinstance(data[0], dict):
            self.data = [(d['ts'], d['value']) for d in data]
        else:
            self.data = data
        
        # Limit number of points for performance
        if len(self.data) > self.max_points:
            step = len(self.data) // self.max_points
            self.data = self.data[::step]
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Draw title
        painter.setPen(QPen(QColor("#778da9")))
        painter.setFont(QFont("Arial", 7, QFont.Bold))
        painter.drawText(0, 3, w, 14, Qt.AlignCenter, "CÔNG SUẤT THEO THỜI GIAN")
        
        if not self.data or len(self.data) < 2:
            painter.setPen(QPen(QColor("#778da9")))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(0, 20, w, h-20, Qt.AlignCenter, 
                           "Không có dữ liệu" if not self.data else "Cần ít nhất 2 điểm")
            return
        
        # Chart area margins
        margin_top = 25
        margin_bottom = 30
        margin_left = 35
        margin_right = 10
        
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom
        
        if chart_w <= 0 or chart_h <= 0:
            return
        
        # Find min/max values
        values = [v for _, v in self.data]
        min_val = min(values)
        max_val = max(values)
        
        # Add some padding to the range
        val_range = max_val - min_val
        if val_range == 0:
            val_range = max_val * 0.1 if max_val > 0 else 10
        
        min_val = max(0, min_val - val_range * 0.1)
        max_val = max_val + val_range * 0.1
        val_range = max_val - min_val
        
        # Draw Y-axis labels (power values)
        painter.setPen(QPen(QColor("#778da9")))
        painter.setFont(QFont("Arial", 6))
        
        num_y_labels = 5
        for i in range(num_y_labels):
            val = min_val + (val_range * i / (num_y_labels - 1))
            y = margin_top + chart_h - (chart_h * i / (num_y_labels - 1))
            
            # Draw grid line
            painter.setPen(QPen(QColor("#1b263b"), 1, Qt.DotLine))
            painter.drawLine(margin_left, int(y), margin_left + chart_w, int(y))
            
            # Draw label
            painter.setPen(QPen(QColor("#778da9")))
            painter.drawText(0, int(y) - 6, margin_left - 3, 12, 
                           Qt.AlignRight | Qt.AlignVCenter, f"{int(val)}W")
        
        # Convert data points to screen coordinates
        points = []
        for i, (ts, value) in enumerate(self.data):
            x = margin_left + (i / (len(self.data) - 1)) * chart_w
            y = margin_top + chart_h - ((value - min_val) / val_range * chart_h)
            points.append((x, y))
        
        # Draw filled area under the line
        gradient = QLinearGradient(0, margin_top, 0, margin_top + chart_h)
        gradient.setColorAt(0, self.fill_color)
        gradient.setColorAt(1, QColor("#0d1b2a"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        
        # Create polygon for filled area
        from PyQt5.QtGui import QPolygonF
        from PyQt5.QtCore import QPointF
        
        polygon = QPolygonF()
        polygon.append(QPointF(margin_left, margin_top + chart_h))  # Bottom left
        
        for x, y in points:
            polygon.append(QPointF(x, y))
        
        polygon.append(QPointF(margin_left + chart_w, margin_top + chart_h))  # Bottom right
        painter.drawPolygon(polygon)
        
        # Draw the line
        painter.setPen(QPen(self.line_color, 2))
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # Draw data points
        painter.setBrush(QBrush(self.line_color))
        painter.setPen(QPen(QColor("#0d1b2a"), 1))
        for x, y in points:
            painter.drawEllipse(int(x) - 2, int(y) - 2, 4, 4)
        
        # Draw X-axis labels (time)
        painter.setPen(QPen(QColor("#778da9")))
        painter.setFont(QFont("Arial", 6))
        
        num_x_labels = min(6, len(self.data))
        for i in range(num_x_labels):
            idx = int(i * (len(self.data) - 1) / (num_x_labels - 1)) if num_x_labels > 1 else 0
            ts, _ = self.data[idx]
            
            # Format timestamp
            if isinstance(ts, datetime):
                time_str = ts.strftime("%H:%M")
            elif isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M")
                except:
                    time_str = ts[:5]  # First 5 chars
            else:
                time_str = str(ts)[:5]
            
            x = margin_left + (idx / (len(self.data) - 1)) * chart_w if len(self.data) > 1 else margin_left
            painter.drawText(int(x) - 20, margin_top + chart_h + 2, 40, 15, 
                           Qt.AlignCenter, time_str)
        
        # Draw current value indicator
        if points:
            last_x, last_y = points[-1]
            last_val = self.data[-1][1]
            
            # Draw indicator box
            box_w = 50
            box_h = 16
            box_x = last_x - box_w // 2
            box_y = last_y - box_h - 8
            
            # Ensure box stays within bounds
            if box_x < margin_left:
                box_x = margin_left
            if box_x + box_w > w - margin_right:
                box_x = w - margin_right - box_w
            
            painter.setBrush(QBrush(QColor("#1b263b")))
            painter.setPen(QPen(self.line_color, 1))
            painter.drawRoundedRect(int(box_x), int(box_y), box_w, box_h, 4, 4)
            
            painter.setPen(QPen(QColor("#e0e1dd")))
            painter.setFont(QFont("Arial", 7, QFont.Bold))
            painter.drawText(int(box_x), int(box_y), box_w, box_h, 
                           Qt.AlignCenter, f"{int(last_val)}W")
