# -*- coding: utf-8 -*-
"""
Firebase Handler for Power Management System
Connects to Firebase Realtime Database to sync power data
"""

import json
import threading
import time
from datetime import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    FIREBASE_ADMIN_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# Firebase Configuration
FIREBASE_CONFIG = {
    'apiKey': "AIzaSyDTvGflmFqArRm4MvJXNCEU6F7GGZ-vsFU",
    'authDomain': "datn-426e1.firebaseapp.com",
    'databaseURL': "https://datn-426e1-default-rtdb.firebaseio.com",
    'projectId': "datn-426e1",
    'storageBucket': "datn-426e1.firebasestorage.app",
    'messagingSenderId': "496143525778",
    'appId': "1:496143525778:web:e59595f5bee532f40d834b",
    'measurementId': "G-27WWLRE790"
}


class FirebaseHandler:
    """
    Firebase Realtime Database Handler
    Uses REST API for simplicity (no service account needed)
    """
    
    def __init__(self, config=None):
        self.config = config or FIREBASE_CONFIG
        self.database_url = self.config['databaseURL']
        self.connected = False
        self.last_sync = None
        self._callbacks = []
        self._sync_thread = None
        self._running = False
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test Firebase connection"""
        if not REQUESTS_AVAILABLE:
            print("[Firebase] requests library not available")
            return False
        
        try:
            response = requests.get(f"{self.database_url}/.json", timeout=5)
            if response.status_code == 200:
                self.connected = True
                print("[Firebase] Connected successfully")
                return True
            else:
                print(f"[Firebase] Connection failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[Firebase] Connection error: {e}")
            return False
    
    # ==================== ROOM DATA ====================
    
    def get_rooms(self):
        """Get all rooms data from Firebase"""
        try:
            response = requests.get(f"{self.database_url}/rooms.json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data if data else {}
            return {}
        except Exception as e:
            print(f"[Firebase] Error getting rooms: {e}")
            return {}
    
    def update_room(self, room_id, data):
        """Update a room's data"""
        try:
            response = requests.patch(
                f"{self.database_url}/rooms/{room_id}.json",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Firebase] Error updating room {room_id}: {e}")
            return False
    
    def set_room_power(self, room_id, power):
        """Update room's current power consumption"""
        return self.update_room(room_id, {'power': power, 'updated_at': self._get_timestamp()})
    
    # ==================== DEVICE CONTROL ====================
    
    def get_device_states(self, room_id):
        """Get device states for a room"""
        try:
            response = requests.get(
                f"{self.database_url}/rooms/{room_id}/devices.json",
                timeout=5
            )
            if response.status_code == 200:
                return response.json() or {}
            return {}
        except Exception as e:
            print(f"[Firebase] Error getting device states: {e}")
            return {}
    
    def set_device_state(self, room_id, device_id, state):
        """Set device ON/OFF state"""
        try:
            data = {
                'state': state,
                'updated_at': self._get_timestamp()
            }
            response = requests.patch(
                f"{self.database_url}/rooms/{room_id}/devices/{device_id}.json",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Firebase] Error setting device state: {e}")
            return False
    
    # ==================== POWER DATA ====================
    
    def get_total_power(self):
        """Get total power consumption"""
        try:
            response = requests.get(
                f"{self.database_url}/power/total.json",
                timeout=5
            )
            if response.status_code == 200:
                return response.json() or 0
            return 0
        except Exception as e:
            print(f"[Firebase] Error getting total power: {e}")
            return 0
    
    def update_power_data(self, room_powers, total_power):
        """Update power consumption data for all rooms"""
        try:
            data = {
                'rooms': room_powers,
                'total': total_power,
                'updated_at': self._get_timestamp()
            }
            response = requests.patch(
                f"{self.database_url}/power.json",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Firebase] Error updating power data: {e}")
            return False
    
    # ==================== ENERGY TRACKING ====================
    
    def get_energy_usage(self, period='today'):
        """Get energy usage for a period"""
        try:
            response = requests.get(
                f"{self.database_url}/energy/{period}.json",
                timeout=5
            )
            if response.status_code == 200:
                return response.json() or {}
            return {}
        except Exception as e:
            print(f"[Firebase] Error getting energy usage: {e}")
            return {}
    
    def update_energy_usage(self, energy_kwh, cost_vnd):
        """Update daily energy usage"""
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            data = {
                'energy_kwh': energy_kwh,
                'cost_vnd': cost_vnd,
                'updated_at': self._get_timestamp()
            }
            response = requests.patch(
                f"{self.database_url}/energy/daily/{today}.json",
                json=data,
                timeout=5
            )
            # Also update current totals
            requests.patch(
                f"{self.database_url}/energy/current.json",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Firebase] Error updating energy usage: {e}")
            return False
    
    # ==================== THRESHOLDS ====================
    
    def get_thresholds(self):
        """Get power thresholds settings"""
        try:
            response = requests.get(
                f"{self.database_url}/settings/thresholds.json",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data
            # Return defaults
            return {'warning': 500, 'critical': 1000}
        except Exception as e:
            print(f"[Firebase] Error getting thresholds: {e}")
            return {'warning': 500, 'critical': 1000}
    
    def set_thresholds(self, warning, critical):
        """Set power thresholds"""
        try:
            data = {
                'warning': warning,
                'critical': critical,
                'updated_at': self._get_timestamp()
            }
            response = requests.patch(
                f"{self.database_url}/settings/thresholds.json",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Firebase] Error setting thresholds: {e}")
            return False
    
    # ==================== ALERTS ====================
    
    def add_alert(self, alert_type, message, power_value):
        """Add a power alert"""
        try:
            alert_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            data = {
                'type': alert_type,  # 'warning' or 'critical'
                'message': message,
                'power': power_value,
                'timestamp': self._get_timestamp(),
                'acknowledged': False
            }
            response = requests.put(
                f"{self.database_url}/alerts/{alert_id}.json",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Firebase] Error adding alert: {e}")
            return False
    
    def get_recent_alerts(self, limit=10):
        """Get recent alerts"""
        try:
            response = requests.get(
                f"{self.database_url}/alerts.json?orderBy=\"timestamp\"&limitToLast={limit}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json() or {}
            return {}
        except Exception as e:
            print(f"[Firebase] Error getting alerts: {e}")
            return {}
    
    # ==================== SYNC ====================
    
    def sync_all_data(self, rooms_data, power_data, energy_data):
        """Sync all data to Firebase at once"""
        try:
            data = {
                'rooms': rooms_data,
                'power': power_data,
                'energy': {
                    'current': energy_data
                },
                'last_sync': self._get_timestamp()
            }
            response = requests.patch(
                f"{self.database_url}/.json",
                json=data,
                timeout=10
            )
            if response.status_code == 200:
                self.last_sync = datetime.now()
                return True
            return False
        except Exception as e:
            print(f"[Firebase] Error syncing data: {e}")
            return False
    
    def start_auto_sync(self, interval_seconds=5, callback=None):
        """Start auto-sync in background thread"""
        if self._sync_thread and self._sync_thread.is_alive():
            return
        
        self._running = True
        if callback:
            self._callbacks.append(callback)
        
        def sync_loop():
            while self._running:
                try:
                    # Fetch latest data from Firebase
                    response = requests.get(f"{self.database_url}/.json", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        for cb in self._callbacks:
                            try:
                                cb(data)
                            except Exception as e:
                                print(f"[Firebase] Callback error: {e}")
                except Exception as e:
                    print(f"[Firebase] Sync error: {e}")
                
                time.sleep(interval_seconds)
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        print(f"[Firebase] Auto-sync started (interval: {interval_seconds}s)")
    
    def stop_auto_sync(self):
        """Stop auto-sync"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=2)
        print("[Firebase] Auto-sync stopped")
    
    def add_sync_callback(self, callback):
        """Add callback for data sync events"""
        self._callbacks.append(callback)
    
    # ==================== HELPERS ====================
    
    def _get_timestamp(self):
        """Get current timestamp string"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def is_connected(self):
        """Check if connected to Firebase"""
        return self.connected
    
    def get_status(self):
        """Get connection status info"""
        return {
            'connected': self.connected,
            'database_url': self.database_url,
            'last_sync': self.last_sync.strftime('%H:%M:%S') if self.last_sync else 'Never',
            'auto_sync': self._running
        }


# Singleton instance
_firebase_instance = None

def get_firebase():
    """Get Firebase handler singleton instance"""
    global _firebase_instance
    if _firebase_instance is None:
        _firebase_instance = FirebaseHandler()
    return _firebase_instance


# Test connection when module loads
if __name__ == "__main__":
    print("Testing Firebase connection...")
    fb = FirebaseHandler()
    print(f"Status: {fb.get_status()}")
    
    # Test write
    print("\nTesting write...")
    fb.update_power_data({'room1': 100, 'room2': 200}, 300)
    
    # Test read
    print("\nTesting read...")
    print(f"Total power: {fb.get_total_power()}")
    print(f"Thresholds: {fb.get_thresholds()}")
