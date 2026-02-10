import os
import sys
import numpy as np
import cv2
import random
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

# Filtered hand connections: Thumb and Index only
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),      # Index
]

# Global QApplication instance to avoid re-initialization issues
_q_app = None

def get_qapp():
    global _q_app
    if _q_app is None:
        _q_app = QApplication.instance()
        if _q_app is None:
            _q_app = QApplication(sys.argv)
    return _q_app

def select_directory():
    """
    Opens a folder selection dialog and returns the selected path.
    """
    get_qapp()
    dir_path = QFileDialog.getExistingDirectory(
        None, 
        "Select Dataset Directory", 
        os.path.join(os.path.dirname(__file__), "..", "data_collector", "data")
    )
    return dir_path

def draw_landmarks(image, landmarks, color=(0, 255, 0), thickness=2):
    """
    Draws hand landmarks and connections on a canvas.
    """
    h, w, _ = image.shape
    
    # Handle both 21 (one hand) and 42 (two hands) landmarks
    n_pts = len(landmarks)
    for start_offset in range(0, n_pts, 21):
        pts_part = landmarks[start_offset : start_offset + 21]
        coords = []
        for point in pts_part:
            x, y = int(point[0] * w), int(point[1] * h)
            coords.append((x, y))
            
        # Draw connections
        for connection in HAND_CONNECTIONS:
            start_idx, end_idx = connection
            if start_idx < len(coords) and end_idx < len(coords):
                cv2.line(image, coords[start_idx], coords[end_idx], color, thickness)

