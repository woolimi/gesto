import os
import glob
import numpy as np

# --- Configuration ---
DATA_ROOT = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "data", "converted_gesture")

# Feature Indices
# 0-2: x, y, z (Original)
# 3: Is_Fist (Left)
# 4: Pinch_Dist (Left)
# 5: Thumb_V (Left)
# 6: Index_Z_V (Left)
# 7: Is_Fist (Right)
# 8: Pinch_Dist (Right)
# 9: Thumb_V (Right)
# 10: Index_Z_V (Right)
NUM_CHANNELS = 11

# Landmark Indices (MediaPipe Hands)
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20

def calculate_euclidean_dist(p1, p2):
    return np.linalg.norm(p1 - p2)

def is_fist(landmarks):
    """
    Check if the hand is in a fist state.
    A hand is considered a fist if ALL 4 fingers (Index, Middle, Ring, Pinky) are curled.
    Curled condition: Distance(Wrist, Tip) < Distance(Wrist, PIP)
    This intrinsic metric is robust to hand rotation.
    """
    wrist = landmarks[WRIST]
    
    fingers = [
        (INDEX_PIP, INDEX_TIP),
        (MIDDLE_PIP, MIDDLE_TIP),
        (RING_PIP, RING_TIP),
        (PINKY_PIP, PINKY_TIP)
    ]
    
    curled_count = 0
    for pip_idx, tip_idx in fingers:
        dist_tip = calculate_euclidean_dist(wrist, landmarks[tip_idx])
        dist_pip = calculate_euclidean_dist(wrist, landmarks[pip_idx])
        if dist_tip < dist_pip:
            curled_count += 1
            
    return 1.0 if curled_count == 4 else 0.0

def process_hand_features(landmarks, prev_landmarks):
    """
    Calculate 4 features for a single hand (21 landmarks).
    Features: [Is_Fist, Pinch_Dist, Thumb_V, Index_Z_V]
    """
    # 1. Is_Fist
    fist_val = is_fist(landmarks)
    
    # 2. Pinch_Dist (Thumb Tip - Index Tip)
    pinch_dist = calculate_euclidean_dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP])
    
    # 3. Thumb_V (y velocity)
    thumb_v = 0.0
    if prev_landmarks is not None:
        thumb_v = landmarks[THUMB_TIP][1] - prev_landmarks[THUMB_TIP][1]
        
    # 4. Index_Z_V (z velocity)
    index_z_v = 0.0
    if prev_landmarks is not None:
        index_z_v = landmarks[INDEX_TIP][2] - prev_landmarks[INDEX_TIP][2]
        
    return [fist_val, pinch_dist, thumb_v, index_z_v]

def convert_file(file_path):
    try:
        data = np.load(file_path) # Shape: (30, 42, 3)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return

    frames, landmarks_count, coords = data.shape
    if landmarks_count != 42 or coords != 3:
        print(f"Skipping {file_path}: Invalid shape {data.shape}")
        return

    # Create new array
    new_data = np.zeros((frames, landmarks_count, NUM_CHANNELS), dtype=np.float32)
    
    # Copy original coordinates (Channels 0-2)
    new_data[:, :, 0:3] = data

    prev_right = None
    prev_left = None

    for i in range(frames):
        # Extract Hands (Right: 0-20, Left: 21-41) based on data_collector logic
        # Note: data_collector uses: right_slot + left_slot
        right_hand = data[i, 0:21, :]
        left_hand = data[i, 21:42, :]
        
        # Calculate Features
        # Left Hand Features (Channels 3-6)
        # Note: Left hand is indices 21-41 in data, but we pass the slice which is 0-20 relative
        left_feats = process_hand_features(left_hand, prev_left)
        
        # Right Hand Features (Channels 7-10)
        right_feats = process_hand_features(right_hand, prev_right)
        
        # Assign to all landmarks in the frame
        # Broadcasting strategy: features are hand-global, so we assign same value to all landmarks?
        # The user request said "data shape (30, 42, 10)" - which implies per-landmark channels.
        # Usually global features are repeated across landmarks or stored separately.
        # Given the shape (30, 42, 11), we must repeat the feature values for each landmark.
        # Channel 3-6: Left Hand Features -> Assign to Left Hand Landmarks? Or All?
        # User said: "Channel 3~6: Left hand data... Channel 7~10: Right hand data"
        # It implies these channels exist for ALL 42 landmarks.
        
        new_data[i, :, 3] = left_feats[0] # Is_Fist
        new_data[i, :, 4] = left_feats[1] # Pinch_Dist
        new_data[i, :, 5] = left_feats[2] # Thumb_V
        new_data[i, :, 6] = left_feats[3] # Index_Z_V
        
        new_data[i, :, 7] = right_feats[0] # Is_Fist
        new_data[i, :, 8] = right_feats[1] # Pinch_Dist
        new_data[i, :, 9] = right_feats[2] # Thumb_V
        new_data[i, :, 10] = right_feats[3] # Index_Z_V
        
        prev_right = right_hand
        prev_left = left_hand

    # Save
    rel_path = os.path.relpath(file_path, DATA_ROOT)
    save_path = os.path.join(OUTPUT_ROOT, rel_path)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    np.save(save_path, new_data)
    # print(f"Converted: {rel_path} -> {new_data.shape}")

def main():
    if not os.path.exists(DATA_ROOT):
        print(f"Data directory not found: {DATA_ROOT}")
        return

    npy_files = glob.glob(os.path.join(DATA_ROOT, "**/*.npy"), recursive=True)
    print(f"Found {len(npy_files)} files to convert.")
    
    # Filter out already converted files if output is inside data root (avoid recursion loop if mistakenly placed)
    # But here OUTPUT_ROOT is 'data_collector/data/converted_gesture', so it IS inside DATA_ROOT.
    # We must exclude the output directory from search.
    
    files_to_process = []
    for f in npy_files:
        if "converted_gesture" in f:
            continue
        files_to_process.append(f)
        
    print(f"Processing {len(files_to_process)} files...")
    
    for f in files_to_process:
        convert_file(f)
        
    print("Conversion Complete.")

if __name__ == "__main__":
    main()
