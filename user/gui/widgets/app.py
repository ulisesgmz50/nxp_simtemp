"""
SimTemp Monitor Application
Main application window and coordinator
"""

import tkinter as tk
from tkinter import ttk

from widgets.panels.configuration import ConfigurationPanel
from widgets.panels.live_data import LiveDataPanel
from widgets.panels.event_log import EventLogPanel
from widgets.panels.status_bar import StatusBar
from core.device_reader import DeviceReader
from core.config import Config
from tkinter import messagebox


class SimTempMonitor:
    """Main application class"""

    def __init__(self, root):
        self.root = root
        self.config = Config()
        self.device_reader = DeviceReader()

        # Statistics tracking
        self.max_recorded = 25.0
        self.min_recorded = 25.0
        self.temp_history = []

        self._setup_window()
        self._setup_styles()
        self._create_widgets()
        self._start_monitoring()

    def _setup_window(self):
        """Configure the main window"""
        self.root.title("SimTemp Monitor")
        self.root.geometry("1100x750")
        self.root.configure(bg="#050510")
        self.root.resizable(True, True)
        self.root.minsize(900, 650)  # Minimum window size

    def _setup_styles(self):
        """Configure ttk styles for dark theme"""
        style = ttk.Style()
        style.theme_use("clam")

        # Configure very dark theme colors (darker than plot)
        bg_color = "#050510"  # Very dark main background
        panel_color = "#0a0a15"  # Very dark panels
        text_color = "#ffffff"
        accent_color = "#4a9eff"

        style.configure("Dark.TFrame", background=panel_color)
        style.configure("Dark.TLabel", background=panel_color, foreground=text_color)
        style.configure(
            "DarkTitle.TLabel",
            background=bg_color,
            foreground=text_color,
            font=("Arial", 24, "bold"),
        )
        style.configure(
            "DarkSubtitle.TLabel", background=bg_color, foreground="#888888", font=("Arial", 10)
        )

    def _create_widgets(self):
        """Create all GUI components"""
        # Title section
        title_frame = tk.Frame(self.root, bg="#050510", height=100)
        title_frame.pack(fill="x", padx=30, pady=(20, 0))

        title_label = ttk.Label(title_frame, text="SimTemp Monitor", style="DarkTitle.TLabel")
        title_label.pack(anchor="w")

        subtitle_label = ttk.Label(
            title_frame,
            text="Real-time temperature monitoring for embedded systems",
            style="DarkSubtitle.TLabel",
        )
        subtitle_label.pack(anchor="w")

        # Main content frame
        content_frame = tk.Frame(self.root, bg="#050510")
        content_frame.pack(fill="both", expand=True, padx=30, pady=15)

        # Left panel - Configuration
        left_frame = tk.Frame(content_frame, bg="#050510")
        left_frame.pack(side="left", fill="y", padx=(0, 15))

        self.config_panel = ConfigurationPanel(
            left_frame, self.config, self.on_config_change, self.device_reader
        )

        # Right panel - Live Data
        right_frame = tk.Frame(content_frame, bg="#1e1e2e")
        right_frame.pack(side="left", fill="both", expand=True)

        self.live_data_panel = LiveDataPanel(right_frame)

        # Bottom section - Event Log
        self.event_log = EventLogPanel(self.root)

        # Status Bar
        self.status_bar = StatusBar(self.root)

    def on_config_change(self, config):
        """Handle configuration changes"""
        # Configuration is now handled directly by ConfigurationPanel via sysfs
        # This callback is for UI updates only
        self.event_log.add_event("Configuration updated", "info")

    def _start_monitoring(self):
        """Start the temperature monitoring loop"""
        # Check if device is available
        if not DeviceReader.is_available():
            messagebox.showerror(
                "Device Not Found",
                "SimTemp device not found!\n\n"
                "Please ensure:\n"
                "1. Kernel module is loaded: sudo insmod kernel/nxp_simtemp.ko\n"
                "2. Device exists: /dev/simtemp\n"
                "3. Sysfs exists: /sys/class/misc/simtemp\n\n"
                "The application will now exit.",
            )
            self.root.quit()
            return

        # Start device reader
        if not self.device_reader.start():
            messagebox.showerror(
                "Device Error",
                f"Failed to start device reader:\n{self.device_reader.last_error}\n\n"
                "The application will now exit.",
            )
            self.root.quit()
            return

        self.event_log.add_event("Connected to /dev/simtemp", "info")
        self._update_temperature()

    def _update_temperature(self):
        """Update temperature readings and GUI"""
        # Get all available samples from device
        samples = self.device_reader.get_all_samples()

        # Process each sample
        for sample in samples:
            temp = sample.temp_celsius

            # Update statistics
            self.temp_history.append(temp)
            if len(self.temp_history) > 1000:
                self.temp_history.pop(0)
            self.max_recorded = max(self.max_recorded, temp)
            self.min_recorded = min(self.min_recorded, temp)

            # Update live data
            self.live_data_panel.update_temperature(temp)

            # Check threshold (from sample flags)
            if sample.is_threshold_crossed:
                self.event_log.add_event(
                    f"⚠️ THRESHOLD ALERT: Temperature {temp:.1f}°C exceeded threshold!", "error"
                )

        # Update status bar with real kernel stats
        stats = self.device_reader.get_stats()
        if stats:
            avg_temp = (
                sum(self.temp_history) / len(self.temp_history) if self.temp_history else 25.0
            )
            self.status_bar.update_stats(
                max_temp=self.max_recorded,
                min_temp=self.min_recorded,
                avg_temp=avg_temp,
                status=f"Monitoring ({stats.get('total_samples', 0)} samples)",
            )

        # Check for errors
        if self.device_reader.last_error:
            self.event_log.add_event(f"Device error: {self.device_reader.last_error}", "error")

        # Schedule next update (GUI refresh rate: 50ms = 20 FPS)
        self.root.after(50, self._update_temperature)
