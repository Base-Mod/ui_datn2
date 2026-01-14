"""
Database Manager for Power Management System
Handles all MySQL database operations
"""
import pymysql
from pymysql import Error
from datetime import datetime, timedelta
import json


class DatabaseManager:
    def __init__(self, host, user, password, database):
        """Initialize database connection"""
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            print(f"[DB] Attempting connection to {self.host}...")
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                connect_timeout=10,
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"[DB] Connected to {self.database}")
            return True
        except Error as e:
            print(f"[DB ERROR] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("[DB] Disconnected")
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a SQL query"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                self.connection.commit()
                cursor.close()
                return True
        except Error as e:
            print(f"[DB ERROR] Query failed: {e}")
            print(f"[DB ERROR] Query: {query}")
            return None if fetch else False
    
    # ==================== PENDING COMMANDS ====================
    
    def get_pending_devices(self):
        """
        Get all devices from pending_commands table
        Returns: List of dicts with slave_id, device0, device1, sync
        """
        query = "SELECT slave_id, device0, device1, sync FROM pending_commands ORDER BY slave_id"
        return self.execute_query(query) or []
    
    def update_device_command(self, slave_id, device0=None, device1=None):
        """
        Update device command in pending_commands
        Sets sync=1 and updates change_token
        """
        updates = []
        params = []
        
        if device0 is not None:
            updates.append("device0 = %s")
            params.append(device0)
        
        if device1 is not None:
            updates.append("device1 = %s")
            params.append(device1)
        
        if not updates:
            return False
        
        updates.append("sync = 1")
        updates.append("change_token = NOW()")
        params.append(slave_id)
        
        query = f"UPDATE pending_commands SET {', '.join(updates)} WHERE slave_id = %s"
        return self.execute_query(query, tuple(params), fetch=False)
    
    # ==================== MODBUS DATA ====================
    
    def get_power_data(self, slave_id, reg=40002, hours=24):
        """
        Get power consumption data from modbus_data
        Args:
            slave_id: Slave device ID
            reg: Register number for power (default 40002)
            hours: Number of hours to look back
        Returns: List of dicts with ts, value
        """
        time_threshold = datetime.now() - timedelta(hours=hours)
        
        query = """
            SELECT ts, value 
            FROM modbus_data 
            WHERE slave_id = %s AND reg = %s AND ts >= %s
            ORDER BY ts ASC
        """
        return self.execute_query(query, (slave_id, reg, time_threshold)) or []
    
    def get_latest_sensor_data(self, slave_id):
        """
        Get latest sensor readings for a slave
        Returns dict with voltage, current, power, energy, etc.
        Mapping: reg 40001=voltage, 40002=power (W), 40003=energy (kWh)
        """
        query = """
            SELECT reg, value, ts 
            FROM modbus_data 
            WHERE slave_id = %s AND ts >= NOW() - INTERVAL 5 MINUTE
            ORDER BY ts DESC
        """
        rows = self.execute_query(query, (slave_id,))
        
        if not rows:
            return {}
        
        # Get the most recent value for each register
        data = {}
        seen_regs = set()
        
        for row in rows:
            reg = row['reg']
            if reg not in seen_regs:
                data[f"reg_{reg}"] = row['value']
                seen_regs.add(reg)
        
        # Map to common names: 40001=voltage, 40002=power(W), 40003=energy(kWh)
        result = {
            'voltage': data.get('reg_40001', 0),
            'power': data.get('reg_40002', 0),
            'energy': data.get('reg_40003', 0),
        }
        
        return result
    
    def get_all_slaves(self):
        """Get list of all unique slave_ids from modbus_data"""
        query = "SELECT DISTINCT slave_id FROM modbus_data ORDER BY slave_id"
        result = self.execute_query(query)
        return [row['slave_id'] for row in result] if result else []
    
    # ==================== SETTINGS ====================
    
    def get_settings(self):
        """
        Get system settings
        Returns: Dict with threshold_warning, threshold_critical, tier_limits, tier_prices, vat
        """
        query = "SELECT * FROM settings WHERE id = 1"
        result = self.execute_query(query)
        
        if result and len(result) > 0:
            settings = result[0]
            # Parse JSON tier_prices if it's a string
            if isinstance(settings.get('tier_prices'), str):
                try:
                    settings['tier_prices'] = json.loads(settings['tier_prices'])
                except:
                    settings['tier_prices'] = [1984, 2050, 2380, 2998, 3350, 3460]
            return settings
        
        # Return defaults if no settings found
        return {
            'threshold_warning': 500,
            'threshold_critical': 1000,
            'tier_limit1': 50,
            'tier_limit2': 100,
            'tier_limit3': 200,
            'tier_limit4': 300,
            'tier_limit5': 400,
            'tier_prices': [1984, 2050, 2380, 2998, 3350, 3460],
            'vat': 8
        }
    
    def update_settings(self, settings_dict):
        """
        Update system settings
        Args:
            settings_dict: Dict with keys like threshold_warning, tier_prices, etc.
        """
        updates = []
        params = []
        
        allowed_fields = [
            'threshold_warning', 'threshold_critical',
            'tier_limit1', 'tier_limit2', 'tier_limit3', 'tier_limit4', 'tier_limit5',
            'tier_prices', 'vat'
        ]
        
        for field in allowed_fields:
            if field in settings_dict:
                value = settings_dict[field]
                
                # Convert tier_prices list to JSON string
                if field == 'tier_prices' and isinstance(value, list):
                    value = json.dumps(value)
                
                updates.append(f"{field} = %s")
                params.append(value)
        
        if not updates:
            return False
        
        query = f"UPDATE settings SET {', '.join(updates)} WHERE id = 1"
        return self.execute_query(query, tuple(params), fetch=False)
    
    # ==================== ROOMS ====================
    
    def get_rooms(self):
        """Get all rooms with their current data"""
        query = "SELECT * FROM rooms ORDER BY id"
        return self.execute_query(query) or []
    
    def get_devices(self, room_id=None):
        """Get devices, optionally filtered by room_id"""
        if room_id:
            query = "SELECT * FROM devices WHERE room_id = %s ORDER BY id"
            return self.execute_query(query, (room_id,)) or []
        else:
            query = "SELECT * FROM devices ORDER BY room_id, id"
            return self.execute_query(query) or []


# ==================== TESTING ====================

if __name__ == "__main__":
    # Test connection
    db = DatabaseManager(
        host="47.128.66.94",
        user="root",
        password="fbd3b9f31da4a89d",
        database="power_management"
    )
    
    if db.connect():
        print("\n[TEST] Getting pending devices:")
        devices = db.get_pending_devices()
        for dev in devices:
            print(f"  Slave {dev['slave_id']}: device0={dev['device0']}, device1={dev['device1']}, sync={dev['sync']}")
        
        print("\n[TEST] Getting settings:")
        settings = db.get_settings()
        print(f"  Warning: {settings['threshold_warning']}W")
        print(f"  Critical: {settings['threshold_critical']}W")
        print(f"  Tier prices: {settings['tier_prices']}")
        
        print("\n[TEST] Getting all slaves:")
        slaves = db.get_all_slaves()
        print(f"  Slaves: {slaves}")
        
        if slaves:
            print(f"\n[TEST] Getting power data for slave {slaves[0]}:")
            power_data = db.get_power_data(slaves[0], hours=1)
            print(f"  Found {len(power_data)} data points in last hour")
            if power_data:
                print(f"  Latest: {power_data[-1]}")
        
        db.disconnect()
    else:
        print("[TEST] Failed to connect to database")
