# -*- coding: utf-8 -*-
"""
Firebase Realtime Database Handler for Power Management System
Syncs device states and power data with Firebase bidirectionally
"""

import json
import threading
import time

# Try importing firebase-admin
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("[WARNING] firebase-admin not installed, running in simulation mode")

from config import ROOMS, POWER_THRESHOLDS


# Singleton instance
_firebase_instance = None


def get_firebase():
    """Get or create Firebase handler singleton"""
    global _firebase_instance
    if _firebase_instance is None:
        _firebase_instance = FirebaseHandler()
        _firebase_instance.connect()
    return _firebase_instance


class FirebaseHandler:
    """
    Handles Firebase Realtime Database communication
    
    Firebase Structure:
    /power_management/
        /rooms/
            /room1/
                /name: "Phòng 1"
                /power: 60 (W)
                /energy: 1.5 (kWh)
                /devices/
                    /device0/
                        state: true/false
                        name: "Đèn"
                        power: 15 (W)
                    /device1/
                        state: true/false
                        name: "Quạt"
                        power: 45 (W)
            /room2/
                ...
        /total/
            /power: 500 (W)
            /energy: 10.5 (kWh)
            /monthly_cost: 750000 (VND)
        /settings/
            /thresholds/
                warning: 500
                critical: 1000
            /tier_prices: [1893, 1956, 2271, 2860, 3197, 3302]
            /vat: 8
        /control/  (for bidirectional control from app/web)
            /room1/
                /device0: true/false
                /device1: true/false
            ...
    """
    
    def __init__(self, cred_path: str = None, database_url: str = None):
        """
        Initialize Firebase handler
        
        Args:
            cred_path: Path to Firebase service account JSON file
            database_url: Firebase Realtime Database URL
        """
        self.connected = False
        self.simulation_mode = not FIREBASE_AVAILABLE
        self.db_ref = None
        self.control_listener = None
        self.device_states = {}
        self.power_data = {}
        self.on_device_change_callback = None
        self.auto_sync_thread = None
        self.auto_sync_running = False
        
        # Initialize device states from config
        self._init_device_states()
        
        # Firebase config - UPDATE THESE with your Firebase project
        self.cred_path = cred_path or "firebase_credentials.json"
        self.database_url = database_url or "https://your-project-id.firebaseio.com"
    
    def _init_device_states(self):
        """Initialize device states from config"""
        for room in ROOMS:
            room_id = room['id']
            self.device_states[room_id] = {}
            self.power_data[room_id] = {'power': 0.0, 'energy': 0.0}
            for device in room['devices']:
                self.device_states[room_id][device['id']] = {
                    'state': False,
                    'name': device['name'],
                    'power': device['power']
                }
    
    def connect(self) -> bool:
        """Connect to Firebase"""
        if self.simulation_mode:
            self.connected = True
            print("[SIM] Firebase simulation mode active")
            return True
        
        try:
            # Initialize Firebase app
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.cred_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.database_url
                })
            
            self.db_ref = db.reference('power_management')
            self.connected = True
            print("[FIREBASE] Connected to Firebase")
            
            # Start listening for control commands
            self._start_control_listener()
            
            return True
        except Exception as e:
            print(f"[ERROR] Firebase connection failed: {e}")
            self.simulation_mode = True
            self.connected = True
            return True
    
    def is_connected(self) -> bool:
        """Check if connected to Firebase"""
        return self.connected and not self.simulation_mode
    
    def disconnect(self):
        """Disconnect from Firebase"""
        self.stop_auto_sync()
        if self.control_listener:
            self.control_listener.close()
            self.control_listener = None
        self.connected = False
    
    def _start_control_listener(self):
        """Start listening for device control commands from Firebase"""
        if self.simulation_mode:
            return
        
        try:
            control_ref = self.db_ref.child('control')
            self.control_listener = control_ref.listen(self._on_control_change)
            print("[FIREBASE] Listening for control commands")
        except Exception as e:
            print(f"[ERROR] Failed to start control listener: {e}")
    
    def _on_control_change(self, event):
        """Handle control commands from Firebase (app/web)"""
        try:
            if event.data is None:
                return
            
            path = event.path.strip('/')
            data = event.data
            
            # Parse path: room1/device0
            if '/' in path:
                parts = path.split('/')
                room_key = parts[0]  # room1
                device_key = parts[1]  # device0
                
                room_id = int(room_key.replace('room', ''))
                device_id = int(device_key.replace('device', ''))
                
                if isinstance(data, bool):
                    self._handle_remote_control(room_id, device_id, data)
            elif path and isinstance(data, dict):
                # Full room update
                room_id = int(path.replace('room', ''))
                for device_key, state in data.items():
                    device_id = int(device_key.replace('device', ''))
                    if isinstance(state, bool):
                        self._handle_remote_control(room_id, device_id, state)
        except Exception as e:
            print(f"[ERROR] Processing control event: {e}")
    
    def _handle_remote_control(self, room_id: int, device_id: int, state: bool):
        """Handle remote control command and trigger callback"""
        # Update local state
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            old_state = self.device_states[room_id][device_id]['state']
            if old_state != state:
                self.device_states[room_id][device_id]['state'] = state
                print(f"[FIREBASE] Remote control: Room {room_id}, Device {device_id} -> {'ON' if state else 'OFF'}")
                
                # Trigger callback to update UI and Modbus
                if self.on_device_change_callback:
                    self.on_device_change_callback(room_id, device_id, state)
    
    def set_device_change_callback(self, callback):
        """Set callback for device state changes from Firebase
        
        Callback signature: callback(room_id: int, device_id: int, state: bool)
        """
        self.on_device_change_callback = callback
    
    # ===== Device Control Methods =====
    
    def set_device_state(self, room_id: int, device_id: int, state: bool) -> bool:
        """
        Set device state in Firebase (called from UI)
        
        Args:
            room_id: Room identifier
            device_id: Device identifier
            state: True = ON, False = OFF
        
        Returns:
            bool: Success status
        """
        # Update local state
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            self.device_states[room_id][device_id]['state'] = state
        
        if self.simulation_mode:
            print(f"[SIM] Firebase: Room {room_id}, Device {device_id}: {'ON' if state else 'OFF'}")
            return True
        
        try:
            # Update in control path
            ref = self.db_ref.child(f'control/room{room_id}/device{device_id}')
            ref.set(state)
            
            # Update in rooms path
            device_ref = self.db_ref.child(f'rooms/room{room_id}/devices/device{device_id}/state')
            device_ref.set(state)
            
            return True
        except Exception as e:
            print(f"[ERROR] Firebase set device state: {e}")
            return False
    
    def get_device_state(self, room_id: int, device_id: int) -> bool:
        """Get device state from local cache"""
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            return self.device_states[room_id][device_id]['state']
        return False
    
    # ===== Power Data Methods =====
    
    def update_power_data(self, room_powers: dict, total_power: float):
        """
        Update room power data to Firebase
        
        Args:
            room_powers: Dict of room power data
            total_power: Total power consumption
        """
        if self.simulation_mode:
            return True
        
        try:
            # Update each room
            for room_key, room_data in room_powers.items():
                room_ref = self.db_ref.child(f'rooms/{room_key}')
                room_ref.update({
                    'name': room_data.get('name', ''),
                    'power': round(room_data.get('power', 0), 2)
                })
                
                # Update devices
                if 'devices' in room_data:
                    for device_key, device_data in room_data['devices'].items():
                        device_ref = room_ref.child(f'devices/{device_key}')
                        device_ref.update(device_data)
            
            # Update total
            total_ref = self.db_ref.child('total')
            total_ref.update({
                'power': round(total_power, 2),
                'last_updated': {'.sv': 'timestamp'}
            })
            
            return True
        except Exception as e:
            print(f"[ERROR] Firebase update power data: {e}")
            return False
    
    def update_energy_usage(self, energy_kwh: float, monthly_cost: float):
        """Update energy usage and cost to Firebase"""
        if self.simulation_mode:
            return True
        
        try:
            total_ref = self.db_ref.child('total')
            total_ref.update({
                'energy': round(energy_kwh, 2),
                'monthly_cost': round(monthly_cost, 0)
            })
            return True
        except Exception as e:
            print(f"[ERROR] Firebase update energy: {e}")
            return False
    
    # ===== Threshold Settings =====
    
    def get_thresholds(self) -> dict:
        """Get threshold settings from Firebase"""
        if self.simulation_mode:
            return POWER_THRESHOLDS.copy()
        
        try:
            thresholds_ref = self.db_ref.child('settings/thresholds')
            data = thresholds_ref.get()
            if data:
                return {
                    'warning': data.get('warning', POWER_THRESHOLDS['warning']),
                    'critical': data.get('critical', POWER_THRESHOLDS['critical'])
                }
        except Exception as e:
            print(f"[ERROR] Firebase get thresholds: {e}")
        
        return POWER_THRESHOLDS.copy()
    
    def set_thresholds(self, warning: int, critical: int):
        """Save threshold settings to Firebase"""
        if self.simulation_mode:
            return True
        
        try:
            thresholds_ref = self.db_ref.child('settings/thresholds')
            thresholds_ref.update({
                'warning': warning,
                'critical': critical
            })
            return True
        except Exception as e:
            print(f"[ERROR] Firebase set thresholds: {e}")
            return False
    
    # ===== Tier Prices =====
    
    def get_tier_prices(self) -> tuple:
        """Get tier prices and VAT from Firebase"""
        if self.simulation_mode:
            return None, None
        
        try:
            settings_ref = self.db_ref.child('settings')
            data = settings_ref.get()
            if data:
                prices = data.get('tier_prices')
                vat = data.get('vat')
                return prices, vat
        except Exception as e:
            print(f"[ERROR] Firebase get tier prices: {e}")
        
        return None, None
    
    def set_tier_prices(self, prices: list, vat: int):
        """Save tier prices and VAT to Firebase"""
        if self.simulation_mode:
            return True
        
        try:
            settings_ref = self.db_ref.child('settings')
            settings_ref.update({
                'tier_prices': prices,
                'vat': vat
            })
            return True
        except Exception as e:
            print(f"[ERROR] Firebase set tier prices: {e}")
            return False
    
    # ===== Fetch Room Power from Firebase =====
    
    def fetch_room_power(self) -> dict:
        """
        Fetch room power data from Firebase
        Returns: {room_id: {'power': W, 'energy': kWh}}
        """
        if self.simulation_mode:
            return {}
        
        try:
            rooms_ref = self.db_ref.child('rooms')
            data = rooms_ref.get()
            
            result = {}
            if data:
                for room_key, room_data in data.items():
                    room_id = int(room_key.replace('room', ''))
                    result[room_id] = {
                        'power': room_data.get('power', 0),
                        'energy': room_data.get('energy', 0),
                        'name': room_data.get('name', f'Room {room_id}')
                    }
            return result
        except Exception as e:
            print(f"[ERROR] Firebase fetch room power: {e}")
            return {}
    
    def fetch_total_stats(self) -> dict:
        """
        Fetch total statistics from Firebase
        Returns: {'power': W, 'energy': kWh, 'monthly_cost': VND}
        """
        if self.simulation_mode:
            return {}
        
        try:
            total_ref = self.db_ref.child('total')
            data = total_ref.get()
            return data or {}
        except Exception as e:
            print(f"[ERROR] Firebase fetch total: {e}")
            return {}
    
    # ===== Auto Sync =====
    
    def start_auto_sync(self, interval: float = 5.0):
        """Start auto-sync thread (not typically needed with listeners)"""
        if self.auto_sync_running:
            return
        
        self.auto_sync_running = True
        self.auto_sync_thread = threading.Thread(target=self._auto_sync_loop, args=(interval,), daemon=True)
        self.auto_sync_thread.start()
    
    def stop_auto_sync(self):
        """Stop auto-sync thread"""
        self.auto_sync_running = False
        if self.auto_sync_thread:
            self.auto_sync_thread.join(timeout=1.0)
            self.auto_sync_thread = None
    
    def _auto_sync_loop(self, interval: float):
        """Auto-sync loop (runs in background thread)"""
        while self.auto_sync_running:
            try:
                # Fetch latest data from Firebase
                room_data = self.fetch_room_power()
                if room_data:
                    for room_id, data in room_data.items():
                        self.power_data[room_id] = data
            except Exception as e:
                print(f"[ERROR] Auto-sync: {e}")
            
            time.sleep(interval)

