"""
Event Log Panel
Displays system events with timestamps
"""

import tkinter as tk
from datetime import datetime


class EventLogPanel:
    """Panel for displaying system events"""

    def __init__(self, parent):
        # Main frame
        self.frame = tk.Frame(parent, bg="#0a0a15", height=180)
        self.frame.pack(fill="x", padx=30, pady=(15, 0))
        self.frame.pack_propagate(False)

        self._create_widgets()
        self._add_initial_events()

    def _create_widgets(self):
        """Create event log widgets"""
        # Title
        title = tk.Label(
            self.frame, text="Event Log", fg="white", bg="#0a0a15", font=("Arial", 12, "bold")
        )
        title.pack(pady=(15, 12), padx=20, anchor="w")

        # Create scrollable text widget
        text_frame = tk.Frame(self.frame, bg="#050510")
        text_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Text widget with scrollbar
        scrollbar = tk.Scrollbar(
            text_frame,
            bg="#1a1a25",
            troughcolor="#050510",
            activebackground="#4a9eff",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            text_frame,
            bg="#050510",
            fg="#888888",
            font=("Consolas", 9),
            wrap="none",
            yscrollcommand=scrollbar.set,
            height=8,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            insertbackground="#888888",
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=self.log_text.yview)

        # Configure text tags for different event types
        self.log_text.tag_config("timestamp", foreground="#4a7a9a")
        self.log_text.tag_config("normal", foreground="#888888")
        self.log_text.tag_config("warning", foreground="#ffaa00")
        self.log_text.tag_config("error", foreground="#ff4444")
        self.log_text.tag_config("info", foreground="#4a9eff")

    def _add_initial_events(self):
        """Add initial events to the log"""
        self.add_event("System initialized. Monitoring started.", "info")

    def add_event(self, message, event_type="normal"):
        """Add an event to the log"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

        # Insert timestamp
        self.log_text.insert("end", f"{timestamp} ", "timestamp")

        # Insert message with appropriate tag
        self.log_text.insert("end", f"{message}\n", event_type)

        # Auto-scroll to bottom
        self.log_text.see("end")

        # Keep only last 100 lines
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 100:
            self.log_text.delete("1.0", "2.0")
