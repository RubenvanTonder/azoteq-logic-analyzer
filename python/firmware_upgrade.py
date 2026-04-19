import sys
import os
import time
import platform
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QPushButton, 
                             QGroupBox, QCheckBox, QTextEdit, QTabWidget, 
                             QGridLayout, QMessageBox, QFileDialog, QProgressBar)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPalette, QColor

# ==========================================
# 1. OPTIMIZED FLASHER WORKER (High Speed)
# ==========================================
class FlasherWorker(QThread):
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, source_file):
        super().__init__()
        self.source_file = source_file
        self.is_running = True

    def find_pico_drive(self):
        """Optimized OS-specific drive detector"""
        system = platform.system()
        
        if system == "Windows":
            import string
            import ctypes
            drives = []
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
            
            for drive in drives:
                if os.path.exists(os.path.join(drive, "INFO_UF2.TXT")):
                    return drive
                    
        elif system == "Darwin": # macOS
            if os.path.exists("/Volumes/RPI-RP2/INFO_UF2.TXT"):
                return "/Volumes/RPI-RP2"
                
        elif system == "Linux":
            user = os.environ.get('USER', 'root')
            candidates = [
                f"/media/{user}/RPI-RP2",
                "/media/RPI-RP2",
                "/mnt/RPI-RP2",
                "/run/media/{user}/RPI-RP2"
            ]
            for path in candidates:
                if os.path.exists(os.path.join(path, "INFO_UF2.TXT")):
                    return path
        return None

    def run(self):
        target_drive = None
        timeout = 30
        poll_interval = 0.2 
        elapsed = 0

        self.status_update.emit("Searching for RPI-RP2...")
        
        # 1. FAST POLLING
        while self.is_running and elapsed < timeout:
            target_drive = self.find_pico_drive()
            if target_drive:
                break
            time.sleep(poll_interval)
            elapsed += poll_interval
            self.progress_update.emit(int((elapsed / timeout) * 30))

        if not target_drive:
            self.finished.emit(False, "Timeout: Drive not found.")
            return

        # 2. HIGH SPEED RAW COPY
        self.status_update.emit(f"Flashing to {target_drive}...")
        self.progress_update.emit(50)

        try:
            dest_path = os.path.join(target_drive, os.path.basename(self.source_file))
            file_size = os.path.getsize(self.source_file)
            chunk_size = 64 * 1024 
            copied = 0
            
            with open(self.source_file, 'rb') as fsrc:
                with open(dest_path, 'wb') as fdst:
                    while True:
                        buf = fsrc.read(chunk_size)
                        if not buf: break
                        fdst.write(buf)
                        copied += len(buf)
                        pct = 50 + int((copied / file_size) * 50)
                        self.progress_update.emit(pct)

                    fdst.flush()
                    os.fsync(fdst.fileno())
            
            self.progress_update.emit(100)
            self.finished.emit(True, "Flash Complete (Device Rebooting)")

        except OSError as e:
            # Handle early disconnect as success
            err_str = str(e)
            if "No such device" in err_str or "Input/output error" in err_str or "Permission denied" in err_str:
                 self.progress_update.emit(100)
                 self.finished.emit(True, "Flash Complete (Device Disconnected Early)")
            else:
                self.finished.emit(False, f"Write Error: {err_str}")
        except Exception as e:
            self.finished.emit(False, f"Unexpected Error: {str(e)}")

# ==========================================
# 2. SERIAL WORKER
# ==========================================
class SerialWorker(QThread):
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.is_running = False

    def connect_serial(self, port, baud):
        self.port_name = port
        self.baud_rate = baud
        self.start()

    def run(self):
        try:
            self.serial_port = serial.Serial(self.port_name, self.baud_rate, timeout=0.1)
            self.is_running = True
            self.connection_status.emit(True)
            while self.is_running:
                if self.serial_port.in_waiting:
                    self.data_received.emit(self.serial_port.read(self.serial_port.in_waiting))
                self.msleep(10)
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.connection_status.emit(False)
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    def send_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data.encode('utf-8') + b'\n')
            except Exception as e:
                self.error_occurred.emit(str(e))

    def stop(self):
        self.is_running = False
        self.wait()

