"""Test database connection"""
import mysql.connector
from db_manager import DatabaseManager

DB_CONFIG = {
    "host": "47.128.66.94",
    "user": "root",
    "password": "fbd3b9f31da4a89d",
    "database": "power_management"
}

print("Testing DatabaseManager...")
db = DatabaseManager(**DB_CONFIG)

if db.connect():
    print("✓ Database connected successfully!")
    
    # Test pending_commands
    devices = db.get_pending_devices()
    print(f"\n✓ Found {len(devices)} devices in pending_commands:")
    for d in devices:
        print(f"  - Slave {d['slave_id']}: device0={d['device0']}, device1={d['device1']}")
    
    # Test settings
    settings = db.get_settings()
    print(f"\n✓ Settings loaded:")
    print(f"  - Warning threshold: {settings.get('threshold_warning', 'N/A')}W")
    print(f"  - Critical threshold: {settings.get('threshold_critical', 'N/A')}W")
    
    # Test get_all_slaves
    slaves = db.get_all_slaves()
    print(f"\n✓ Found {len(slaves)} slaves in modbus_data: {slaves}")
    
    db.disconnect()
    print("\n✓ All tests passed!")
else:
    print("✗ Failed to connect to database")
