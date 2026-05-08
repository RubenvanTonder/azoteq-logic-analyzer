import time

from device import LogicAnalyzerDevice
from capture import CaptureSession
from save import *

PORT = "COM15"   # or COMx on Windows
LENGTH = 10000
dev = LogicAnalyzerDevice(PORT)
cap = CaptureSession(dev)

dev.reset()
print(dev.identify())

dev.set_sample_rate(1_000_000)
dev.set_sample_limit(LENGTH)

# Enable D0–D3
for ch in range(4):
    dev.enable_digital(ch, True)

dev.start_fixed()
time.sleep(0.2)

print(dev.identify())  # or raw read
print(dev.debug_read(64))
# # You must calculate expected byte count correctly
# raw = cap.capture_fixed(LENGTH)
# save_binary("capture.bin", raw)



dev.close()