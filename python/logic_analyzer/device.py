import serial
import time

class LogicAnalyzerDevice:
    def __init__(self, port, baudrate=115200, timeout=1.0):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout
        )
        time.sleep(0.2)

    def close(self):
        self.ser.close()

    def _write(self, cmd: str):
        if not cmd.endswith("\n"):
            cmd += "\n"
        self.ser.write(cmd.encode("ascii"))

    def _read_response(self):
        return self.ser.read_until(b'*', size=64).decode(errors="ignore").strip()

    def reset(self):
        self._write("*")
        time.sleep(0.1)

    def identify(self):
        self._write("i")
        return self._read_response()

    def set_sample_rate(self, rate_hz: int):
        self._write(f"R{rate_hz}")
        return self._read_response()

    def set_sample_limit(self, samples: int):
        self._write(f"L{samples}")
        return self._read_response()

    def enable_analog(self, channel: int, enable=True):
        self._write(f"A{1 if enable else 0}{channel:02d}")
        return self._read_response()

    def enable_digital(self, channel: int, enable=True):
        self._write(f"D{1 if enable else 0}{channel:02d}")
        return self._read_response()

    def start_fixed(self):
        self._write("F")

    def start_continuous(self):
        self._write("C")

    def capture_fixed(self, n_bytes):
      # flush stale data
      self.ser.reset_input_buffer()

      # start capture
      self.start_fixed()

      # wait for device to respond DONE/OK
      resp = self._read_response()

      # now read raw waveform
      return self.ser.read(n_bytes)

    def read_bytes(self, n):
        return self.ser.read(n)

    def debug_read(self, n=100):
      data = self.ser.read(n)
      print(data)
      return data