import struct
import time

class CaptureSession:
    def __init__(self, device):
        self.dev = device

    def capture_fixed(self, total_bytes, timeout=5.0):
        data = bytearray()
        start = time.time()

        while len(data) < total_bytes:
            chunk = self.dev.read_bytes(total_bytes - len(data))
            if chunk:
                data.extend(chunk)
            if time.time() - start > timeout:
                break

        return bytes(data)

    def unpack_adc_u16(self, raw):
        # RP ADC samples are 12-bit right aligned in u16
        return list(struct.iter_unpack("<H", raw))

    def unpack_digital_bytes(self, raw):
        return list(raw)