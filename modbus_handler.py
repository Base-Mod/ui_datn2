# -*- coding: utf-8 -*-
"""
Modbus RTU Communication Handler for Power Management System
"""

from config import MODBUS_CONFIG, ROOMS

# Try importing pymodbus, use simulation if not available
try:
    from pymodbus.client import ModbusSerialClient
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    print("[WARNING] pymodbus not installed, running in simulation mode")


class ModbusHandler:
    """
    Handles Modbus RTU communication with slave devices
    Each room is a Modbus slave with unique address
    """
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.simulation_mode = not MODBUS_AVAILABLE
        
        # Device states for simulation/tracking
        # Format: {room_id: {device_id: state}}
        self.device_states = {}
        self._init_device_states()
    
    def _init_device_states(self):
        """Initialize device states from config"""
        for room in ROOMS:
            self.device_states[room['id']] = {}
            for device in room['devices']:
                self.device_states[room['id']][device['id']] = False
    
    def connect(self):
        """Connect to Modbus RTU"""
        if self.simulation_mode:
            self.connected = True
            print("[SIM] Modbus simulation mode active")
            return True
        
        try:
            self.client = ModbusSerialClient(
                port=MODBUS_CONFIG['port'],
                baudrate=MODBUS_CONFIG['baudrate'],
                parity=MODBUS_CONFIG['parity'],
                stopbits=MODBUS_CONFIG['stopbits'],
                bytesize=MODBUS_CONFIG['bytesize'],
                timeout=MODBUS_CONFIG['timeout']
            )
            self.connected = self.client.connect()
            return self.connected
        except Exception as e:
            print(f"[ERROR] Modbus connection failed: {e}")
            self.simulation_mode = True
            self.connected = True
            return True
    
    def disconnect(self):
        """Disconnect from Modbus"""
        if self.client and not self.simulation_mode:
            self.client.close()
        self.connected = False
    
    def write_coil(self, room_id: int, device_id: int, value: bool) -> bool:
        """
        Write single coil (device ON/OFF)
        
        Args:
            room_id: Room identifier
            device_id: Device identifier within room
            value: True = ON, False = OFF
        
        Returns:
            bool: Success status
        """
        room = self._get_room(room_id)
        if not room:
            return False
        
        device = self._get_device(room, device_id)
        if not device:
            return False
        
        slave_addr = room['modbus_addr']
        register = device['register']
        
        if self.simulation_mode:
            self.device_states[room_id][device_id] = value
            print(f"[SIM] Room {room_id}, Device {device_id}: {'ON' if value else 'OFF'}")
            return True
        
        try:
            result = self.client.write_coil(register, value, slave=slave_addr)
            if not result.isError():
                self.device_states[room_id][device_id] = value
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Write coil failed: {e}")
            return False
    
    def read_coil(self, room_id: int, device_id: int) -> bool:
        """Read single coil state"""
        room = self._get_room(room_id)
        if not room:
            return False
        
        device = self._get_device(room, device_id)
        if not device:
            return False
        
        if self.simulation_mode:
            return self.device_states.get(room_id, {}).get(device_id, False)
        
        try:
            slave_addr = room['modbus_addr']
            register = device['register']
            result = self.client.read_coils(register, 1, slave=slave_addr)
            if not result.isError():
                return result.bits[0]
            return False
        except Exception as e:
            print(f"[ERROR] Read coil failed: {e}")
            return self.device_states.get(room_id, {}).get(device_id, False)
    
    def read_all_devices(self, room_id: int) -> dict:
        """Read all device states for a room"""
        room = self._get_room(room_id)
        if not room:
            return {}
        
        states = {}
        for device in room['devices']:
            states[device['id']] = self.read_coil(room_id, device['id'])
        return states
    
    def get_device_state(self, room_id: int, device_id: int) -> bool:
        """Get cached device state"""
        return self.device_states.get(room_id, {}).get(device_id, False)
    
    def toggle_device(self, room_id: int, device_id: int) -> bool:
        """Toggle device state"""
        current_state = self.get_device_state(room_id, device_id)
        return self.write_coil(room_id, device_id, not current_state)
    
    def _get_room(self, room_id: int):
        """Get room config by ID"""
        for room in ROOMS:
            if room['id'] == room_id:
                return room
        return None
    
    def _get_device(self, room: dict, device_id: int):
        """Get device config by ID"""
        for device in room['devices']:
            if device['id'] == device_id:
                return device
        return None
    
    def get_active_power(self) -> float:
        """Calculate total active power consumption (Watts)"""
        total_power = 0.0
        for room in ROOMS:
            for device in room['devices']:
                if self.device_states.get(room['id'], {}).get(device['id'], False):
                    total_power += device['power']
        return total_power
    
    def get_room_power(self, room_id: int) -> float:
        """Calculate power consumption for a specific room"""
        room = self._get_room(room_id)
        if not room:
            return 0.0
        
        power = 0.0
        for device in room['devices']:
            if self.device_states.get(room_id, {}).get(device['id'], False):
                power += device['power']
        return power
