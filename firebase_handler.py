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
        self.power_stream = None
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
            
            # Start listening for power value changes
            self._start_power_listener()
            
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
            try:
                self.stream.close()
            except:
                pass
            self.stream = None
        if self.power_stream:
            try:
                self.power_stream.close()
            except:
                pass
            self.power_stream = None
        self.connected = False
    
    def sync_device_states_from_firebase(self):
        """Read all device states AND power values from Firebase"""
        if self.simulation_mode or not self.db:
            return {}
        
        try:
            # Load device states from /control
            control_data = self.db.child("power_management").child("control").get().val()
            if control_data:
                print(f"[FIREBASE] Loaded device states: {control_data}")
                for room_key, devices in control_data.items():
                    room_id = int(room_key.replace('room', ''))
                    if isinstance(devices, dict):
                        for device_key, state in devices.items():
                            device_id = int(device_key.replace('device', ''))
                            if room_id in self.device_states and device_id in self.device_states[room_id]:
                                self.device_states[room_id][device_id]['state'] = bool(state)
            
            # Load device power values from /rooms
            rooms_data = self.db.child("power_management").child("rooms").get().val()
            if rooms_data:
                print(f"[FIREBASE] Loading power values from Firebase...")
                for room_key, room_data in rooms_data.items():
                    room_id = int(room_key.replace('room', ''))
                    if isinstance(room_data, dict) and 'devices' in room_data:
                        for device_key, device_data in room_data['devices'].items():
                            device_id = int(device_key.replace('device', ''))
                            if room_id in self.device_states and device_id in self.device_states[room_id]:
                                # Read power from Firebase, not from config!
                                if 'power' in device_data:
                                    firebase_power = device_data['power']
                                    self.device_states[room_id][device_id]['power'] = float(firebase_power)
                                    print(f"[FIREBASE] Room {room_id}, Device {device_id}: {firebase_power}W")
            
            return control_data
        except Exception as e:
            print(f"[ERROR] Firebase sync device states: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_all_device_states(self) -> dict:
        """Get all device states from local cache"""
        return self.device_states
    
    def _start_control_listener(self):
        """Start listening for device control commands from Firebase"""
        if self.simulation_mode or not self.db:
            return
        
        try:
            # Start stream in background thread to prevent blocking UI
            def stream_handler(message):
                # Handle in background thread
                thread = threading.Thread(target=self._on_control_change, args=(message,), daemon=True)
                thread.start()
            
            # Start stream
            def start_stream():
                try:
                    self.stream = self.db.child("power_management").child("control").stream(stream_handler)
                    print("[FIREBASE] Listening for control commands...")
                except Exception as e:
                    print(f"[ERROR] Stream failed: {e}")
            
            # Run stream in background thread
            stream_thread = threading.Thread(target=start_stream, daemon=True)
            stream_thread.start()
            
        except Exception as e:
            print(f"[ERROR] Failed to start control listener: {e}")
    
    def _start_power_listener(self):
        """Start listening for power value changes from Firebase"""
        if self.simulation_mode or not self.db:
            return
        
        try:
            def power_stream_handler(message):
                thread = threading.Thread(target=self._on_power_change, args=(message,), daemon=True)
                thread.start()
            
            def start_power_stream():
                try:
                    self.power_stream = self.db.child("power_management").child("rooms").stream(power_stream_handler)
                    print("[FIREBASE] Listening for power value changes...")
                except Exception as e:
                    print(f"[ERROR] Power stream failed: {e}")
            
            stream_thread = threading.Thread(target=start_power_stream, daemon=True)
            stream_thread.start()
            
        except Exception as e:
            print(f"[ERROR] Failed to start power listener: {e}")
    
    def _on_power_change(self, message):
        """Handle power value changes from Firebase"""
        try:
            if message["data"] is None:
                return
            
            path = message["path"].strip('/')
            data = message["data"]
            event = message["event"]
            
            # Look for device power updates: room1/devices/device0/power
            if 'devices' in path and 'power' in path:
                parts = path.split('/')
                if len(parts) >= 4:
                    room_key = parts[0]
                    device_key = parts[2]
                    
                    room_id = int(room_key.replace('room', ''))
                    device_id = int(device_key.replace('device', ''))
                    
                    if isinstance(data, (int, float)):
                        if room_id in self.device_states and device_id in self.device_states[room_id]:
                            old_power = self.device_states[room_id][device_id]['power']
                            new_power = float(data)
                            if old_power != new_power:
                                self.device_states[room_id][device_id]['power'] = new_power
                                print(f"[FIREBASE] Power updated: Room {room_id}, Device {device_id}: {old_power}W → {new_power}W")
            
        except Exception as e:
            print(f"[ERROR] Processing power change: {e}")
    
    def _on_control_change(self, message):
        """Handle control commands from Firebase"""
        try:
            if message["data"] is None:
                return
            
            path = message["path"].strip('/')
            data = message["data"]
            event = message["event"]
            
            print(f"[FIREBASE] Stream event: {event}, path: '{path}', data: {data}")
            
            # Handle initial full data load (path is empty, data is full dict)
            if path == "" and isinstance(data, dict):
                print("[FIREBASE] Initial data load from stream")
                for room_key, devices in data.items():
                    if isinstance(devices, dict):
                        room_id = int(room_key.replace('room', ''))
                        for device_key, state in devices.items():
                            device_id = int(device_key.replace('device', ''))
                            if isinstance(state, bool):
                                # Only update local cache, don't trigger callback on initial load
                                if room_id in self.device_states and device_id in self.device_states[room_id]:
                                    self.device_states[room_id][device_id]['state'] = state
                return
            
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
            elif path and isinstance(data, bool):
                # Single device update with path like "room1/device0" but parsed as single part
                # This handles edge case
                pass
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
        """Set device state in Firebase (async - doesn't block UI)"""
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            self.device_states[room_id][device_id]['state'] = state
        
        if self.simulation_mode:
            print(f"[SIM] Firebase: Room {room_id}, Device {device_id}: {'ON' if state else 'OFF'}")
            return True
        
        # Run Firebase update in background thread
        def update_firebase():
            try:
                self.db.child("power_management").child("control").child(f"room{room_id}").child(f"device{device_id}").set(state)
                self.db.child("power_management").child("rooms").child(f"room{room_id}").child("devices").child(f"device{device_id}").update({"state": state})
                print(f"[FIREBASE] Set Room {room_id}, Device {device_id}: {'ON' if state else 'OFF'}")
            except Exception as e:
                print(f"[ERROR] Firebase set device state: {e}")
        
        thread = threading.Thread(target=update_firebase, daemon=True)
        thread.start()
        return True
    
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
        """Get total power for a room from local cache (fast)"""
        # Use local cache - Firebase stream updates it automatically
        total = 0.0
        if room_id in self.device_states:
            for device_id, device_data in self.device_states[room_id].items():
                if device_data['state']:
                    total += device_data['power']
        return total
    
    def get_active_power(self) -> float:
        """Get total active power from local cache (fast)"""
        # Use local cache - Firebase stream updates it automatically
        total = 0.0
        for room_id in self.device_states:
            total += self.get_room_power(room_id)
        return total
    
    def get_device_power(self, room_id: int, device_id: int) -> float:
        """Get power for a specific device from local cache"""
        if room_id in self.device_states and device_id in self.device_states[room_id]:
            if self.device_states[room_id][device_id]['state']:
                return self.device_states[room_id][device_id]['power']
        return 0.0
    
    def get_all_room_data(self, room_id: int) -> dict:
        """Get all data for a room from local cache (fast)"""
        result = {
            'name': '',
            'total_power': 0,
            'devices': {}
        }
        
        # Use local cache
        if room_id in self.device_states:
            for dev_id, dev_data in self.device_states[room_id].items():
                result['devices'][f'device{dev_id}'] = dev_data
                if dev_data['state']:
                    result['total_power'] += dev_data['power']
        return result
    
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
        """Update room power CONSUMPTION to Firebase (async) - does NOT change device power ratings"""
        if self.simulation_mode:
            print(f"[SIM] Would update Firebase: Total={total_power}W")
            return True
        
        def update_firebase():
            try:
                # Update each room's current consumption (NOT device power ratings)
                for room_key, room_data in room_powers.items():
                    # Only update room-level power consumption
                    room_update = {
                        'name': room_data.get('name', ''),
                        'power': round(room_data.get('power', 0), 2)  # Current consumption
                    }
                    self.db.child("power_management").child("rooms").child(room_key).update(room_update)
                    print(f"[FIREBASE] Updated {room_key} consumption: {room_update['power']}W")
                    
                    # Update device STATES only, NOT power ratings
                    if 'devices' in room_data:
                        for device_key, device_data in room_data['devices'].items():
                            # Only update name and state - preserve power rating from Firebase
                            device_update = {
                                'name': device_data.get('name', ''),
                                'state': device_data.get('state', False)
                                # DO NOT update 'power' - it's set via Firebase console/app
                            }
                            self.db.child("power_management").child("rooms").child(room_key).child("devices").child(device_key).update(device_update)
                
                # Update total consumption
                total_update = {'power': round(total_power, 2)}
                self.db.child("power_management").child("total").update(total_update)
                print(f"[FIREBASE] Updated TOTAL consumption: {total_power}W")
            except Exception as e:
                print(f"[ERROR] Firebase update power: {e}")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=update_firebase, daemon=True)
        thread.start()
        return True
    
    def update_energy_usage(self, energy_kwh: float, monthly_cost: float):
        """Update energy usage and cost to Firebase (async)"""
        if self.simulation_mode:
            print(f"[SIM] Would update energy: {energy_kwh} kWh, {monthly_cost} VND")
            return True
        
        def update_firebase():
            try:
                energy_update = {
                    'energy': round(energy_kwh, 2),
                    'monthly_cost': round(monthly_cost, 0)
                }
                self.db.child("power_management").child("total").update(energy_update)
                print(f"[FIREBASE] Updated energy: {energy_kwh} kWh, cost: {monthly_cost} VND")
            except Exception as e:
                print(f"[ERROR] Firebase update energy: {e}")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=update_firebase, daemon=True)
        thread.start()
        return True
    
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
        """Save threshold settings to Firebase (async)"""
        if self.simulation_mode:
            return True
        
        def update_firebase():
            try:
                self.db.child("power_management").child("settings").child("thresholds").update({
                    'warning': warning,
                    'critical': critical
                })
            except Exception as e:
                print(f"[ERROR] Firebase set thresholds: {e}")
        
        thread = threading.Thread(target=update_firebase, daemon=True)
        thread.start()
        return True
    
    # ===== Tier Prices =====
    
    def get_tier_prices(self) -> tuple:
        """Get tier prices and VAT from Firebase"""
        if self.simulation_mode:
            return None, None
        
        try:
            data = self.db.child("power_management").child("settings").get().val()
            if data:
                tier_prices_data = data.get('tier_prices')
                vat = data.get('vat')
                
                # Convert tier_prices from dict to list if needed
                if isinstance(tier_prices_data, dict):
                    # Firebase stores as {"tier1": 1678, "tier2": 1734, ...}
                    # Convert to [1678, 1734, ...]
                    prices = []
                    for i in range(1, 7):  # tier1 to tier6
                        tier_key = f"tier{i}"
                        if tier_key in tier_prices_data:
                            price = tier_prices_data[tier_key]
                            # Ensure it's a number
                            if isinstance(price, (int, float, str)):
                                try:
                                    prices.append(int(price))
                                except ValueError:
                                    prices.append(0)
                            else:
                                prices.append(0)
                    if len(prices) == 6:
                        return prices, vat
                elif isinstance(tier_prices_data, list) and len(tier_prices_data) == 6:
                    # Already a list, just validate
                    prices = []
                    for price in tier_prices_data:
                        if isinstance(price, (int, float, str)):
                            try:
                                prices.append(int(price))
                            except ValueError:
                                prices.append(0)
                        else:
                            prices.append(0)
                    return prices, vat
        except Exception as e:
            print(f"[ERROR] Firebase get tier prices: {e}")
        
        return None, None
    
    def set_tier_prices(self, prices: list, vat: int):
        """Save tier prices and VAT to Firebase (async)"""
        if self.simulation_mode:
            return True
        
        def update_firebase():
            try:
                self.db.child("power_management").child("settings").update({
                    'tier_prices': prices,
                    'vat': vat
                })
            except Exception as e:
                print(f"[ERROR] Firebase set tier prices: {e}")
        
        thread = threading.Thread(target=update_firebase, daemon=True)
        thread.start()
        return True
    
    def stop_auto_sync(self):
        """Stop auto-sync/streams"""
        if self.stream:
            try:
                self.stream.close()
            except:
                pass
            self.stream = None
        if self.power_stream:
            try:
                self.power_stream.close()
            except:
                pass
            self.power_stream = None