# ==========================================
# 3. MAIN GUI (DARK MODE)
# ==========================================
class PicoSigrokManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pico Sigrok Manager")
        self.resize(950, 650)

        # --- DATA WORKERS ---
        self.serial_worker = SerialWorker()
        self.serial_worker.data_received.connect(self.process_serial_data)
        self.serial_worker.connection_status.connect(self.update_connection_status)

        # --- UI SETUP ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # Tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.tab_monitor = QWidget()
        self.setup_monitor_tab()
        self.tabs.addTab(self.tab_monitor, "Device Control")

        self.tab_flash = QWidget()
        self.setup_flash_tab()
        self.tabs.addTab(self.tab_flash, "Firmware Upgrade")

        self.refresh_ports()

    def setup_monitor_tab(self):
        layout = QVBoxLayout(self.tab_monitor)
        
        # -- Connection --
        grp_conn = QGroupBox("Connection")
        hbox = QHBoxLayout()
        self.port_combo = QComboBox()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setCheckable(True)
        self.btn_connect.clicked.connect(self.toggle_connection)
        
        hbox.addWidget(QLabel("Port:"))
        hbox.addWidget(self.port_combo)
        hbox.addWidget(btn_refresh)
        hbox.addWidget(self.btn_connect)
        grp_conn.setLayout(hbox)
        layout.addWidget(grp_conn)
        
        # -- Channel Management --
        grp_chan = QGroupBox("Channel Mapping & Control")
        vbox_chan = QVBoxLayout()

        # Map Button
        hbox_map = QHBoxLayout()
        btn_map = QPushButton("Query Pin Mapping (n)")
        btn_map.setToolTip("Sends nD0-nD7 and nA0-nA1 to discover real Pin names")
        btn_map.clicked.connect(self.query_pin_names)
        hbox_map.addWidget(btn_map)
        vbox_chan.addLayout(hbox_map)
        
        # Digital Toggles
        self.chk_dig = []
        hbox_d = QHBoxLayout()
        hbox_d.addWidget(QLabel("Digital:"))
        for i in range(8):
            chk = QCheckBox(f"D{i}")
            chk.stateChanged.connect(lambda state, idx=i: self.send_cmd(f"D{'1' if state else '0'}{idx}"))
            hbox_d.addWidget(chk)
            self.chk_dig.append(chk)
        vbox_chan.addLayout(hbox_d)

        # Analog Toggles (REDUCED TO 2 CHANNELS: A0, A1)
        self.chk_ana = []
        hbox_a = QHBoxLayout()
        hbox_a.addWidget(QLabel("Analog:"))
        for i in range(2): # Changed from 3 to 2
            chk = QCheckBox(f"A{i}")
            chk.stateChanged.connect(lambda state, idx=i: self.send_cmd(f"A{'1' if state else '0'}{idx}"))
            hbox_a.addWidget(chk)
            self.chk_ana.append(chk)
        vbox_chan.addLayout(hbox_a)

        grp_chan.setLayout(vbox_chan)
        layout.addWidget(grp_chan)

        # -- Operations --
        grp_run = QGroupBox("Operations")
        hbox_run = QHBoxLayout()
        
        btn_id = QPushButton("Identify (i)")
        btn_id.clicked.connect(lambda: self.send_cmd("i"))
        
        btn_boot = QPushButton("Enter Bootloader (bootsel)")
        btn_boot.setStyleSheet("background-color: #5a2e2e; color: #ffcccc; font-weight: bold; border: 1px solid #721c24;")
        btn_boot.clicked.connect(self.trigger_bootsel)

        hbox_run.addWidget(btn_id)
        hbox_run.addWidget(btn_boot)
        grp_run.setLayout(hbox_run)
        layout.addWidget(grp_run)

        # -- Logs --
        split = QTabWidget()
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        # Dark Log Style
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #cfcfcf; font-family: Monospace; border: 1px solid #333;")
        split.addTab(self.log_view, "Protocol Log")

        self.map_view = QTextEdit()
        self.map_view.setReadOnly(True)
        # Dark Map Style (Blueish text for data)
        self.map_view.setStyleSheet("background-color: #1e1e1e; color: #66a3ff; font-family: Monospace; border: 1px solid #333;")
        split.addTab(self.map_view, "Pin Map Results")

        layout.addWidget(split)

    def setup_flash_tab(self):
        layout = QVBoxLayout(self.tab_flash)
        
        lbl_instr = QLabel(
            "<h3 style='color: #fff;'>High-Speed Firmware Upgrade</h3>"
            "<ol style='color: #ccc;'>"
            "<li>Select <b>.uf2</b> file.</li>"
            "<li>Click <b>Start Upgrade</b>.</li>"
            "<li>Device reboots to 'RPI-RP2' drive.</li>"
            "<li>File is copied instantly.</li></ol>"
        )
        layout.addWidget(lbl_instr)
        
        # File Selection
        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet("border: 1px solid #444; padding: 5px; background: #2b2b2b; color: #fff;")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_firmware)
        file_layout.addWidget(self.lbl_file, 1)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)
        
        # Progress
        self.flash_progress = QProgressBar()
        self.flash_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #2b2b2b;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)
        layout.addWidget(self.flash_progress)
        
        # Log
        self.flash_log = QTextEdit()
        self.flash_log.setReadOnly(True)
        self.flash_log.setStyleSheet("background-color: #1e1e1e; color: #0f0; font-family: Monospace;")
        layout.addWidget(self.flash_log)
        
        # Button
        self.btn_upgrade = QPushButton("Start Upgrade")
        self.btn_upgrade.setMinimumHeight(50)
        self.btn_upgrade.setStyleSheet("background-color: #2a82da; color: white; font-weight: bold; font-size: 14px;")
        self.btn_upgrade.clicked.connect(self.start_upgrade)
        layout.addWidget(self.btn_upgrade)

    # ====================
    # LOGIC HANDLERS
    # ====================
    def refresh_ports(self):
        self.port_combo.clear()
        for port in serial.tools.list_ports.comports():
            self.port_combo.addItem(f"{port.device}", port.device)

    def toggle_connection(self):
        if self.btn_connect.isChecked():
            port = self.port_combo.currentData()
            if port:
                self.serial_worker.connect_serial(port, 115200)
                self.log(f"Connecting to {port}...")
        else:
            self.serial_worker.stop()
            self.log("Disconnected.")

    def update_connection_status(self, connected):
        self.btn_connect.setChecked(connected)
        self.btn_connect.setText("Disconnect" if connected else "Connect")
        # Highlight connect button when active
        if connected:
            self.btn_connect.setStyleSheet("background-color: #2d5a35; color: #d4edda;")
        else:
            self.btn_connect.setStyleSheet("")

    def send_cmd(self, cmd):
        self.log(f"TX: {cmd}")
        self.serial_worker.send_data(cmd)

    def query_pin_names(self):
        self.map_view.clear()
        self.map_view.append("--- Querying Pin Map ---")
        # Digital D0-D7
        for i in range(8):
            self.send_cmd(f"nD{i}")
            time.sleep(0.05)
        # Analog A0-A1 (REDUCED TO 2)
        for i in range(2): 
            self.send_cmd(f"nA{i}")
            time.sleep(0.05)

    def process_serial_data(self, data):
        try:
            text = data.decode('utf-8').strip()
            if text:
                if text.startswith("GP") or "ADC" in text:
                    self.map_view.append(f"RX: {text}")
                self.log(f"RX: {text}")
        except:
            pass

    def log(self, msg):
        self.log_view.append(msg)

    # ====================
    # FLASH HANDLERS
    # ====================
    def browse_firmware(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Firmware", "", "UF2 Files (*.uf2)")
        if fname:
            self.lbl_file.setText(fname)
            self.flash_path = fname

    def trigger_bootsel(self):
        if QMessageBox.question(self, "Confirm", "Reboot to bootloader?") == QMessageBox.Yes:
            self.send_cmd("bootsel")
            self.serial_worker.stop()

    def start_upgrade(self):
        if not hasattr(self, 'flash_path'):
            QMessageBox.warning(self, "Error", "Select a file first.")
            return
        
        if self.serial_worker.isRunning():
            self.send_cmd("bootsel")
            time.sleep(0.5)
            self.serial_worker.stop()
        
        self.btn_upgrade.setEnabled(False)
        self.flasher = FlasherWorker(self.flash_path)
        self.flasher.status_update.connect(self.flash_log.append)
        self.flasher.progress_update.connect(self.flash_progress.setValue)
        self.flasher.finished.connect(self.on_flash_finished)
        self.flasher.start()

    def on_flash_finished(self, success, msg):
        self.btn_upgrade.setEnabled(True)
        self.flash_log.append(msg)
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Error", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- DARK MODE THEME CONFIGURATION ---
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    # Apply generic tooltip styling
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")

    window = PicoSigrokManager()
    window.show()
    sys.exit(app.exec_())
