# -*- coding: utf-8 -*-
"""
Test Firebase Connection
Run this on Pi 4 to check if Firebase works
"""

print("=" * 50)
print("FIREBASE CONNECTION TEST")
print("=" * 50)

# Step 1: Check if pyrebase4 is installed
print("\n[1] Checking pyrebase4...")
try:
    import pyrebase
    print("    OK - pyrebase4 is installed")
except ImportError as e:
    print(f"    ERROR - pyrebase4 not installed!")
    print("    Run: pip install pyrebase4")
    exit(1)

# Step 2: Firebase config
print("\n[2] Firebase Configuration...")
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDTvGflmFqArRm4MvJXNCEU6F7GGZ-vsFU",
    "authDomain": "datn-426e1.firebaseapp.com",
    "databaseURL": "https://datn-426e1-default-rtdb.firebaseio.com",
    "projectId": "datn-426e1",
    "storageBucket": "datn-426e1.firebasestorage.app",
    "messagingSenderId": "496143525778",
    "appId": "1:496143525778:web:e59595f5bee532f40d834b"
}
print(f"    Database URL: {FIREBASE_CONFIG['databaseURL']}")

# Step 3: Initialize Firebase
print("\n[3] Connecting to Firebase...")
try:
    firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
    db = firebase.database()
    print("    OK - Firebase initialized")
except Exception as e:
    print(f"    ERROR - Failed to initialize: {e}")
    exit(1)

# Step 4: Test READ
print("\n[4] Testing READ from Firebase...")
try:
    data = db.child("power_management").get().val()
    if data:
        print(f"    OK - Read data: {list(data.keys()) if isinstance(data, dict) else data}")
    else:
        print("    OK - No data yet (database is empty)")
except Exception as e:
    print(f"    ERROR - Read failed: {e}")
    print("    Check Firebase Rules - should allow read")

# Step 5: Test WRITE
print("\n[5] Testing WRITE to Firebase...")
try:
    # Write test data
    db.child("power_management").child("test").set({
        "message": "Hello from Pi 4",
        "timestamp": "test"
    })
    print("    OK - Write successful!")
    
    # Verify write
    verify = db.child("power_management").child("test").get().val()
    print(f"    Verify: {verify}")
    
    # Clean up test data
    db.child("power_management").child("test").remove()
    print("    Test data cleaned up")
except Exception as e:
    print(f"    ERROR - Write failed: {e}")
    print("    Check Firebase Rules - should allow write")
    print("\n    Go to Firebase Console -> Realtime Database -> Rules")
    print('    Set rules to: {"rules": {".read": true, ".write": true}}')

# Step 6: Test device control path
print("\n[6] Testing device control path...")
try:
    # Write device state
    db.child("power_management").child("control").child("room1").child("device0").set(True)
    print("    OK - Set room1/device0 = True")
    
    # Read it back
    state = db.child("power_management").child("control").child("room1").child("device0").get().val()
    print(f"    Read back: {state}")
    
    # Toggle it
    db.child("power_management").child("control").child("room1").child("device0").set(False)
    print("    OK - Set room1/device0 = False")
    
except Exception as e:
    print(f"    ERROR - Device control test failed: {e}")

# Step 7: Test streaming (listening for changes)
print("\n[7] Testing stream listener...")
print("    (This will listen for 5 seconds)")

import time
import threading

stream_received = False

def stream_handler(message):
    global stream_received
    stream_received = True
    print(f"    Stream received: event={message['event']}, path={message['path']}, data={message['data']}")

try:
    stream = db.child("power_management").child("control").stream(stream_handler)
    print("    Stream started, waiting 3 seconds...")
    time.sleep(3)
    stream.close()
    
    if stream_received:
        print("    OK - Stream is working!")
    else:
        print("    WARNING - No stream event received (might be OK if no data)")
except Exception as e:
    print(f"    ERROR - Stream failed: {e}")

print("\n" + "=" * 50)
print("TEST COMPLETE")
print("=" * 50)
print("\nIf all tests passed, Firebase connection is working.")
print("If any test failed, check:")
print("  1. Internet connection on Pi 4")
print("  2. Firebase Realtime Database Rules (allow read/write)")
print("  3. Correct database URL")
