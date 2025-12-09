# -*- coding: utf-8 -*-
"""
Configuration for Power Management System
"""

# Modbus Configuration
MODBUS_CONFIG = {
    'port': '/dev/ttyUSB0',  # Serial port for RS485
    'baudrate': 9600,
    'parity': 'N',
    'stopbits': 1,
    'bytesize': 8,
    'timeout': 1
}

# Room Configuration - Expandable
# Each room has: name, modbus_address, devices list
ROOMS = [
    {
        'id': 1,
        'name': 'Phòng 1',
        'modbus_addr': 1,
        'devices': [
            {'id': 0, 'name': 'Đèn', 'register': 0, 'power': 15},
            {'id': 1, 'name': 'Quạt', 'register': 1, 'power': 45},
        ]
    },
    {
        'id': 2,
        'name': 'Phòng 2', 
        'modbus_addr': 2,
        'devices': [
            {'id': 0, 'name': 'Đèn', 'register': 0, 'power': 12},
            {'id': 1, 'name': 'Điều hòa', 'register': 1, 'power': 850},
        ]
    },
    {
        'id': 3,
        'name': 'Phòng 3',
        'modbus_addr': 3,
        'devices': [
            {'id': 0, 'name': 'Đèn', 'register': 0, 'power': 18},
            {'id': 1, 'name': 'Quạt', 'register': 1, 'power': 50},
        ]
    },
    {
        'id': 4,
        'name': 'Phòng 4',
        'modbus_addr': 4,
        'devices': [
            {'id': 0, 'name': 'Đèn', 'register': 0, 'power': 15},
            {'id': 1, 'name': 'Điều hòa', 'register': 1, 'power': 900},
        ]
    },
]

# Vietnamese Electricity Tiered Pricing (VND/kWh) - 2024
# Bậc thang giá điện sinh hoạt
ELECTRICITY_TIERS = [
    {'tier': 1, 'from': 0, 'to': 50, 'price': 1893, 'name': 'Bậc 1 (0-50 kWh)'},
    {'tier': 2, 'from': 51, 'to': 100, 'price': 1956, 'name': 'Bậc 2 (51-100 kWh)'},
    {'tier': 3, 'from': 101, 'to': 200, 'price': 2271, 'name': 'Bậc 3 (101-200 kWh)'},
    {'tier': 4, 'from': 201, 'to': 300, 'price': 2860, 'name': 'Bậc 4 (201-300 kWh)'},
    {'tier': 5, 'from': 301, 'to': 400, 'price': 3197, 'name': 'Bậc 5 (301-400 kWh)'},
    {'tier': 6, 'from': 401, 'to': float('inf'), 'price': 3302, 'name': 'Bậc 6 (>400 kWh)'},
]

# VAT Rate
VAT_RATE = 0.08  # 8%

# Power Threshold Settings (Watts)
POWER_THRESHOLDS = {
    'warning': 500,    # Warning threshold (W)
    'critical': 1000,  # Critical threshold (W)
}
