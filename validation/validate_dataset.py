import os
import sys
import numpy as np
import cv2
import random
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

# Standard MediaPipe hand connections including palm
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),      # Index
    (0, 9), (9, 10), (10, 11), (11, 12), # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    # Palm connections
    (5, 9), (9, 13), (13, 17), (0, 17)
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

def draw_hand(image, landmarks, label, color=(0, 255, 0), thickness=1):
    """
    Draws a single hand (21 landmarks) on the provided canvas/ROI.
    """
    h, w, _ = image.shape
    
    coords = []
    for point in landmarks:
        x, y = int(point[0] * w), int(point[1] * h)
        coords.append((x, y))
        
    # Draw connections
    for connection in HAND_CONNECTIONS:
        start_idx, end_idx = connection
        if start_idx < len(coords) and end_idx < len(coords):
            cv2.line(image, coords[start_idx], coords[end_idx], color, thickness)

    # Draw points (circles)
    for j, coord in enumerate(coords):
        # Wrist is slightly larger
        radius = 3 if j == 0 else 2
        cv2.circle(image, coord, radius, color, -1)
        
    # Draw hand label at wrist
    if coords:
        wrist_coord = coords[0]
        # Offset label slightly
        cv2.putText(image, label, (wrist_coord[0] + 5, wrist_coord[1] - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

def visualize_dataset_overlaid(valid_items, title="Overlaid Dataset Visualization", start_idx=0, total_count=None):
    """
    Visualizes multiple gesture data sequences overlaid on a single canvas.
    Sequences are colored based on the participant name.
    """
    if not valid_items:
        print("No data to visualize.")
        return QMessageBox.StandardButton.Close
    
    if total_count is None:
        total_count = len(valid_items)
    
    end_idx = start_idx + len(valid_items)

    # Revised Layout: Split Screen (Left Panel | Right Panel)
    PANEL_WIDTH, PANEL_HEIGHT = 640, 480
    TOTAL_WIDTH = PANEL_WIDTH * 2
    
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
    
    print(f"Starting overlaid visualization of {len(valid_items)} sequences ({len(unique_names)} participants).")
    print("Controls: 'q' to quit, 'p' to pause, any key to resume.")

    for f in range(max_frames):
        canvas = np.zeros((PANEL_HEIGHT, TOTAL_WIDTH, 3), dtype=np.uint8)
        
        # Draw Separator
        cv2.line(canvas, (PANEL_WIDTH, 0), (PANEL_WIDTH, PANEL_HEIGHT), (100, 100, 100), 2)
        
        # Headers/Titles
        cv2.putText(canvas, "LEFT HAND DATA (Left Hand, Ch 21-41)", (10, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(canvas, "RIGHT HAND DATA (Right Hand, Ch 0-20)", (PANEL_WIDTH + 10, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        # Overlays
        first_valid_features = False # Flag to print features only once per frame
        
        for i, (data, name) in enumerate(valid_items):
            if f < len(data):
                color = name_to_color[name]
                
                # Check shapes and Extract Hands
                # Assumption: data shape is (Frames, 42, C)
                # Right Hand: 0-21, Left Hand: 21-42
                
                if data[f].shape[0] == 42:
                    right_hand_pts = data[f][0:21, 0:3]
                    left_hand_pts = data[f][21:42, 0:3]
                    
                    # Draw Left Hand on Left Panel (canvas[:, :640])
                    # Note: We must create a view or pass the slice.
                    draw_hand(canvas[:, :PANEL_WIDTH], left_hand_pts, "L", color, thickness=1)
                    
                    # Draw Right Hand on Right Panel (canvas[:, 640:])
                    draw_hand(canvas[:, PANEL_WIDTH:], right_hand_pts, "R", color, thickness=1)

                    # Visualize Features for the FIRST item only (to avoid clutter)
                    if not first_valid_features and data[f].shape[1] >= 11:
                        first_valid_features = True
                        
                        # Extract Features
                        # Left Hand Features are at indices 21, channels 3-6
                        l_fist = data[f][21, 3] 
                        l_pinch = data[f][21, 4]
                        l_thumb_v = data[f][21, 5]
                        l_index_z_v = data[f][21, 6]
                        
                        # Right Hand Features are at indices 0, channels 7-10
                        r_fist = data[f][0, 7] 
                        r_pinch = data[f][0, 8]
                        r_thumb_v = data[f][0, 9]
                        r_index_z_v = data[f][0, 10]
                        
                        # Display Text on Bottom of Each Panel
                        info_y = PANEL_HEIGHT - 40
                        
                        # Semi-transparent background
                        cv2.rectangle(canvas, (0, info_y - 20), (TOTAL_WIDTH, PANEL_HEIGHT), (20, 20, 20), -1)
                        
                        # Left Info
                        cv2.putText(canvas, f"Fist:{l_fist:.0f} Pinch:{l_pinch:.3f}", 
                                    (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
                        cv2.putText(canvas, f"ThV:{l_thumb_v:.3f} IdxZV:{l_index_z_v:.3f}", 
                                    (10, info_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
                        
                        # Right Info
                        cv2.putText(canvas, f"Fist:{r_fist:.0f} Pinch:{r_pinch:.3f}", 
                                    (PANEL_WIDTH + 10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
                        cv2.putText(canvas, f"ThV:{r_thumb_v:.3f} IdxZV:{r_index_z_v:.3f}", 
                                    (PANEL_WIDTH + 10, info_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        
        # General Info
        cv2.putText(canvas, f"Frame: {f}/{max_frames}", (10, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(canvas, f"Batch: {start_idx+1}-{end_idx} / {total_count}", (10, 75), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow(title, canvas)
        
        key = cv2.waitKey(delay) & 0xFF
        if key == ord('q'):
            cv2.destroyAllWindows()
            return QMessageBox.StandardButton.Close
        if key == ord('p'):
            cv2.waitKey(-1)

    # Loop or exit using GUI
    get_qapp()
    
    has_more = end_idx < total_count
    msg = f"Batch {start_idx+1}-{end_idx} finished."
    if has_more:
        msg += f"\nShow next {min(50, total_count - end_idx)} items?"
        buttons = QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Close
        default_btn = QMessageBox.StandardButton.Retry
    else:
        msg += "\nAll items shown."
        buttons = QMessageBox.StandardButton.Close
        default_btn = QMessageBox.StandardButton.Close

    reply = QMessageBox.question(
        None, 
        "Finished", 
        msg,
        buttons,
        default_btn
    )
    
    cv2.destroyAllWindows()
    return reply

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
    print("Validation Summary")
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
            batch_size = 50
            total_count = len(valid_items)
            for i in range(0, total_count, batch_size):
                batch = valid_items[i : i + batch_size]
                reply = visualize_dataset_overlaid(
                    batch, 
                    title=f"Overlaid ({i+1}-{min(i+batch_size, total_count)}): {os.path.basename(target_dir)}",
                    start_idx=i,
                    total_count=total_count
                )
                if reply != QMessageBox.StandardButton.Retry:
                    break
        else:
            print("No valid sequences found to visualize.")
    else:
        print("No directory selected.")
