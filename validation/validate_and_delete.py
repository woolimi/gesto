import os
import sys
import shutil
import numpy as np
import cv2
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

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

def draw_hand(image, landmarks, label, color=(0, 255, 0), thickness=1):
    """
    Draws a single hand (21 landmarks) on the provided canvas/ROI.
    landmarks: shape (21, 3) or (21, 2)
    """
    h, w, _ = image.shape
    
    coords = []
    for point in landmarks:
        # Assuming normalized coordinates if max value <= 1.0, else pixel coordinates
        # But based on validate_dataset.py logic: x, y = int(point[0] * w), int(point[1] * h)
        # We'll stick to that assumption.
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
        cv2.putText(image, label, (wrist_coord[0] + 5, wrist_coord[1] - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

class HandDataViewer(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(640, 480)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #202020; border: 1px solid #444;")
        self.current_frame = None

    def update_frame(self, frame):
        """Updates the displayed frame."""
        if frame is None:
            self.clear()
            self.setText("No Image")
            return

        h, w, ch = frame.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        p = QPixmap.fromImage(convert_to_Qt_format)
        self.setPixmap(p)

class ValidateDeleteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dataset Validator")
        self.setGeometry(100, 100, 800, 600)
        
        # Data state
        self.file_list = []
        self.current_index = 0
        self.current_data = None
        self.frame_index = 0
        self.dataset_dir = ""
        self.deleted_dir = ""
        self.deleted_history = [] # Stack of (original_path, filename) for undo

        # UI Setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Info Labels
        self.info_label = QLabel("No directory loaded.")
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(self.info_label)

        self.stats_label = QLabel("")
        layout.addWidget(self.stats_label)

        # Viewer
        self.viewer = HandDataViewer()
        # Center the viewer
        viewer_container = QHBoxLayout()
        viewer_container.addStretch()
        viewer_container.addWidget(self.viewer)
        viewer_container.addStretch()
        layout.addLayout(viewer_container)

        # Controls
        controls_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("Previous (Left)")
        self.btn_prev.setShortcut(Qt.Key.Key_Left)
        self.btn_prev.clicked.connect(self.prev_file)
        
        self.btn_undo = QPushButton("Undo Delete (Ctrl+Z)")
        self.btn_undo.setShortcut("Ctrl+Z")
        self.btn_undo.clicked.connect(self.undo_delete)
        
        self.btn_delete = QPushButton("Delete (Del / Backspace)")
        self.btn_delete.setStyleSheet("background-color: #ffcccc; color: #cc0000; font-weight: bold;")
        self.btn_delete.setShortcut(Qt.Key.Key_Delete)
        # Also bind backspace
        self.btn_delete_alt =  QPushButton("Delete") # dummy helper for shortcut
        self.btn_delete_alt.setShortcut(Qt.Key.Key_Backspace)
        self.btn_delete_alt.clicked.connect(self.delete_current_file)
        self.btn_delete_alt.hide() 
        self.btn_delete.clicked.connect(self.delete_current_file)

        self.btn_pass = QPushButton("Pass / Next (Right / Space)")
        self.btn_pass.setStyleSheet("background-color: #ccffcc; color: #006600; font-weight: bold;")
        self.btn_pass.setShortcut(Qt.Key.Key_Right)
        # Also bind Space
        self.btn_pass_space = QPushButton("Pass")
        self.btn_pass_space.setShortcut(Qt.Key.Key_Space)
        self.btn_pass_space.clicked.connect(self.next_file)
        self.btn_pass_space.hide() # Hidden, just for shortcut
        self.btn_pass.clicked.connect(self.next_file)

        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_undo)
        controls_layout.addWidget(self.btn_delete)
        controls_layout.addWidget(self.btn_pass)
        
        layout.addLayout(controls_layout)

        # Timer for playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_frame)
        self.timer.start(33) # ~30 FPS

        # Initial Load
        self.select_directory()

    def select_directory(self):
        start_dir =  os.path.join(os.path.dirname(__file__), "..", "data_collector", "data")
        self.dataset_dir = QFileDialog.getExistingDirectory(self, "Select Dataset Directory", start_dir)
        
        if self.dataset_dir:
            self.deleted_dir = os.path.join(self.dataset_dir, "deleted")
            os.makedirs(self.deleted_dir, exist_ok=True)
            self.scan_directory()
        else:
            self.info_label.setText("No directory selected.")

    def scan_directory(self):
        path = Path(self.dataset_dir)
        # Exclude the deleted folder itself
        all_files = list(path.rglob("*.npy"))
        self.file_list = [f for f in all_files if "deleted" not in str(f.parent)]
        self.file_list.sort()
        
        self.current_index = 0
        if self.file_list:
            self.load_file(0)
        else:
            self.info_label.setText("No .npy files found.")
            self.viewer.update_frame(None)

    def load_file(self, index):
        if not self.file_list:
            return
        
        if index < 0 or index >= len(self.file_list):
            return

        self.current_index = index
        self.frame_index = 0
        file_path = self.file_list[index]
        
        try:
            self.current_data = np.load(file_path)
            # Update info
            self.info_label.setText(f"File: {file_path.name}")
            self.stats_label.setText(f"Index: {index + 1} / {len(self.file_list)} | Shape: {self.current_data.shape}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            self.info_label.setText(f"Error loading {file_path.name}")
            self.current_data = None

    def play_frame(self):
        if self.current_data is None:
            return

        data = self.current_data
        
        # Determine format
        # Supports (Frames, 42, 3), (Frames, 21, 3), etc.
        # Logic from validate_dataset.py
        
        valid_data = None
        
        # Reshape logic
        if data.ndim == 2:
            if data.shape[1] == 63:
                valid_data = data.reshape(-1, 21, 3)
            elif data.shape[1] == 126:
                valid_data = data.reshape(-1, 42, 3)
            elif data.shape[1] == 462: 
                valid_data = data.reshape(-1, 42, 11)
        elif data.ndim == 3:
            # (Frames, Points, Channels)
            valid_data = data

        if valid_data is None:
            return 

        # Loop frames
        num_frames = valid_data.shape[0]
        if num_frames == 0:
            return

        self.frame_index = (self.frame_index + 1) % num_frames
        
        # Create canvas
        canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Draw frame info
        cv2.putText(canvas, f"Frame: {self.frame_index}/{num_frames}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)

        frame_data = valid_data[self.frame_index]
        
        # Draw Hands
        # Check if 21 or 42 points
        num_points = frame_data.shape[0]
        
        if num_points == 42:
            # Right (0-21), Left (21-42) - assuming standard format in this project
            right_hand_pts = frame_data[0:21, 0:3]
            left_hand_pts = frame_data[21:42, 0:3]
            
            draw_hand(canvas, right_hand_pts, "Right", (0, 255, 0)) # Green
            draw_hand(canvas, left_hand_pts, "Left", (255, 0, 0))   # Blue
            
        elif num_points == 21:
            hand_pts = frame_data[0:21, 0:3]
            draw_hand(canvas, hand_pts, "Hand", (0, 255, 0))

        self.viewer.update_frame(canvas)

    def next_file(self):
        if self.current_index < len(self.file_list) - 1:
            self.load_file(self.current_index + 1)
        else:
             QMessageBox.information(self, "Finished", "End of file list.")

    def prev_file(self):
        if self.current_index > 0:
            self.load_file(self.current_index - 1)

    def delete_current_file(self):
        if not self.file_list:
            return
            
        current_file = self.file_list[self.current_index]
        filename = current_file.name
        dest_path = os.path.join(self.deleted_dir, filename)
        
        try:
            # Move file
            shutil.move(str(current_file), dest_path)
            print(f"Deleted (Moved): {current_file} -> {dest_path}")
            
            self.deleted_history.append((current_file, dest_path))
            
            # Remove from list
            del self.file_list[self.current_index]
            
            if self.file_list:
                # Stay at current index unless it was the last one
                if self.current_index >= len(self.file_list):
                    self.current_index = len(self.file_list) - 1
                self.load_file(self.current_index)
            else:
                self.info_label.setText("All files deleted.")
                self.viewer.update_frame(None)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")

    def undo_delete(self):
        if not self.deleted_history:
            return

        original_path, current_path = self.deleted_history.pop()
        
        try:
            if os.path.exists(current_path):
                shutil.move(current_path, str(original_path))
                print(f"Restored: {current_path} -> {original_path}")
                
                # Re-insert and sort
                self.file_list.append(original_path)
                self.file_list.sort()
                
                # Find new index
                try:
                    new_index = self.file_list.index(original_path)
                    self.load_file(new_index)
                except ValueError:
                    # Should not happen
                    self.load_file(self.current_index)
                    
            else:
                QMessageBox.warning(self, "Error", f"File not found in deleted folder: {current_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to undo delete: {e}")


def main():
    app = QApplication(sys.argv)
    window = ValidateDeleteApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
