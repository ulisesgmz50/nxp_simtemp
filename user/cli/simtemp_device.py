#!/usr/bin/env python3
"""
NXP SimTemp Device Interface
Low-level interface for /dev/simtemp character device and sysfs attributes
"""

import struct
import os
import select
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


# Device paths
DEVICE_PATH = "/dev/simtemp"
SYSFS_BASE = "/sys/class/misc/simtemp"

# Binary sample structure (must match kernel definition)
# struct simtemp_sample {
#     __u64 timestamp_ns;  /* 8 bytes */
#     __s32 temp_mC;       /* 4 bytes */
#     __u32 flags;         /* 4 bytes */
# } __packed;             /* Total: 16 bytes */
SAMPLE_FORMAT = "=QiI"  # Little-endian: u64, s32, u32
SAMPLE_SIZE = struct.calcsize(SAMPLE_FORMAT)

# Flag definitions (must match kernel)
FLAG_NEW_SAMPLE = 1 << 0
FLAG_THRESHOLD_CROSSED = 1 << 1


@dataclass
class TemperatureSample:
    """Represents a temperature sample from the device"""
    timestamp_ns: int
    temp_mC: int
    flags: int

    @property
    def temp_celsius(self) -> float:
        """Temperature in degrees Celsius"""
        return self.temp_mC / 1000.0

    @property
    def timestamp_sec(self) -> float:
        """Timestamp in seconds"""
        return self.timestamp_ns / 1e9

    @property
    def is_threshold_crossed(self) -> bool:
        """Check if threshold was crossed"""
        return bool(self.flags & FLAG_THRESHOLD_CROSSED)

    def __str__(self) -> str:
        flags_str = []
        if self.flags & FLAG_NEW_SAMPLE:
            flags_str.append("NEW")
        if self.flags & FLAG_THRESHOLD_CROSSED:
            flags_str.append("THRESHOLD")

        return (f"[{self.timestamp_sec:.3f}s] {self.temp_celsius:6.2f}°C "
                f"({self.temp_mC:6d} mC) flags=[{','.join(flags_str) if flags_str else 'NONE'}]")


class SimTempDevice:
    """Interface to NXP SimTemp character device and sysfs"""

    def __init__(self, device_path: str = DEVICE_PATH, sysfs_base: str = SYSFS_BASE):
        self.device_path = device_path
        self.sysfs_base = Path(sysfs_base)
        self._fd: Optional[int] = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self, non_blocking: bool = False) -> None:
        """Open the character device"""
        if self._fd is not None:
            raise RuntimeError("Device already open")

        if not os.path.exists(self.device_path):
            raise FileNotFoundError(f"Device not found: {self.device_path}")

        flags = os.O_RDONLY
        if non_blocking:
            flags |= os.O_NONBLOCK

        self._fd = os.open(self.device_path, flags)

    def close(self) -> None:
        """Close the character device"""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def read_sample(self) -> TemperatureSample:
        """Read one temperature sample from the device"""
        if self._fd is None:
            raise RuntimeError("Device not open")

        try:
            data = os.read(self._fd, SAMPLE_SIZE)
        except BlockingIOError:
            raise TimeoutError("No data available (non-blocking mode)")
        except OSError as e:
            if e.errno == 4:  # EINTR - interrupted by signal
                raise KeyboardInterrupt("Read interrupted by signal")
            raise

        if len(data) != SAMPLE_SIZE:
            raise IOError(f"Partial read: expected {SAMPLE_SIZE} bytes, got {len(data)}")

        timestamp_ns, temp_mC, flags = struct.unpack(SAMPLE_FORMAT, data)
        return TemperatureSample(timestamp_ns, temp_mC, flags)

    def poll(self, timeout_ms: int = 1000) -> bool:
        """
        Poll the device for available data
        Returns True if data is available, False on timeout
        """
        if self._fd is None:
            raise RuntimeError("Device not open")

        poll_obj = select.poll()
        poll_obj.register(self._fd, select.POLLIN | select.POLLPRI)

        events = poll_obj.poll(timeout_ms)
        return len(events) > 0

    def read_samples_continuous(self, count: Optional[int] = None, callback=None):
        """
        Read samples continuously

        Args:
            count: Number of samples to read (None = infinite)
            callback: Function called for each sample: callback(sample)

        Yields:
            TemperatureSample objects
        """
        samples_read = 0

        try:
            while True:
                if count is not None and samples_read >= count:
                    break

                sample = self.read_sample()
                samples_read += 1

                if callback:
                    callback(sample)

                yield sample

        except KeyboardInterrupt:
            pass

    # Sysfs attribute access

    def _read_sysfs(self, attr: str) -> str:
        """Read a sysfs attribute"""
        path = self.sysfs_base / attr
        if not path.exists():
            raise FileNotFoundError(f"Sysfs attribute not found: {path}")
        return path.read_text().strip()

    def _write_sysfs(self, attr: str, value: str) -> None:
        """Write a sysfs attribute"""
        path = self.sysfs_base / attr
        if not path.exists():
            raise FileNotFoundError(f"Sysfs attribute not found: {path}")

        try:
            path.write_text(value + "\n")
        except PermissionError:
            raise PermissionError(f"Permission denied writing to {path}. Try sudo?")

    def get_sampling_ms(self) -> int:
        """Get current sampling period in milliseconds"""
        return int(self._read_sysfs("sampling_ms"))

    def set_sampling_ms(self, value: int) -> None:
        """Set sampling period in milliseconds (10-10000)"""
        if not 10 <= value <= 10000:
            raise ValueError(f"Sampling period must be 10-10000 ms, got {value}")
        self._write_sysfs("sampling_ms", str(value))

    def get_threshold_mC(self) -> int:
        """Get current threshold in milli-Celsius"""
        return int(self._read_sysfs("threshold_mC"))

    def set_threshold_mC(self, value: int) -> None:
        """Set threshold in milli-Celsius (-40000 to 125000)"""
        if not -40000 <= value <= 125000:
            raise ValueError(f"Threshold must be -40000 to 125000 mC, got {value}")
        self._write_sysfs("threshold_mC", str(value))

    def get_mode(self) -> str:
        """Get current temperature generation mode"""
        return self._read_sysfs("mode")

    def set_mode(self, mode: str) -> None:
        """Set temperature generation mode (normal, noisy, ramp)"""
        valid_modes = ["normal", "noisy", "ramp"]
        if mode not in valid_modes:
            raise ValueError(f"Mode must be one of {valid_modes}, got {mode}")
        self._write_sysfs("mode", mode)

    def get_stats(self) -> Dict[str, int]:
        """Get module statistics"""
        stats_text = self._read_sysfs("stats")
        stats = {}
        for line in stats_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                stats[key.strip()] = int(value.strip())
        return stats

    def get_config(self) -> Dict[str, any]:
        """Get current configuration"""
        return {
            'sampling_ms': self.get_sampling_ms(),
            'threshold_mC': self.get_threshold_mC(),
            'threshold_celsius': self.get_threshold_mC() / 1000.0,
            'mode': self.get_mode(),
        }

    @staticmethod
    def is_device_available() -> bool:
        """Check if the device is available"""
        return os.path.exists(DEVICE_PATH)

    @staticmethod
    def is_sysfs_available() -> bool:
        """Check if sysfs interface is available"""
        return Path(SYSFS_BASE).exists()


def celsius_to_mC(celsius: float) -> int:
    """Convert Celsius to milli-Celsius"""
    return int(celsius * 1000)


def mC_to_celsius(mC: int) -> float:
    """Convert milli-Celsius to Celsius"""
    return mC / 1000.0
