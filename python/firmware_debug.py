import sys
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QSpinBox, 
                             QPushButton, QGroupBox, QCheckBox, QTextEdit, 
                             QTabWidget, QGridLayout, QMessageBox, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer

# ==========================================
# WORKER THREAD (Non-Blocking Serial I/O)
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
        self.start()

    def run(self):
        try:
            # Standard Pico CDC ignores baud, but we set it anyway
            self.serial_port = serial.Serial(self.port_name, self.baud_rate, timeout=0.1)
            self.is_running = True
            self.connection_status.emit(True)
            
            while self.is_running:
                if self.serial_port.in_waiting:
                    # Read available bytes
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self.data_received.emit(data)
                self.msleep(10)  # Prevent CPU hogging

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.connection_status.emit(False)
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    def send_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            try:
                # Protocol expects CR/LF termination implied by "else // no CR/LF"
                # But usually C parsers like '\n' or '\r'. 
                # The provided code runs logic on CHAR input, resetting on CR/LF
                self.serial_port.write(data.encode('utf-8') + b'\n')
            except Exception as e:
                self.error_occurred.emit(str(e))

    def stop(self):
        self.is_running = False
        self.wait()

# ==========================================
# MAIN INTERFACE
# ==========================================
class PicoSigrokGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pico Sigrok Interface (Custom Protocol)")
        self.resize(1000, 700)

        self.worker = SerialWorker()
        self.worker.data_received.connect(self.process_serial_data)
        self.worker.connection_status.connect(self.update_connection_status)
        self.worker.error_occurred.connect(self.handle_error)

        # Setup UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        self.create_connection_group()
        self.create_config_group()
        self.create_control_group()
        self.create_monitor_group()

    def create_connection_group(self):
        group = QGroupBox("Serial Connection")
        layout = QHBoxLayout()

        self.port_combo = QComboBox()
        self.refresh_ports()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.toggle_connection)

        layout.addWidget(QLabel("Port:"))
        layout.addWidget(self.port_combo)
        layout.addWidget(refresh_btn)
        layout.addWidget(self.connect_btn)
        layout.addStretch()

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def create_config_group(self):
        group = QGroupBox("Acquisition Configuration")
        layout = QGridLayout()

        # Sample Rate (Cmd: R)
        layout.addWidget(QLabel("Sample Rate (Hz):"), 0, 0)
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(5000, 120000016) # Matches firmware limits
        self.rate_spin.setValue(10000)
        self.rate_spin.setSingleStep(1000)
        layout.addWidget(self.rate_spin, 0, 1)
        
        btn_set_rate = QPushButton("Set Rate (R)")
        btn_set_rate.clicked.connect(lambda: self.send_cmd(f"R{self.rate_spin.value()}"))
        layout.addWidget(btn_set_rate, 0, 2)

        # Sample Limit (Cmd: L)
        layout.addWidget(QLabel("Sample Count:"), 1, 0)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 10000000)
        self.limit_spin.setValue(1024)
        layout.addWidget(self.limit_spin, 1, 1)

        btn_set_limit = QPushButton("Set Limit (L)")
        btn_set_limit.clicked.connect(lambda: self.send_cmd(f"L{self.limit_spin.value()}"))
        layout.addWidget(btn_set_limit, 1, 2)

        # Pre-trigger (Cmd: p)
        layout.addWidget(QLabel("Pre-Trigger:"), 2, 0)
        self.pre_spin = QSpinBox()
        self.pre_spin.setRange(0, 1000000)
        layout.addWidget(self.pre_spin, 2, 1)

        btn_set_pre = QPushButton("Set Pre (p)")
        btn_set_pre.clicked.connect(lambda: self.send_cmd(f"p{self.pre_spin.value()}"))
        layout.addWidget(btn_set_pre, 2, 2)

        # Channel Masks
        # Digital D0-D7 (Simplified for UI)
        dig_layout = QHBoxLayout()
        self.dig_checks = []
        for i in range(8):
            chk = QCheckBox(f"D{i}")
            chk.stateChanged.connect(lambda state, idx=i: self.send_cmd(f"D{'1' if state else '0'}{idx}"))
            dig_layout.addWidget(chk)
            self.dig_checks.append(chk)
        layout.addWidget(QLabel("Digital Channels:"), 3, 0)
        layout.addLayout(dig_layout, 3, 1, 1, 2)

        # Analog A0-A2
        ana_layout = QHBoxLayout()
        self.ana_checks = []
        for i in range(3):
            chk = QCheckBox(f"A{i}")
            chk.stateChanged.connect(lambda state, idx=i: self.send_cmd(f"A{'1' if state else '0'}{idx}"))
            ana_layout.addWidget(chk)
            self.ana_checks.append(chk)
        layout.addWidget(QLabel("Analog Channels:"), 4, 0)
        layout.addLayout(ana_layout, 4, 1, 1, 2)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def create_control_group(self):
        group = QGroupBox("Control Operations")
        layout = QHBoxLayout()

        # Identify (Cmd: i)
        btn_id = QPushButton("Identify (i)")
        btn_id.clicked.connect(lambda: self.send_cmd("i"))
        layout.addWidget(btn_id)

        # Fixed Run (Cmd: F)
        btn_fixed = QPushButton("Run Fixed (F)")
        btn_fixed.setStyleSheet("background-color: #d4edda; color: #155724;")
        btn_fixed.clicked.connect(lambda: self.send_cmd("F"))
        layout.addWidget(btn_fixed)

        # Continuous Run (Cmd: C)
        btn_cont = QPushButton("Run Cont (C)")
        btn_cont.setStyleSheet("background-color: #fff3cd; color: #856404;")
        btn_cont.clicked.connect(lambda: self.send_cmd("C"))
        layout.addWidget(btn_cont)

        # Bootsel (Cmd: b)
        btn_boot = QPushButton("Enter Bootsel")
        btn_boot.setStyleSheet("background-color: #f8d7da; color: #721c24;")
        btn_boot.clicked.connect(lambda: self.send_cmd("bootsel")) # Matches strcmp
        layout.addWidget(btn_boot)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def create_monitor_group(self):
        monitor_tabs = QTabWidget()
        
        # Text Log Tab
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: Monospace; font-size: 10pt;")
        monitor_tabs.addTab(self.log_view, "Protocol Log")

        # Hex Dump Tab
        self.hex_view = QTextEdit()
        self.hex_view.setReadOnly(True)
        self.hex_view.setStyleSheet("font-family: Courier New; background-color: #222; color: #0f0;")
        monitor_tabs.addTab(self.hex_view, "Raw Data (Hex)")

        self.main_layout.addWidget(monitor_tabs)
        
        # Clear logs button
        btn_clear = QPushButton("Clear Logs")
        btn_clear.clicked.connect(lambda: [self.log_view.clear(), self.hex_view.clear()])
        self.main_layout.addWidget(btn_clear)

    # ==========================================
    # LOGIC & SLOT FUNCTIONS
    # ==========================================
    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}", port.device)

    def toggle_connection(self):
        if self.connect_btn.isChecked():
            port = self.port_combo.currentData()
            if not port:
                self.connect_btn.setChecked(False)
                return
            self.worker.connect_serial(port, 115200)
            self.log_msg(f"Attempting to connect to {port}...")
        else:
            self.worker.stop()
            self.log_msg("Disconnected.")

    def update_connection_status(self, connected):
        if connected:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #c3e6cb;")
            self.log_msg("Connection Successful.")
            # Auto-identify on connect
            self.send_cmd("i")
        else:
            self.connect_btn.setChecked(False)
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("")

    def send_cmd(self, command_str):
        if not self.worker.isRunning():
            QMessageBox.warning(self, "Error", "Not connected to device.")
            return
        
        # Construct specific C-firmware logic mapping
        # Case 'b': requires "bootsel" string.
        if command_str == "bootsel":
            # The firmware checks: if(!strcmp(d->cmdstr,"bootsel")) inside case 'b'
            # We send 'b' then the string. 
            # Wait, looking at C code: case 'b': if(!strcmp(d->cmdstr,"bootsel"))
            # The parser accumulates chars into d->cmdstr.
            # So we must send the CHARACTERS "bootsel" then the triggering char?
            # Actually, usually these parsers switch on the *first* char or last char.
            # Code says: switch(charin). 
            # If charin is 'b', it checks cmdstr. 
            # This implies we need to fill cmdstr first, then send 'b'?
            # OR, the switch happens on completion?
            # The C code shows: d->cmdstr[d->cmdstrptr++] = charin; ... ret=0;
            # UNLESS it hits the switch. 
            # The switch is inside `process_char`. 
            # If `process_char` is called for every byte:
            # It accumulates until some terminator? 
            # The code snippet shows the switch happens *inside* `else` of `if (charin == '\n' || charin == '\r')`?
            # NO. The provided snippet shows:
            # `switch (d->cmdstr[0])` inside the `if (charin == '\r' || charin == '\n')` block.
            # Meaning: The device buffers chars until CR/LF, THEN switches on the FIRST char.
            pass

        self.log_msg(f"TX -> {command_str}")
        self.worker.send_data(command_str)

    def process_serial_data(self, data):
        # Display ASCII log
        try:
            text = data.decode('utf-8', errors='ignore')
            if text.strip():
                self.log_msg(f"RX <- {text.strip()}")
        except:
            pass

        # Display Hex Dump for raw analysis
        hex_str = " ".join(["{:02X}".format(x) for x in data])
        self.hex_view.append(hex_str)

    def log_msg(self, text):
        self.log_view.append(text)

    def handle_error(self, msg):
        QMessageBox.critical(self, "Serial Error", msg)
        self.connect_btn.setChecked(False)
        self.toggle_connection()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PicoSigrokGUI()
    window.show()
    sys.exit(app.exec_())
