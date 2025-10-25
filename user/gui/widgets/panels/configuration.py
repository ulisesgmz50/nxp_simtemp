"""
Configuration Panel
Handles all configuration controls
"""

import tkinter as tk
from tkinter import ttk
from widgets.modern_button import RoundedButton
from widgets.modern_slider import RoundedSlider


class ConfigurationPanel:
    """Panel for temperature monitoring configuration"""

    def __init__(self, parent, config, callback, device_reader=None):
        self.config = config
        self.callback = callback
        self.device_reader = device_reader

        # Main frame (very dark)
        self.frame = tk.Frame(parent, bg="#0a0a15", width=300)
        self.frame.pack(fill="both", expand=True)
        self.frame.pack_propagate(False)

        self._create_widgets()

    def _create_widgets(self):
        """Create all configuration widgets"""
        # Title
        title = tk.Label(
            self.frame, text="Configuration", fg="white", bg="#0a0a15", font=("Arial", 14, "bold")
        )
        title.pack(pady=(20, 25), padx=20, anchor="w")

        # Sampling Period (in milliseconds for kernel module)
        self._create_sampling_period()

        # Temperature Threshold
        self._create_threshold_input()

        # Temperature Mode Selection
        self._create_mode_selector()

        # Buttons
        self._create_buttons()

    def _create_sampling_period(self):
        """Create sampling period slider (in milliseconds)"""
        label = tk.Label(
            self.frame, text="Sampling Period (ms)", fg="#888888", bg="#0a0a15", font=("Arial", 10)
        )
        label.pack(padx=20, anchor="w", pady=(0, 8))

        slider_frame = tk.Frame(self.frame, bg="#0a0a15")
        slider_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Kernel module supports 10-10000 ms, use common values
        self.sampling_var = tk.IntVar(value=100)  # Default 100ms

        # Modern rounded slider
        slider = RoundedSlider(
            slider_frame,
            from_=100,
            to=1000,
            variable=self.sampling_var,
            resolution=10,  # Steps of 10ms
            bg="#0a0a15",
            track_bg="#050510",
            thumb_bg="#4a9eff",
            thumb_hover_bg="#6ab7ff",
            thumb_active_bg="#3a8eef",
            track_height=6,
            thumb_radius=10,
        )
        slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        value_label = tk.Label(
            slider_frame, textvariable=self.sampling_var, fg="white", bg="#0a0a15", width=5
        )
        value_label.pack(side="right", padx=(5, 0))

    def _create_threshold_input(self):
        """Create temperature threshold input"""
        label = tk.Label(
            self.frame,
            text="Temperature Threshold (°C)",
            fg="#888888",
            bg="#0a0a15",
            font=("Arial", 10),
        )
        label.pack(padx=20, anchor="w", pady=(15, 8))

        self.threshold_var = tk.StringVar(value="45.0")

        # Create a frame to simulate rounded corners
        entry_container = tk.Frame(self.frame, bg="#050510", highlightthickness=0)
        entry_container.pack(fill="x", padx=20, pady=(0, 15))

        threshold_entry = tk.Entry(
            entry_container,
            textvariable=self.threshold_var,
            bg="#050510",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Arial", 11),
            borderwidth=0,
            highlightthickness=0,
        )
        threshold_entry.pack(fill="x", padx=10, pady=8)

    def _create_mode_selector(self):
        """Create temperature generation mode selector"""
        label = tk.Label(
            self.frame, text="Temperature Mode", fg="#888888", bg="#0a0a15", font=("Arial", 10)
        )
        label.pack(padx=20, anchor="w", pady=(15, 8))

        # Mode buttons
        mode_frame = tk.Frame(self.frame, bg="#0a0a15")
        mode_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.mode_var = tk.StringVar(value="normal")

        modes = [
            ("Normal", "normal"),
            ("Noisy", "noisy"),
            ("Ramp", "ramp"),
        ]

        for i, (display_name, mode_value) in enumerate(modes):
            btn = tk.Radiobutton(
                mode_frame,
                text=display_name,
                variable=self.mode_var,
                value=mode_value,
                bg="#0a0a15",
                fg="white",
                selectcolor="#4a9eff",
                activebackground="#0a0a15",
                activeforeground="white",
                font=("Arial", 9),
                highlightthickness=0,
                borderwidth=0,
                relief="flat",
            )
            btn.pack(anchor="w", pady=2)

    def _create_buttons(self):
        """Create action buttons"""
        # Apply Changes button (primary)
        apply_btn = RoundedButton(
            self.frame,
            text="Apply Changes",
            command=self._apply_changes,
            bg="#4a9eff",
            fg="white",
            hover_bg="#6ab7ff",
            active_bg="#3a8eef",
            font=("Arial", 10, "bold"),
            height=42,
            corner_radius=10,
            parent_bg="#0a0a15",
        )
        apply_btn.pack(fill="x", padx=20, pady=(0, 12))

        # Reset to Default button (secondary)
        reset_btn = RoundedButton(
            self.frame,
            text="Reset to Default",
            command=self._reset_defaults,
            bg="#1a1a25",
            fg="#888888",
            hover_bg="#2a2a35",
            active_bg="#0a0a15",
            font=("Arial", 10),
            height=38,
            corner_radius=8,
            parent_bg="#0a0a15",
        )
        reset_btn.pack(fill="x", padx=20, pady=(0, 20))

    def _apply_changes(self):
        """Apply configuration changes to kernel module via sysfs"""
        if not self.device_reader:
            # Fallback to old config object if no device reader
            try:
                self.config.sampling_period = self.sampling_var.get()
                self.callback(self.config)
            except ValueError:
                pass
            return

        success = True
        errors = []

        try:
            # Set sampling period (in milliseconds)
            sampling_ms = self.sampling_var.get()
            if not self.device_reader.set_sampling_ms(sampling_ms):
                errors.append(f"Sampling period: {self.device_reader.last_error}")
                success = False
        except ValueError as e:
            errors.append(f"Invalid sampling period: {e}")
            success = False

        try:
            # Set threshold (convert to Celsius)
            threshold_c = float(self.threshold_var.get())
            if not self.device_reader.set_threshold_celsius(threshold_c):
                errors.append(f"Threshold: {self.device_reader.last_error}")
                success = False
        except ValueError as e:
            errors.append(f"Invalid threshold: {e}")
            success = False

        try:
            # Set mode
            mode = self.mode_var.get()
            if not self.device_reader.set_mode(mode):
                errors.append(f"Mode: {self.device_reader.last_error}")
                success = False
        except Exception as e:
            errors.append(f"Mode error: {e}")
            success = False

        # Show result
        if success:
            from tkinter import messagebox

            messagebox.showinfo("Success", "Configuration updated successfully!")
            self.callback(self.config)
        else:
            from tkinter import messagebox

            messagebox.showerror("Configuration Error", "\n".join(errors))

    def _reset_defaults(self):
        """Reset to default configuration"""
        # Set default values
        self.sampling_var.set(100)  # 100ms
        self.threshold_var.set("45.0")  # 45°C
        self.mode_var.set("normal")

        # Apply to device if available
        if self.device_reader:
            self.device_reader.set_sampling_ms(100)
            self.device_reader.set_threshold_celsius(45.0)
            self.device_reader.set_mode("normal")

        self.callback(self.config)
