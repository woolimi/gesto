
import os
import shutil
import subprocess
from pathlib import Path
import numpy as np

# Configuration
TEST_DIR = Path("/tmp/reverse_test_data")
INPUT_GESTURE = "Swipe_Up"
OUTPUT_GESTURE = "Swipe_Down"
SCRIPT_PATH = "/home/robo/projects/first_project/data_collector/reverse_gesture_npy.py"

def setup_test_data():
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    
    gesture_dir = TEST_DIR / "Gesture" / INPUT_GESTURE
    gesture_dir.mkdir(parents=True)
    
    # Create a dummy .npy file (30, 42, 11)
    # Mark the first frame with a specific value to verify reversal
    dummy_data = np.zeros((30, 42, 11), dtype=np.float32)
    dummy_data[0, :, 0] = 1.0 # First frame X = 1.0
    dummy_data[-1, :, 0] = 0.0 # Last frame X = 0.0
    
    filename = f"{INPUT_GESTURE}_987654321.npy"
    np.save(gesture_dir / filename, dummy_data)
    print(f"Created test file: {gesture_dir / filename}")
    return gesture_dir / filename

def run_reverse_script():
    cmd = [
        "python3", SCRIPT_PATH,
        "--gesture", INPUT_GESTURE,
        "--output-gesture", OUTPUT_GESTURE,
        "--data-dir", str(TEST_DIR),
        "--mode", "Gesture"
    ]
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"Output: {result.stdout}")

def verify_results():
    out_dir = TEST_DIR / "Gesture" / OUTPUT_GESTURE
    expected_filename = f"{OUTPUT_GESTURE}_987654321.npy"
    expected_path = out_dir / expected_filename
    
    if expected_path.exists():
        print(f"SUCCESS: File renamed correctly to {expected_filename}")
        
        data = np.load(expected_path)
        print(f"File shape: {data.shape}")
        
        # Verify shape
        if data.shape == (30, 42, 3):
            print("SUCCESS: Shape is correct (30, 42, 3)")
        else:
             print(f"FAILED: Expected shape (30, 42, 3), got {data.shape}")
             
        # Verify Reversal
        # Original: Frame 0 has X=1.0, Frame 29 has X=0.0
        # Reversed: Frame 0 should have X=0.0, Frame 29 should have X=1.0
        
        frame_0_val = data[0, 0, 0]
        frame_last_val = data[-1, 0, 0]
        
        print(f"Frame 0 X: {frame_0_val} (Expected 0.0)")
        print(f"Frame 29 X: {frame_last_val} (Expected 1.0)")
        
        if np.isclose(frame_0_val, 0.0) and np.isclose(frame_last_val, 1.0):
            print("SUCCESS: Data is reversed in time.")
        else:
            print("FAILED: Data reversal check failed.")

    else:
        print(f"FAILED: File not found at {expected_path}")
        print(f"Contents of {out_dir}: {list(out_dir.glob('*')) if out_dir.exists() else 'Dir does not exist'}")

if __name__ == "__main__":
    setup_test_data()
    run_reverse_script()
    verify_results()
    # Clean up
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
