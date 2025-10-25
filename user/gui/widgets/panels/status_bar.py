"""
Status Bar
Displays system statistics and status
"""

import tkinter as tk


class StatusBar:
    """Bottom status bar with statistics"""

    def __init__(self, parent):
        # Main frame
        self.frame = tk.Frame(parent, bg="#050510", height=40)
        self.frame.pack(fill="x", side="bottom")
        self.frame.pack_propagate(False)

        self._create_widgets()

    def _create_widgets(self):
        """Create status bar widgets"""
        # Statistics container
        stats_frame = tk.Frame(self.frame, bg="#050510")
        stats_frame.pack(side="left", padx=30, fill="y")

        # Max Temperature
        self.max_label = self._create_stat_label(stats_frame, "Max Temp:", "91.0°C")
        self.max_label.pack(side="left", padx=(0, 25))

        # Min Temperature
        self.min_label = self._create_stat_label(stats_frame, "Min Temp:", "25.3°C")
        self.min_label.pack(side="left", padx=(0, 25))

        # Average Temperature
        self.avg_label = self._create_stat_label(stats_frame, "Avg Temp:", "58.0°C")
        self.avg_label.pack(side="left")

        # Status indicator
        status_frame = tk.Frame(self.frame, bg="#050510")
        status_frame.pack(side="right", padx=30, fill="y")

        # Status indicator dot
        self.status_dot = tk.Canvas(
            status_frame, width=10, height=10, bg="#050510", highlightthickness=0
        )
        self.status_dot.pack(side="left", pady=15, padx=(0, 5))
        self.status_dot.create_oval(2, 2, 8, 8, fill="#00ff00", outline="")

        # Status text
        self.status_label = tk.Label(
            status_frame, text="Status: Monitoring", fg="#888888", bg="#050510", font=("Arial", 10)
        )
        self.status_label.pack(side="left", pady=10)

    def _create_stat_label(self, parent, label, value):
        """Create a statistics label"""
        frame = tk.Frame(parent, bg="#050510")

        label_widget = tk.Label(frame, text=label, fg="#666666", bg="#050510", font=("Arial", 9))
        label_widget.pack(side="left")

        value_widget = tk.Label(
            frame, text=value, fg="white", bg="#050510", font=("Arial", 10, "bold")
        )
        value_widget.pack(side="left", padx=(3, 0))

        return frame

    def update_stats(self, max_temp, min_temp, avg_temp, status):
        """Update status bar statistics"""
        # Update temperature stats
        for widget in self.max_label.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("font")[1] == 10:
                widget.config(text=f"{max_temp:.1f}°C")

        for widget in self.min_label.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("font")[1] == 10:
                widget.config(text=f"{min_temp:.1f}°C")

        for widget in self.avg_label.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("font")[1] == 10:
                widget.config(text=f"{avg_temp:.1f}°C")

        # Update status
        self.status_label.config(text=f"Status: {status}")

        # Update status indicator color
        if status == "Monitoring":
            color = "#00ff00"  # Green
        elif status == "Warning":
            color = "#ffaa00"  # Orange
        else:
            color = "#ff4444"  # Red

        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 8, 8, fill=color, outline="")
