# -*- coding: utf-8 -*-
"""
Firebase Realtime Database Handler for Power Management System
Syncs device states and power data with Firebase bidirectionally
"""

import threading
import time

# Try importing pyrebase4 (simpler than firebase-admin)
try:
    import pyrebase
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("[WARNING] pyrebase4 not installed. Run: pip install pyrebase4")

from config import ROOMS, POWER_THRESHOLDS


# Firebase Configuration - YOUR PROJECT
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDTvGflmFqArRm4MvJXNCEU6F7GGZ-vsFU",
    "authDomain": "datn-426e1.firebaseapp.com",
    "databaseURL": "https://datn-426e1-default-rtdb.firebaseio.com",
    "projectId": "datn-426e1",
    "storageBucket": "datn-426e1.firebasestorage.app",
    "messagingSenderId": "496143525778",
    "appId": "1:496143525778:web:e59595f5bee532f40d834b"
}


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
                /name: "Phong 1"
                /power: 60 (W)
                /devices/
                    /device0/
                        state: true/false
                        name: "Den"
                        power: 15 (W)
        /total/
            /power: 500 (W)
            /monthly_cost: 750000 (VND)
        /control/
            /room1/device0: true/false
        /settings/
            /thresholds: {warning: 500, critical: 1000}
    """
    
    def __init__(self):
        self.connected = False
        self.simulation_mode = not FIREBASE_AVAILABLE
        self.db = None
        self.device_states = {}
        self.power_data = {}
        self.on_device_change_callback = None
        self.stream = None
        self.stream_thread = None
        
        # Initialize device states from config
        self._init_device_states()
    
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
            print("[SIM] Firebase simulation mode - pyrebase4 not installed")
            return True
        
        try:
            firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
            self.db = firebase.database()
            self.connected = True
            print("[FIREBASE] Connected to Firebase Realtime Database")
            print(f"[FIREBASE] URL: {FIREBASE_CONFIG['databaseURL']}")
            
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
        if self.stream:
            self.stream.close()
            self.stream = None
        self.connected = False
    
    def sync_device_states_from_firebase(self):
        """Read all device states from Firebase and return them"""
        if self.simulation_mode or not self.db:
            return {}
        
        try:
            data = self.db.child("power_management").child("control").get().val()
            if data:
                print(f"[FIREBASE] Loaded device states: {data}")
                # Parse and update local states
                for room_key, devices in data.items():
                    room_id = int(room_key.replace('room', ''))
                    if isinstance(devices, dict):
                        for device_key, state in devices.items():
                            device_id = int(device_key.replace('device', ''))
                            if room_id in self.device_states and device_id in self.device_states[room_id]:
                                self.device_states[room_id][device_id]['state'] = bool(state)
                return data
            return {}
        except Exception as e:
            print(f"[ERROR] Firebase sync device states: {e}")
            return {}
    
    def get_all_device_states(self) -> dict:
        """Get all device states from local cache"""
        return self.device_states
    
    def _start_control_listener(self):
        """Start listening for device control commands from Firebase"""
        if self.simulation_mode or not self.db:
            return
        
        try:
            # Start stream in background thread
            def stream_handler(message):
                self._on_control_change(message)
            
            self.stream = self.db.child("power_management").child("control").stream(stream_handler)
            print("[FIREBASE] Listening for control commands...")
        except Exception as e:
            print(f"[ERROR] Failed to start control listener: {e}")
    
    def _on_control_change(self, message):
        """Handle control commands from Firebase"""
        try:
            if message["data"] is None:
                return
            
            path = message["path"].strip('/')
            data = message["data"]
            event = message["event"]
            
            print(f"[FIREBASE] Stream event: {event}, path: {path}, data: {data}")
            
            # Parse path: room1/device0
            if '/' in path:
                parts = path.split('/')
                room_key = parts[0]
                device_key = parts[1]
                
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
        """Handle remote control command"""
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            old_state = self.device_states[room_id][device_id]['state']
            if old_state != state:
                self.device_states[room_id][device_id]['state'] = state
                print(f"[FIREBASE] Remote: Room {room_id}, Device {device_id} -> {'ON' if state else 'OFF'}")
                
                if self.on_device_change_callback:
                    self.on_device_change_callback(room_id, device_id, state)
    
    def set_device_change_callback(self, callback):
        """Set callback for device state changes from Firebase"""
        self.on_device_change_callback = callback
    
    # ===== Device Control Methods =====
    
    def set_device_state(self, room_id: int, device_id: int, state: bool) -> bool:
        """Set device state in Firebase"""
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            self.device_states[room_id][device_id]['state'] = state
        
        if self.simulation_mode:
            print(f"[SIM] Firebase: Room {room_id}, Device {device_id}: {'ON' if state else 'OFF'}")
            return True
        
        try:
            # Update control path
            self.db.child("power_management").child("control").child(f"room{room_id}").child(f"device{device_id}").set(state)
            
            # Update rooms path
            self.db.child("power_management").child("rooms").child(f"room{room_id}").child("devices").child(f"device{device_id}").update({"state": state})
            
            print(f"[FIREBASE] Set Room {room_id}, Device {device_id}: {'ON' if state else 'OFF'}")
            return True
        except Exception as e:
            print(f"[ERROR] Firebase set device state: {e}")
            return False
    
    def get_device_state(self, room_id: int, device_id: int) -> bool:
        """Get device state from local cache"""
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            return self.device_states[room_id][device_id]['state']
        return False
    
    def toggle_device(self, room_id: int, device_id: int) -> bool:
        """Toggle device state"""
        current_state = self.get_device_state(room_id, device_id)
        new_state = not current_state
        return self.set_device_state(room_id, device_id, new_state)
    
    def get_room_power(self, room_id: int) -> float:
        """Get total power for a room from Firebase"""
        # Try to read from Firebase first
        if not self.simulation_mode and self.db:
            try:
                data = self.db.child("power_management").child("rooms").child(f"room{room_id}").child("power").get().val()
                if data is not None:
                    return float(data)
            except Exception as e:
                print(f"[ERROR] Get room power: {e}")
        
        # Fallback: calculate from device states
        total = 0.0
        if room_id in self.device_states:
            for device_id, device_data in self.device_states[room_id].items():
                if device_data['state']:
                    total += device_data['power']
        return total
    
    def get_active_power(self) -> float:
        """Get total active power from Firebase"""
        # Try to read from Firebase first
        if not self.simulation_mode and self.db:
            try:
                data = self.db.child("power_management").child("total").child("power").get().val()
                if data is not None:
                    return float(data)
            except Exception as e:
                print(f"[ERROR] Get total power: {e}")
        
        # Fallback: sum all room powers
        total = 0.0
        for room_id in self.device_states:
            total += self.get_room_power(room_id)
        return total
    
    def get_device_power(self, room_id: int, device_id: int) -> float:
        """Get power for a specific device from Firebase"""
        if not self.simulation_mode and self.db:
            try:
                data = self.db.child("power_management").child("rooms").child(f"room{room_id}").child("devices").child(f"device{device_id}").child("power").get().val()
                if data is not None:
                    return float(data)
            except Exception as e:
                print(f"[ERROR] Get device power: {e}")
        
        # Fallback to config
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            return self.device_states[room_id][device_id]['power']
        return 0.0
    
    def disconnect(self):
        """Disconnect from Firebase"""
        self.stop_auto_sync()
        if self.stream:
            try:
                self.stream.close()
            except:
                pass
            self.stream = None
        self.connected = False
        print("[FIREBASE] Disconnected")

    # ===== Power Data Methods =====
    
    def update_power_data(self, room_powers: dict, total_power: float):
        """Update room power data to Firebase"""
        if self.simulation_mode:
            return True
        
        try:
            # Update each room
            for room_key, room_data in room_powers.items():
                self.db.child("power_management").child("rooms").child(room_key).update({
                    'name': room_data.get('name', ''),
                    'power': round(room_data.get('power', 0), 2)
                })
                
                # Update devices
                if 'devices' in room_data:
                    for device_key, device_data in room_data['devices'].items():
                        self.db.child("power_management").child("rooms").child(room_key).child("devices").child(device_key).update(device_data)
            
            # Update total
            self.db.child("power_management").child("total").update({
                'power': round(total_power, 2)
            })
            
            return True
        except Exception as e:
            print(f"[ERROR] Firebase update power: {e}")
            return False
    
    def update_energy_usage(self, energy_kwh: float, monthly_cost: float):
        """Update energy usage and cost to Firebase"""
        if self.simulation_mode:
            return True
        
        try:
            self.db.child("power_management").child("total").update({
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
            data = self.db.child("power_management").child("settings").child("thresholds").get().val()
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
            self.db.child("power_management").child("settings").child("thresholds").update({
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
            data = self.db.child("power_management").child("settings").get().val()
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
            self.db.child("power_management").child("settings").update({
                'tier_prices': prices,
                'vat': vat
            })
            return True
        except Exception as e:
            print(f"[ERROR] Firebase set tier prices: {e}")
            return False
    
    def stop_auto_sync(self):
        """Stop auto-sync/stream"""
        if self.stream:
            try:
                self.stream.close()
            except:
                pass
            self.stream = None










