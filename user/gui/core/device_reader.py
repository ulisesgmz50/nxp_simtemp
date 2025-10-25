"""
Device Reader for GUI
Provides a thread-safe interface to read from /dev/simtemp for GUI applications
"""

import os
import sys
import threading
import queue
import time
from typing import Optional, Callable
from pathlib import Path

# Add CLI directory to path to import simtemp_device
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cli"))

try:
    from simtemp_device import (
        SimTempDevice,
        TemperatureSample,
        celsius_to_mC,
        mC_to_celsius,
        DEVICE_PATH,
        SYSFS_BASE,
    )
except ImportError as e:
    raise ImportError(f"Cannot import simtemp_device: {e}. Make sure CLI is available.")


class DeviceReader:
    """
    Thread-safe device reader for GUI applications

    Runs a background thread that continuously reads from /dev/simtemp
    and provides samples via a queue for the GUI to consume.
    """

    def __init__(self, callback: Optional[Callable[[TemperatureSample], None]] = None):
        """
        Initialize device reader

        Args:
            callback: Optional function to call with each new sample
        """
        self.device = SimTempDevice()
        self.callback = callback
        self.sample_queue = queue.Queue(maxsize=100)

        # Threading
        self._read_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        # Error tracking
        self.last_error: Optional[str] = None
        self.error_count = 0

        # Statistics
        self.samples_read = 0
        self.last_sample: Optional[TemperatureSample] = None

    def start(self) -> bool:
        """
        Start reading from device in background thread

        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            return True

        # Check if device is available
        if not SimTempDevice.is_device_available():
            self.last_error = f"Device not found: {DEVICE_PATH}. Is the module loaded?"
            return False

        if not SimTempDevice.is_sysfs_available():
            self.last_error = f"Sysfs not found: {SYSFS_BASE}. Is the module loaded?"
            return False

        # Open device in non-blocking mode
        try:
            self.device.open(non_blocking=True)
        except Exception as e:
            self.last_error = f"Failed to open device: {e}"
            return False

        # Start reading thread
        self._stop_event.clear()
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()
        self._running = True

        return True

    def stop(self) -> None:
        """Stop reading and clean up resources"""
        if not self._running:
            return

        self._stop_event.set()

        if self._read_thread:
            self._read_thread.join(timeout=2.0)

        try:
            self.device.close()
        except:
            pass

        self._running = False

    def _read_loop(self) -> None:
        """Background thread loop that reads samples"""
        while not self._stop_event.is_set():
            try:
                # Poll for new data with timeout
                if self.device.poll(timeout_ms=100):
                    sample = self.device.read_sample()

                    # Update statistics
                    self.samples_read += 1
                    self.last_sample = sample
                    self.last_error = None
                    self.error_count = 0

                    # Add to queue (non-blocking)
                    try:
                        self.sample_queue.put_nowait(sample)
                    except queue.Full:
                        # Queue full, discard oldest
                        try:
                            self.sample_queue.get_nowait()
                            self.sample_queue.put_nowait(sample)
                        except queue.Empty:
                            pass

                    # Call callback if provided
                    if self.callback:
                        try:
                            self.callback(sample)
                        except Exception as e:
                            # Don't let callback errors crash the reader
                            pass

            except TimeoutError:
                # No data available, this is normal with non-blocking
                continue
            except Exception as e:
                self.last_error = str(e)
                self.error_count += 1

                # If too many errors, slow down polling
                if self.error_count > 10:
                    time.sleep(0.5)

    def get_sample(self, timeout: float = 0.0) -> Optional[TemperatureSample]:
        """
        Get next sample from queue

        Args:
            timeout: Maximum time to wait for sample (0 = non-blocking)

        Returns:
            TemperatureSample or None if no sample available
        """
        try:
            return self.sample_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_all_samples(self) -> list[TemperatureSample]:
        """Get all available samples from queue"""
        samples = []
        while True:
            sample = self.get_sample(timeout=0.0)
            if sample is None:
                break
            samples.append(sample)
        return samples

    # Sysfs configuration methods (thread-safe)

    def get_sampling_ms(self) -> Optional[int]:
        """Get sampling period in milliseconds"""
        try:
            return self.device.get_sampling_ms()
        except Exception as e:
            self.last_error = f"Failed to read sampling_ms: {e}"
            return None

    def set_sampling_ms(self, value: int) -> bool:
        """Set sampling period in milliseconds (10-10000)"""
        try:
            self.device.set_sampling_ms(value)
            return True
        except Exception as e:
            self.last_error = f"Failed to set sampling_ms: {e}"
            return False

    def get_threshold_celsius(self) -> Optional[float]:
        """Get threshold in degrees Celsius"""
        try:
            return self.device.get_threshold_mC() / 1000.0
        except Exception as e:
            self.last_error = f"Failed to read threshold: {e}"
            return None

    def set_threshold_celsius(self, celsius: float) -> bool:
        """Set threshold in degrees Celsius"""
        try:
            self.device.set_threshold_mC(celsius_to_mC(celsius))
            return True
        except Exception as e:
            self.last_error = f"Failed to set threshold: {e}"
            return False

    def get_mode(self) -> Optional[str]:
        """Get temperature generation mode"""
        try:
            return self.device.get_mode()
        except Exception as e:
            self.last_error = f"Failed to read mode: {e}"
            return None

    def set_mode(self, mode: str) -> bool:
        """Set temperature generation mode (normal, noisy, ramp)"""
        try:
            self.device.set_mode(mode)
            return True
        except Exception as e:
            self.last_error = f"Failed to set mode: {e}"
            return False

    def get_stats(self) -> Optional[dict]:
        """Get module statistics"""
        try:
            return self.device.get_stats()
        except Exception as e:
            self.last_error = f"Failed to read stats: {e}"
            return None

    def get_config(self) -> Optional[dict]:
        """Get current configuration"""
        try:
            return self.device.get_config()
        except Exception as e:
            self.last_error = f"Failed to read config: {e}"
            return None

    @property
    def is_running(self) -> bool:
        """Check if reader is running"""
        return self._running

    @staticmethod
    def is_available() -> bool:
        """Check if device is available"""
        return SimTempDevice.is_device_available() and SimTempDevice.is_sysfs_available()
