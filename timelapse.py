import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QLabel, QSpinBox, QWidget, QFileDialog,
                            QProgressBar, QMessageBox, QLineEdit, QComboBox, 
                            QSlider, QGroupBox, QCheckBox, QFormLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QImage

class CaptureThread(QThread):
    update_frame = pyqtSignal(np.ndarray)
    update_status = pyqtSignal(str)
    update_storage = pyqtSignal(int, int)  # current_size, max_size
    
    def __init__(self, interval=60, output_dir="captures", compression=85, 
                 max_storage_mb=1000, auto_cleanup=False, resolution=(0, 0)):
        super().__init__()
        self.interval = interval  # Interval in seconds
        self.active = False
        self.output_dir = output_dir
        self.compression = compression  # JPEG compression level (0-100)
        self.max_storage_mb = max_storage_mb  # Maximum storage in MB
        self.auto_cleanup = auto_cleanup  # Auto cleanup when storage limit reached
        self.resolution = resolution  # Desired resolution (width, height)
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def run(self):
        self.active = True
        self.camera = cv2.VideoCapture(0)
        
        if not self.camera.isOpened():
            self.update_status.emit("Gagal membuka kamera!")
            return
        
        capture_count = 0
        last_capture_time = 0
        last_storage_check = 0
        
        while self.active:
            ret, frame = self.camera.read()
            if not ret:
                self.update_status.emit("Gagal mengambil frame dari kamera!")
                break
                
            # Flip horizontally for selfie-view
            frame = cv2.flip(frame, 1)
            
            # Resize if resolution is specified
            if self.resolution != (0, 0) and self.resolution[0] > 0 and self.resolution[1] > 0:
                frame = cv2.resize(frame, self.resolution, interpolation=cv2.INTER_AREA)
            
            # Update the displayed frame
            self.update_frame.emit(frame)
            
            # Check if it's time to capture a frame
            current_time = time.time()
            if current_time - last_capture_time >= self.interval:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(self.output_dir, f"capture_{timestamp}.jpg")
                
                # Save with compression
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.compression]
                cv2.imwrite(filename, frame, encode_param)
                
                capture_count += 1
                last_capture_time = current_time
                self.update_status.emit(f"Capture #{capture_count} tersimpan: {filename}")
                
                # Check storage usage every 5 captures or if auto cleanup is enabled
                if capture_count % 5 == 0 or self.auto_cleanup:
                    current_storage = self.get_directory_size_mb(self.output_dir)
                    self.update_storage.emit(current_storage, self.max_storage_mb)
                    
                    # If storage exceeds limit and auto cleanup is enabled, remove oldest files
                    if self.auto_cleanup and current_storage > self.max_storage_mb:
                        self.cleanup_old_files(current_storage - self.max_storage_mb * 0.8)  # Clean until 80% usage
            
            # Sleep a bit to reduce CPU usage
            time.sleep(0.03)
        
        # Release the camera when done
        self.camera.release()
    
    def stop(self):
        self.active = False
        self.wait()
    
    def get_directory_size_mb(self, directory):
        """Get directory size in MB"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for f in filenames:
                if f.endswith('.jpg'):
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)  # Convert to MB
    
    def cleanup_old_files(self, size_to_remove_mb):
        """Remove oldest JPG files until specified amount of space is freed"""
        self.update_status.emit(f"Membersihkan file lama untuk menghemat ruang...")
        files = []
        for f in os.listdir(self.output_dir):
            if f.endswith('.jpg'):
                path = os.path.join(self.output_dir, f)
                files.append((path, os.path.getctime(path)))
        
        # Sort files by creation time
        files.sort(key=lambda x: x[1])
        
        # Delete oldest files until we've freed enough space
        size_removed = 0
        files_removed = 0
        for file_path, _ in files:
            if size_removed >= size_to_remove_mb * 1024 * 1024:
                break
                
            file_size = os.path.getsize(file_path)
            os.remove(file_path)
            size_removed += file_size
            files_removed += 1
            
        self.update_status.emit(f"Pembersihan selesai: {files_removed} file dihapus ({size_removed/(1024*1024):.1f} MB)")

class TimelapseApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Work Timelapse Recorder")
        self.setMinimumSize(800, 600)
        
        self.capture_thread = None
        self.output_dir = "captures"
        
        # Default settings
        self.compression = 85
        self.max_storage_mb = 1000  # 1 GB default
        self.auto_cleanup = False
        self.resolution = (0, 0)  # Default to camera resolution
        
        self.init_ui()
    
    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Camera view
        self.camera_view = QLabel("Kamera akan ditampilkan di sini")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setStyleSheet("background-color: #222; color: white;")
        main_layout.addWidget(self.camera_view)
        
        # Controls area
        controls_layout = QHBoxLayout()
        
        # Left controls
        left_controls = QVBoxLayout()
        
        # Output directory selection
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Direktori Output:")
        self.dir_input = QLineEdit(self.output_dir)
        self.dir_input.setReadOnly(True)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_directory)
        
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_btn)
        left_controls.addLayout(dir_layout)
        
        # Storage management box
        storage_group = QGroupBox("Pengaturan Penyimpanan")
        storage_layout = QFormLayout()
        
        # Compression quality slider
        compress_layout = QHBoxLayout()
        self.compress_slider = QSlider(Qt.Horizontal)
        self.compress_slider.setRange(50, 100)
        self.compress_slider.setValue(self.compression)
        self.compress_slider.setTickPosition(QSlider.TicksBelow)
        self.compress_slider.setTickInterval(10)
        self.compress_slider.valueChanged.connect(self.update_compression_label)
        
        self.compress_label = QLabel(f"Kompresi JPG: {self.compression}%")
        compress_layout.addWidget(self.compress_label)
        compress_layout.addWidget(self.compress_slider)
        storage_layout.addRow(compress_layout)
        
        # Storage limit
        storage_limit_layout = QHBoxLayout()
        self.storage_limit_input = QSpinBox()
        self.storage_limit_input.setRange(100, 10000)
        self.storage_limit_input.setValue(self.max_storage_mb)
        self.storage_limit_input.setSingleStep(100)
        self.storage_limit_input.setSuffix(" MB")
        storage_limit_layout.addWidget(QLabel("Batas Penyimpanan:"))
        storage_limit_layout.addWidget(self.storage_limit_input)
        storage_layout.addRow(storage_limit_layout)
        
        # Auto cleanup checkbox
        self.auto_cleanup_check = QCheckBox("Otomatis hapus file lama saat penuh")
        self.auto_cleanup_check.setChecked(self.auto_cleanup)
        storage_layout.addRow(self.auto_cleanup_check)
        
        # Resolution options
        resolution_layout = QHBoxLayout()
        self.resolution_select = QComboBox()
        self.resolution_select.addItem("Asli dari Kamera", (0, 0))
        self.resolution_select.addItem("720p (1280x720)", (1280, 720))
        self.resolution_select.addItem("480p (854x480)", (854, 480))
        self.resolution_select.addItem("360p (640x360)", (640, 360))
        resolution_layout.addWidget(QLabel("Resolusi:"))
        resolution_layout.addWidget(self.resolution_select)
        storage_layout.addRow(resolution_layout)
        
        # Current storage usage
        self.storage_progress = QProgressBar()
        self.storage_progress.setRange(0, 100)
        self.storage_progress.setValue(0)
        storage_layout.addRow("Penggunaan:", self.storage_progress)
        
        # Clean storage button
        self.clean_storage_btn = QPushButton("Bersihkan File Lama")
        self.clean_storage_btn.clicked.connect(self.cleanup_storage)
        storage_layout.addRow(self.clean_storage_btn)
        
        storage_group.setLayout(storage_layout)
        left_controls.addWidget(storage_group)
        
        # Interval selection
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Interval Capture (detik):")
        self.interval_input = QSpinBox()
        self.interval_input.setRange(5, 3600)
        self.interval_input.setValue(60)
        self.interval_input.setSingleStep(5)
        
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_input)
        left_controls.addLayout(interval_layout)
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Kamera:")
        self.camera_select = QComboBox()
        self.camera_select.addItem("Default Camera")
        
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_select)
        left_controls.addLayout(camera_layout)
        
        controls_layout.addLayout(left_controls)
        
        # Right controls (buttons)
        right_controls = QVBoxLayout()
        
        self.start_btn = QPushButton("Mulai Timelapse")
        self.start_btn.clicked.connect(self.start_timelapse)
        self.start_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        
        self.stop_btn = QPushButton("Berhenti")
        self.stop_btn.clicked.connect(self.stop_timelapse)
        self.stop_btn.setEnabled(False)
        
        self.view_images_btn = QPushButton("Lihat Gambar")
        self.view_images_btn.clicked.connect(self.view_captured_images)
        
        self.generate_video_btn = QPushButton("Buat Video")
        self.generate_video_btn.clicked.connect(self.generate_video)
        
        self.cleanup_after_video_btn = QPushButton("Buat Video & Hapus JPG")
        self.cleanup_after_video_btn.clicked.connect(self.generate_video_and_cleanup)
        
        right_controls.addWidget(self.start_btn)
        right_controls.addWidget(self.stop_btn)
        right_controls.addWidget(self.view_images_btn)
        right_controls.addWidget(self.generate_video_btn)
        right_controls.addWidget(self.cleanup_after_video_btn)
        right_controls.setAlignment(Qt.AlignTop)
        
        controls_layout.addLayout(right_controls)
        main_layout.addLayout(controls_layout)
        
        # Status bar
        self.status_label = QLabel("Siap untuk merekam")
        main_layout.addWidget(self.status_label)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Update initial storage usage
        self.update_storage_display()
        
        # Setup timer for regular UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_storage_display)
        self.update_timer.start(10000)  # Update every 10 seconds
    
    def update_compression_label(self):
        self.compression = self.compress_slider.value()
        self.compress_label.setText(f"Kompresi JPG: {self.compression}%")
    
    def update_storage_display(self):
        """Update storage usage display"""
        if os.path.exists(self.output_dir):
            current_size = self.get_directory_size_mb(self.output_dir)
            max_size = self.storage_limit_input.value()
            
            usage_percent = min(int(current_size / max_size * 100), 100)
            self.storage_progress.setValue(usage_percent)
            
            # Color coding
            if usage_percent < 70:
                self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")
            elif usage_percent < 90:
                self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
            else:
                self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
                
            self.status_label.setText(f"Penggunaan storage: {current_size:.1f} MB / {max_size} MB ({usage_percent}%)")
    
    def get_directory_size_mb(self, directory):
        """Get directory size in MB"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for f in filenames:
                if f.endswith('.jpg'):
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)  # Convert to MB
    
    def cleanup_storage(self):
        """Manually clean up oldest files to save space"""
        if not os.path.exists(self.output_dir) or not os.listdir(self.output_dir):
            QMessageBox.information(self, "Info", "Tidak ada file untuk dibersihkan.")
            return
            
        reply = QMessageBox.question(self, "Konfirmasi", 
                                    "Ini akan menghapus 50% file terlama dari folder. Lanjutkan?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Get all JPG files and sort by creation time
            files = []
            for f in os.listdir(self.output_dir):
                if f.endswith('.jpg'):
                    path = os.path.join(self.output_dir, f)
                    files.append((path, os.path.getctime(path)))
            
            files.sort(key=lambda x: x[1])
            
            # Delete oldest 50% of files
            files_to_delete = files[:len(files)//2]
            bytes_removed = 0
            
            for file_path, _ in files_to_delete:
                bytes_removed += os.path.getsize(file_path)
                os.remove(file_path)
            
            mb_removed = bytes_removed / (1024 * 1024)
            QMessageBox.information(self, "Pembersihan Selesai", 
                                   f"Dihapus {len(files_to_delete)} file ({mb_removed:.1f} MB)")
            
            self.update_storage_display()
    
    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Pilih Direktori Output")
        if dir_path:
            self.output_dir = dir_path
            self.dir_input.setText(self.output_dir)
            self.update_storage_display()
    
    def start_timelapse(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        interval = self.interval_input.value()
        self.compression = self.compress_slider.value()
        self.max_storage_mb = self.storage_limit_input.value()
        self.auto_cleanup = self.auto_cleanup_check.isChecked()
        self.resolution = self.resolution_select.currentData()
        
        self.capture_thread = CaptureThread(
            interval=interval, 
            output_dir=self.output_dir,
            compression=self.compression,
            max_storage_mb=self.max_storage_mb,
            auto_cleanup=self.auto_cleanup,
            resolution=self.resolution
        )
        
        self.capture_thread.update_frame.connect(self.update_frame)
        self.capture_thread.update_status.connect(self.update_status)
        self.capture_thread.update_storage.connect(self.update_storage_info)
        self.capture_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.interval_input.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.compress_slider.setEnabled(False)
        self.storage_limit_input.setEnabled(False)
        self.auto_cleanup_check.setEnabled(False)
        self.resolution_select.setEnabled(False)
        
        self.update_status("Timelapse dimulai")
    
    def stop_timelapse(self):
        if self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.stop()
            
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.interval_input.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.compress_slider.setEnabled(True)
        self.storage_limit_input.setEnabled(True)
        self.auto_cleanup_check.setEnabled(True)
        self.resolution_select.setEnabled(True)
        
        self.update_status("Timelapse dihentikan")
        self.update_storage_display()
    
    def update_frame(self, frame):
        h, w, c = frame.shape
        bytes_per_line = 3 * w
        q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_image)
        
        # Scale pixmap to fit in the label while preserving aspect ratio
        scaled_pixmap = pixmap.scaled(self.camera_view.width(), self.camera_view.height(), 
                                    Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.camera_view.setPixmap(scaled_pixmap)
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def update_storage_info(self, current_size, max_size):
        """Update storage info from the capture thread"""
        usage_percent = min(int(current_size / max_size * 100), 100)
        self.storage_progress.setValue(usage_percent)
        
        # Color coding
        if usage_percent < 70:
            self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")
        elif usage_percent < 90:
            self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
    
    def generate_video_and_cleanup(self):
        """Generate video and then delete JPG files"""
        success = self.generate_video(show_message=False)
        
        if success:
            reply = QMessageBox.question(self, "Hapus JPG", 
                                       "Video berhasil dibuat. Hapus semua file JPG untuk menghemat ruang?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                files_deleted = 0
                mb_freed = 0
                
                for f in os.listdir(self.output_dir):
                    if f.endswith('.jpg'):
                        file_path = os.path.join(self.output_dir, f)
                        mb_freed += os.path.getsize(file_path) / (1024 * 1024)
                        os.remove(file_path)
                        files_deleted += 1
                
                QMessageBox.information(self, "Pembersihan Selesai", 
                                      f"Dihapus {files_deleted} file JPG ({mb_freed:.1f} MB)")
                self.update_storage_display()
    
    def generate_video(self, show_message=True):
        # Check if there are images to create a video
        if not os.path.exists(self.output_dir) or not os.listdir(self.output_dir):
            QMessageBox.warning(self, "Peringatan", "Tidak ada gambar untuk membuat video!")
            return False
        
        try:
            # Get output video path
            video_path, _ = QFileDialog.getSaveFileName(self, "Simpan Video", 
                                                    os.path.join(os.path.expanduser("~"), "timelapse.mp4"),
                                                    "Video Files (*.mp4)")
            
            if not video_path:
                return False
                
            # Get all jpg images and sort them by timestamp in filename
            images = [img for img in os.listdir(self.output_dir) if img.endswith(".jpg")]
            
            # Debug info
            self.update_status(f"Menemukan {len(images)} gambar")
            if not images:
                QMessageBox.warning(self, "Peringatan", "Tidak ada file JPG di direktori!")
                return False
            
            # Sort by timestamp in filename (capture_YYYYMMDD_HHMMSS.jpg)
            # This ensures proper chronological order
            images.sort(key=lambda x: x.split('_')[1] + x.split('_')[2].split('.')[0])
            
            # Get frame size from first image
            first_img_path = os.path.join(self.output_dir, images[0])
            frame = cv2.imread(first_img_path)
            if frame is None:
                QMessageBox.warning(self, "Peringatan", f"Tidak bisa membaca file gambar: {first_img_path}")
                return False
                
            h, w, _ = frame.shape
            
            # Create video writer with a different codec
            # Try several codecs that might be available on Windows
            try:
                fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Try XVID codec first
                self.update_status("Menggunakan codec XVID")
            except Exception:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Fallback to mp4v
                    self.update_status("Menggunakan codec mp4v")
                except Exception:
                    fourcc = cv2.VideoWriter_fourcc(*'MJPG')  # Last resort - Motion JPEG
                    self.update_status("Menggunakan codec MJPG")
            
            fps = 10  # Slower FPS might be better for timelapse
            
            # Debug info
            self.update_status(f"Membuat video: {w}x{h} dengan {fps} FPS")
            
            out = cv2.VideoWriter(video_path, fourcc, fps, (w, h))
            if not out.isOpened():
                QMessageBox.warning(self, "Peringatan", "Gagal membuat file video. Coba codec lain.")
                return False
                
            # Progress dialog
            progress = QProgressBar(self)
            progress.setGeometry(0, 0, 300, 25)
            progress.setMaximum(len(images))
            progress.setValue(0)
            progress.show()
            
            # Add images to video
            for i, img_name in enumerate(images):
                img_path = os.path.join(self.output_dir, img_name)
                frame = cv2.imread(img_path)
                
                if frame is not None:
                    out.write(frame)
                    self.update_status(f"Menambahkan frame {i+1}/{len(images)}: {img_name}")
                else:
                    self.update_status(f"Gambar rusak: {img_path}")
                
                progress.setValue(i + 1)
                QApplication.processEvents()
                
            # Release video writer
            out.release()
            
            # Final check if file was created and has content
            if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                if show_message:
                    QMessageBox.information(self, "Sukses", f"Video berhasil dibuat: {video_path}")
                return True
            else:
                if show_message:
                    QMessageBox.warning(self, "Peringatan", "Video dibuat tetapi mungkin kosong atau rusak. Coba codec lain.")
                return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal membuat video: {str(e)}")
            import traceback
            self.update_status(traceback.format_exc())
            return False
    
    def view_captured_images(self):
        """Open the output directory to view captured images"""
        if not os.path.exists(self.output_dir):
            QMessageBox.warning(self, "Peringatan", "Direktori tidak ditemukan!")
            return
            
        # Check if there are any JPG images
        images = [img for img in os.listdir(self.output_dir) if img.endswith(".jpg")]
        if not images:
            QMessageBox.warning(self, "Peringatan", "Tidak ada gambar yang ditemukan!")
            return
            
        # Open directory with default file explorer
        try:
            import subprocess
            if sys.platform == 'win32':
                os.startfile(self.output_dir)
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', self.output_dir])
            else:  # Linux
                subprocess.call(['xdg-open', self.output_dir])
            
            self.update_status(f"Membuka folder: {self.output_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal membuka folder: {str(e)}")
    
    def closeEvent(self, event):
        # Stop the capture thread if it's running
        if self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimelapseApp()
    window.show()
    sys.exit(app.exec_()) 