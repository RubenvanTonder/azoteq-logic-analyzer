import sys
import os
import time
import platform
import serial
print(f"DEBUG: Loaded serial from: {serial.__file__}")
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QGroupBox, QCheckBox, QTextEdit, QTabWidget, QGridLayout, QMessageBox, QFileDialog, QProgressBar)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPalette, QColor

# ==========================================
# 1. FLASHER WORKER
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
        system = platform.system()
        if system == "Windows":
            import string
            import ctypes
            drives = []
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1: drives.append(f"{letter}:\\")
                bitmask >>= 1
            for drive in drives:
                if os.path.exists(os.path.join(drive, "INFO_UF2.TXT")): return drive
        elif system == "Darwin":
            if os.path.exists("/Volumes/RPI-RP2/INFO_UF2.TXT"): return "/Volumes/RPI-RP2"
        elif system == "Linux":
            user = os.environ.get('USER', 'root')
            candidates = [f"/media/{user}/RPI-RP2", "/media/RPI-RP2", "/mnt/RPI-RP2", f"/run/media/{user}/RPI-RP2"]
            for path in candidates:
                if os.path.exists(os.path.join(path, "INFO_UF2.TXT")): return path
        return None

    def run(self):
        target_drive = None
        timeout = 30
        poll_interval = 0.2
        elapsed = 0
        self.status_update.emit("Searching for RPI-RP2...")
        while self.is_running and elapsed < timeout:
            target_drive = self.find_pico_drive()
            if target_drive: break
            time.sleep(poll_interval)
            elapsed += poll_interval
            self.progress_update.emit(int((elapsed / timeout) * 30))

        if not target_drive:
            self.finished.emit(False, "Timeout: Drive not found.")
            return

        self.status_update.emit(f"Flashing to {target_drive}...")
        try:
            dest_path = os.path.join(target_drive, os.path.basename(self.source_file))
            file_size = os.path.getsize(self.source_file)
            chunk_size = 64 * 1024
            copied = 0

            with open(self.source_file, 'rb') as fsrc:
                with open(dest_path, 'wb') as fdst:
                    while self.is_running:
                        buf = fsrc.read(chunk_size)
                        if not buf:
                            break
                        fdst.write(buf)
                        copied += len(buf)
                        self.progress_update.emit(50 + int((copied / file_size) * 45))

                    # IMPORTANT: Pico might reboot the moment the last byte is written.
                    # Wrap the flush/sync in a try block or skip it for UF2.
                    try:
                        fdst.flush()
                        os.fsync(fdst.fileno())
                    except OSError:
                        pass # Drive already disconnected, which is actually a success

            self.progress_update.emit(100)
            self.finished.emit(True, "Flash Complete")

        except Exception as e:
            # Check if error is just the drive vanishing (Normal for Pico)
            if "No such file" in str(e) or "Permission denied" in str(e):
                self.finished.emit(True, "Flash Complete (Drive Reset)")
            else:
                self.finished.emit(False, f"Error: {str(e)}")

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
        self.port_name = ""
        self.baud_rate = 115200

    def connect_serial(self, port, baud):
        self.port_name = port
        self.baud_rate = baud
        if not self.isRunning(): self.start()

    def run(self):
        try:
            self.serial_port = serial.Serial(self.port_name, self.baud_rate, timeout=0.1)
            self.serial_port.dtr = True
            self.serial_port.rts = True
            time.sleep(0.1)
            self.is_running = True
            self.connection_status.emit(True)
            while self.is_running:
                if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting:
                    self.data_received.emit(self.serial_port.read(self.serial_port.in_waiting))
                self.msleep(10)
        except Exception as e:
            self.error_occurred.emit(f"Port Error: {str(e)}")
        finally:
            self.is_running = False
            if self.serial_port:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                except:
                    pass
                self.serial_port = None
            self.connection_status.emit(False) # Notify GUI we are officially out


    def send_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            try: self.serial_port.write(data.encode('utf-8') + b'\n')
            except Exception as e: self.error_occurred.emit(str(e))

    def stop(self):
        self.is_running = False
        if self.serial_port:
            try:
                # Check if we are on Windows and if the overlapped structure is valid
                if platform.system() == "Windows":
                    # This prevents the 'NoneType' byref error
                    if hasattr(self.serial_port, '_overlapped_read') and \
                        self.serial_port._overlapped_read is not None:
                        self.serial_port.cancel_read()
                else:
                    self.serial_port.cancel_read()
            except Exception as e:
                print(f"Cleanup note: Port already closed or gone ({e})")

            # Use wait() only if the thread is still actually running
            if self.isRunning():
                self.wait(500) # Wait max 500ms for thread to exit