def visualize_dataset_overlaid(valid_items, title="Overlaid Pinch Visualization"):
    """
    Visualizes multiple gesture data sequences overlaid on a single canvas.
    Sequences are colored based on the participant name.
    """
    if not valid_items:
        print("No data to visualize.")
        return

    # Constants
    WIDTH, HEIGHT = 640, 480
    FPS = 30
    delay = int(1000 / FPS)
    
    # Extract unique names and assign colors
    unique_names = sorted(list(set(item[1] for item in valid_items)))
    name_to_color = {}
    
    # Generate distinct colors for each name
    for i, name in enumerate(unique_names):
        hue = int(180 * i / max(1, len(unique_names)))
        hsv_color = np.uint8([[[hue, 200, 255]]])
        bgr_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)[0][0]
        name_to_color[name] = tuple(map(int, bgr_color))

    # Find max frame count
    max_frames = max(len(item[0]) for item in valid_items)
    
    print(f"Starting overlaid pinch visualization of {len(valid_items)} sequences ({len(unique_names)} participants).")
    print("Controls: 'q' to quit, 'p' to pause, any key to resume.")

    while True:
        for f in range(max_frames):
            canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            
            # Overlay each sequence frame
            # Overlay each sequence frame
            for i, (data, name) in enumerate(valid_items):
                if f < len(data):
                    # If 11-channel, use only first 3 for drawing
                    landmarks = data[f][:, 0:3] if data[f].shape[1] > 3 else data[f]
                    draw_landmarks(canvas, landmarks, color=name_to_color[name], thickness=1)
                    
                    # Visualize Features for the FIRST item only (to avoid clutter)
                    if i == 0 and data[f].shape[1] >= 11:
                        # L: 3-6, R: 7-10
                        # Features are identical for all landmarks in a hand, so pick 0 (wrist)
                        l_fist = data[f][21, 3] # Left Wrist index 21
                        l_pinch = data[f][21, 4]
                        l_thumb_v = data[f][21, 5]
                        l_index_z_v = data[f][21, 6]
                        
                        r_fist = data[f][0, 7] # Right Wrist index 0
                        r_pinch = data[f][0, 8]
                        r_thumb_v = data[f][0, 9]
                        r_index_z_v = data[f][0, 10]
                        
                        # Display Text on Bottom
                        info_y = HEIGHT - 60
                        cv2.putText(canvas, f"L_Fist: {l_fist:.0f}  | L_Pinch: {l_pinch:.3f} | L_ThumbV: {l_thumb_v:.3f}", 
                                    (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                        cv2.putText(canvas, f"R_Fist: {r_fist:.0f}  | R_Pinch: {r_pinch:.3f} | R_ThumbV: {r_thumb_v:.3f}", 
                                    (10, info_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                        cv2.putText(canvas, f"L_IdxZ_V: {l_index_z_v:.3f} | R_IdxZ_V: {r_index_z_v:.3f}", 
                                    (10, info_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # Overlay info
            cv2.putText(canvas, f"Frame: {f}/{max_frames}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(canvas, f"Count: {len(valid_items)} files ({len(unique_names)} names)", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            # Legend for names
            for j, name in enumerate(unique_names):
                cv2.putText(canvas, name, (WIDTH - 100, 30 + j * 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, name_to_color[name], 2)
            
            cv2.imshow(title, canvas)
            
            key = cv2.waitKey(delay) & 0xFF
            if key == ord('q'):
                cv2.destroyAllWindows()
                return
            if key == ord('p'):
                cv2.waitKey(-1)

        # Loop or exit using GUI
        get_qapp()
        reply = QMessageBox.question(
            None, 
            "Replay?", 
            "Playback finished. Do you want to replay?",
            QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Close,
            QMessageBox.StandardButton.Retry
        )
        if reply == QMessageBox.StandardButton.Retry:
            continue
        else:
            break
            
    cv2.destroyAllWindows()

def validate_dataset(directory_path):
    """
    Scans the given directory for .npy files and validates their shapes.
    Returns a list of (numpy_array, name) for visualization.
    """
    print(f"Scanning directory: {directory_path}\n")
    
    path = Path(directory_path)
    if not path.is_dir():
        print(f"Error: {directory_path} is not a valid directory.")
        return []

    npy_files = list(path.rglob("*.npy"))
    if not npy_files:
        print("No .npy files found in the directory.")
        return []

    total_files = len(npy_files)
    stats = {}
    valid_items = []
    invalid_files = []
    errors = []

    print(f"Found {total_files} .npy files. Validating...\n")

    for file_path in npy_files:
        try:
            # Extract name from filename {filename}_01_{name}.npy
            name = file_path.stem.split('_')[-1]
            
            data = np.load(file_path)
            shape = data.shape
            
            # Shape statistics
            shape_str = str(shape)
            stats[shape_str] = stats.get(shape_str, 0) + 1
            
            # Validation logic
            current_valid_data = None
            if data.ndim == 2:
                if data.shape[1] == 63:
                    current_valid_data = data.reshape(-1, 21, 3)
                elif data.shape[1] == 126:
                    current_valid_data = data.reshape(-1, 42, 3)
                elif data.shape[1] == 462: # 42 * 11
                    current_valid_data = data.reshape(-1, 42, 11)
            elif data.ndim == 3:
                if data.shape[1] == 21 and data.shape[2] == 3:
                    current_valid_data = data
                elif data.shape[1] == 42 and data.shape[2] == 3:
                    current_valid_data = data
                elif data.shape[1] == 42 and data.shape[2] == 11:
                    current_valid_data = data
            
            if current_valid_data is not None:
                valid_items.append((current_valid_data, name))
            else:
                invalid_files.append((file_path, shape_str))
                
        except Exception as e:
            errors.append((file_path, str(e)))

    # Report Summary
    print("-" * 40)
    print("Validation Summary (Pinch Focus)")
    print("-" * 40)
    print(f"Total files processed: {total_files}")
    print(f"Valid sequences:     {len(valid_items)}")
    print(f"Invalid shapes:      {len(invalid_files)}")
    print(f"Failed to load:      {len(errors)}")
    print("-" * 40)

    if stats:
        print("\nShape Distribution:")
        for shape_str, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {shape_str}: {count} files")

    return valid_items

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        print("No directory provided via command line. Opening folder selection dialog...")
        target_dir = select_directory()
        
    if target_dir:
        valid_items = validate_dataset(target_dir)
        
        if valid_items:
            visualize_dataset_overlaid(valid_items, title=f"Pinch Overlay: {os.path.basename(target_dir)}")
        else:
            print("No valid sequences found to visualize.")
    else:
        print("No directory selected.")