# ==========================================
# 3. MAIN GUI
# ==========================================
class PicoSigrokManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pico Device Manager")
        self.resize(950, 650)

        self.serial_worker = SerialWorker()
        self.serial_worker.data_received.connect(self.process_serial_data)
        self.serial_worker.connection_status.connect(self.update_connection_status)
        self.serial_worker.error_occurred.connect(self.handle_serial_error)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

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

        # Connection Group
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

        # Operations Group
        grp_ops = QGroupBox("Operations")
        vbox_ops = QVBoxLayout()

        # Row 1: Query Pin Mapping
        btn_map = QPushButton("Query Pin Mapping (n)")
        btn_map.setFixedHeight(35)
        btn_map.clicked.connect(self.query_pin_names)
        vbox_ops.addWidget(btn_map)

        # Row 2: Identify, LED, Boot (Uniform sizes)
        hbox_btns = QHBoxLayout()
        btn_height = 40

        # PWM Control Group
        grp_pwm = QGroupBox("PWM Control")
        hbox_pwm = QHBoxLayout()

        btn_pwm1 = QPushButton("PWM 1 (500kHz, 50%)")
        btn_pwm1.setFixedHeight(40)
        btn_pwm1.clicked.connect(lambda: self.send_pwm_cmd("1"))

        btn_pwm2 = QPushButton("PWM 2 (500kHz, 20%)")
        btn_pwm2.setFixedHeight(40)
        btn_pwm2.clicked.connect(lambda: self.send_pwm_cmd("2"))

        hbox_pwm.addWidget(btn_pwm1)
        hbox_pwm.addWidget(btn_pwm2)
        grp_pwm.setLayout(hbox_pwm)
        layout.addWidget(grp_pwm)


        self.btn_id = QPushButton("Identify")
        self.btn_id.setFixedHeight(btn_height)
        self.btn_id.clicked.connect(lambda: self.send_cmd("i"))

        self.btn_led = QPushButton("LED: OFF")
        self.btn_led.setCheckable(True)
        self.btn_led.setFixedHeight(btn_height)
        self.btn_led.clicked.connect(self.toggle_led)

        self.btn_boot = QPushButton("Boot")
        self.btn_boot.setFixedHeight(btn_height)
        self.btn_boot.setStyleSheet("background-color: #5a2e2e; color: #ffcccc; font-weight: bold;")
        self.btn_boot.clicked.connect(self.trigger_bootsel)

        hbox_btns.addWidget(self.btn_id)
        hbox_btns.addWidget(self.btn_led)
        hbox_btns.addWidget(self.btn_boot)

        vbox_ops.addLayout(hbox_btns)
        grp_ops.setLayout(vbox_ops)
        layout.addWidget(grp_ops)

        # Logs
        split_tabs = QTabWidget()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #cfcfcf; font-family: Monospace;")
        split_tabs.addTab(self.log_view, "Protocol Log")

        self.map_view = QTextEdit()
        self.map_view.setReadOnly(True)
        self.map_view.setStyleSheet("background-color: #1e1e1e; color: #66a3ff; font-family: Monospace;")
        split_tabs.addTab(self.map_view, "Pin Map Results")

        layout.addWidget(split_tabs)

    def setup_flash_tab(self):
        layout = QVBoxLayout(self.tab_flash)
        layout.addWidget(QLabel("<h3>Firmware Upgrade</h3>"))

        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("No UF2 file selected")
        self.lbl_file.setStyleSheet("border: 1px solid #444; padding: 5px; background: #2b2b2b;")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_firmware)
        file_layout.addWidget(self.lbl_file, 1)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)

        self.flash_progress = QProgressBar()
        layout.addWidget(self.flash_progress)
        self.flash_log = QTextEdit()
        self.flash_log.setReadOnly(True)
        layout.addWidget(self.flash_log)

        self.btn_upgrade = QPushButton("Start Upgrade")
        self.btn_upgrade.setMinimumHeight(50)
        self.btn_upgrade.setStyleSheet("background-color: #2a82da; color: white; font-weight: bold;")
        self.btn_upgrade.clicked.connect(self.start_upgrade)
        layout.addWidget(self.btn_upgrade)

    def toggle_led(self, checked):
        if checked:
            self.send_cmd("B1")
            self.btn_led.setText("LED: ON")
            self.btn_led.setStyleSheet("background-color: #ffd700; color: black; font-weight: bold;")
        else:
            self.send_cmd("B0")
            self.btn_led.setText("LED: OFF")
            self.btn_led.setStyleSheet("")

    def refresh_ports(self):
        self.port_combo.clear()
        for port in serial.tools.list_ports.comports():
            self.port_combo.addItem(f"{port.device}", port.device)

    def toggle_connection(self):
        if self.btn_connect.isChecked():
            port = self.port_combo.currentData()
            if port: self.serial_worker.connect_serial(port, 115200)
            else: self.btn_connect.setChecked(False)
        else:
            self.serial_worker.stop()

    def update_connection_status(self, connected):
        self.btn_connect.setChecked(connected)
        self.btn_connect.setText("Disconnect" if connected else "Connect")
        if connected:
            self.btn_connect.setStyleSheet("background-color: #2d5a35; color: #d4edda;")
            self.send_cmd("i")
        else:
            self.btn_connect.setStyleSheet("")
            self.btn_led.setChecked(False)
            self.btn_led.setText("LED: OFF")
            self.btn_led.setStyleSheet("")

    def query_pin_names(self):
        self.map_view.clear()
        self.map_view.append("--- Querying Pin Map ---")
        # Digital
        for i in range(8):
            self.send_cmd(f"nD{i}")
            time.sleep(0.02)
        # Analog
        for i in range(2):
            self.send_cmd(f"nA{i}")
            time.sleep(0.02)

    def handle_serial_error(self, msg):
        self.log_view.append(f"Error: {msg}")
        self.update_connection_status(False)

    def send_cmd(self, cmd):
        self.log_view.append(f"TX: {cmd}")
        self.serial_worker.send_data(cmd)

    def process_serial_data(self, data):
        try:
            text = data.decode('utf-8').strip()
            if text:
                self.log_view.append(f"RX: {text}")
                # Filter Pin Map responses to the map tab
                if text.startswith("GP") or "ADC" in text:
                    self.map_view.append(f"Pin Map -> {text}")
        except: pass

    def browse_firmware(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Firmware", "", "UF2 Files (*.uf2)")
        if fname:
            self.lbl_file.setText(fname)
            self.flash_path = fname

    def trigger_bootsel(self):
        if QMessageBox.question(self, "Confirm", "Reboot to Bootloader?") == QMessageBox.Yes:
            self.send_cmd("bootsel")
            # Force UI to 'Disconnected' state immediately
            self.btn_connect.setChecked(False)
            self.update_connection_status(False)
            self.serial_worker.stop()

    def send_pwm_cmd(self, channel):
        # Sends 'W1' or 'W2' based on the button clicked
        cmd = f"W{channel}"
        self.send_cmd(cmd)

    def start_upgrade(self):
        if not hasattr(self, 'flash_path'): return
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    app.setPalette(palette)

    window = PicoSigrokManager()
    window.show()
    sys.exit(app.exec_())