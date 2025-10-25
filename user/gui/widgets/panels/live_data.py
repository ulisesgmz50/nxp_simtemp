"""
Live Data Panel
Displays real-time temperature graph with axis labels and current reading from kernel module
"""

import tkinter as tk
from collections import deque
import time


class LiveDataPanel:
    """Panel for displaying live temperature data"""

    def __init__(self, parent):
        self.temperature_history = deque(maxlen=100)
        self.time_history = deque(maxlen=100)
        self.start_time = time.time()

        # Main frame (very dark)
        self.frame = tk.Frame(parent, bg="#0a0a15")
        self.frame.pack(fill="both", expand=True)

        self._create_widgets()

    def _create_widgets(self):
        """Create all live data widgets"""
        # Header with title and current temp in same row
        header_frame = tk.Frame(self.frame, bg="#0a0a15")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        # Left side - Title
        title_container = tk.Frame(header_frame, bg="#0a0a15")
        title_container.pack(side="left", fill="x", expand=True)

        title = tk.Label(
            title_container, text="Live Temperature Plot", fg="white", bg="#0a0a15", font=("Arial", 14, "bold")
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            title_container,
            text="Real-time readings from /dev/simtemp",
            fg="#888888",
            bg="#0a0a15",
            font=("Arial", 9),
        )
        subtitle.pack(anchor="w")

        # Right side - Compact current temp display
        temp_compact_frame = tk.Frame(header_frame, bg="#0a0a15", relief="flat", bd=0)
        temp_compact_frame.pack(side="right", padx=10)

        # Status category (top)
        self.status_label = tk.Label(
            temp_compact_frame,
            text="Waiting",
            fg="#888888",
            bg="#0a0a15",
            font=("Arial", 9, "bold")
        )
        self.status_label.pack(pady=(5, 0))

        # Temperature value (below status)
        self.temp_display = tk.Label(
            temp_compact_frame,
            text="--.-°C",
            fg="#4a9eff",
            bg="#0a0a15",
            font=("Arial", 20, "bold")
        )
        self.temp_display.pack(pady=(0, 5))

        # Main graph container (bigger!)
        graph_container = tk.Frame(self.frame, bg="#0a0a15")
        graph_container.pack(fill="both", expand=True, padx=25, pady=(10, 25))

        # Y-axis label (vertical text)
        y_label_frame = tk.Frame(graph_container, bg="#0a0a15", width=20)
        y_label_frame.pack(side="left", fill="y")

        # Create vertical text using Canvas
        self.y_label_canvas = tk.Canvas(y_label_frame, bg="#0a0a15", width=20, highlightthickness=0)
        self.y_label_canvas.pack(fill="both", expand=True)

        # Draw vertical text (will be drawn in _draw_y_label after canvas is ready)
        self.y_label_canvas.bind("<Configure>", lambda e: self._draw_y_label())

        # Graph area with X-axis label
        graph_area = tk.Frame(graph_container, bg="#0a0a15")
        graph_area.pack(side="left", fill="both", expand=True)

        # Canvas for graph
        self.canvas = tk.Canvas(graph_area, bg="#050510", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # X-axis label
        x_label = tk.Label(
            graph_area,
            text="Time (seconds)",
            fg="#888888",
            bg="#0a0a15",
            font=("Arial", 9)
        )
        x_label.pack(pady=(5, 0))

    def update_temperature(self, temperature):
        """Update temperature display and graph"""
        # Record time
        current_time = time.time() - self.start_time

        # Update main display
        self.temp_display.config(text=f"{temperature:.1f}°C")

        # Update status based on temperature range (TradingView colors)
        if temperature < 20:
            status = "Cold"
            color = "#2196F3"  # Blue
        elif temperature < 40:
            status = "Normal"
            color = "#26a69a"  # TradingView green/teal
        elif temperature < 60:
            status = "Warm"
            color = "#FF9800"  # Orange
        else:
            status = "Hot"
            color = "#F44336"  # Red

        self.status_label.config(text=status, fg=color)
        self.temp_display.config(fg=color)

        # Add to history
        self.temperature_history.append(temperature)
        self.time_history.append(current_time)

        # Redraw graph
        self._draw_graph()

    def _draw_y_label(self):
        """Draw the vertical Y-axis label"""
        self.y_label_canvas.delete("all")

        height = self.y_label_canvas.winfo_height()
        width = self.y_label_canvas.winfo_width()

        if height < 2:
            height = 300
            width = 20

        # Draw text vertically (rotated 90 degrees counter-clockwise)
        x = width / 2
        y = height / 2

        self.y_label_canvas.create_text(
            x, y,
            text="Temperature (°C)",
            fill="#888888",
            font=("Arial", 9),
            angle=90,  # Rotate 90 degrees
            anchor="center"
        )

    def _draw_graph(self):
        """Draw the temperature graph with axis labels and grid"""
        self.canvas.delete("all")

        if len(self.temperature_history) < 2:
            # Show "waiting for data" message
            self.canvas.create_text(
                self.canvas.winfo_width() / 2 if self.canvas.winfo_width() > 1 else 200,
                self.canvas.winfo_height() / 2 if self.canvas.winfo_height() > 1 else 100,
                text="Waiting for data...",
                fill="#888888",
                font=("Arial", 12),
            )
            return

        # Get canvas dimensions
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 1:  # Canvas not yet rendered
            width = 600
            height = 350

        # Margins for axis labels and values
        margin_left = 45
        margin_right = 20
        margin_top = 20
        margin_bottom = 30

        plot_width = width - margin_left - margin_right
        plot_height = height - margin_top - margin_bottom

        # Calculate scaling
        temps = list(self.temperature_history)
        times = list(self.time_history)

        min_temp = min(temps) - 2
        max_temp = max(temps) + 2
        temp_range = max_temp - min_temp if max_temp > min_temp else 1

        min_time = times[0]
        max_time = times[-1]
        time_range = max_time - min_time if max_time > min_time else 1

        # Draw background grid (TradingView style - subtle grid)
        num_horizontal_lines = 5
        for i in range(num_horizontal_lines + 1):
            y = margin_top + (i / num_horizontal_lines) * plot_height
            # Thinner, more subtle grid lines
            self.canvas.create_line(
                margin_left, y, width - margin_right, y, fill="#7385d3", width=1, dash=(2, 4)
            )

            # Y-axis labels (brighter for better visibility)
            temp_value = max_temp - (i / num_horizontal_lines) * temp_range
            self.canvas.create_text(
                margin_left - 10,
                y,
                text=f"{temp_value:.0f}",
                fill="#b0b0b0",
                font=("Arial", 8),
                anchor="e",
            )

        # Draw vertical grid lines
        num_vertical_lines = 5
        for i in range(num_vertical_lines + 1):
            x = margin_left + (i / num_vertical_lines) * plot_width
            self.canvas.create_line(
                x, margin_top, x, height - margin_bottom, fill="#7385d3", width=1, dash=(2, 4)
            )

            # X-axis labels (time)
            if time_range > 0:
                time_value = min_time + (i / num_vertical_lines) * time_range
                self.canvas.create_text(
                    x,
                    height - margin_bottom + 10,
                    text=f"{time_value:.0f}",
                    fill="#b0b0b0",
                    font=("Arial", 8),
                )

        # Draw axis lines (more subtle)
        # Y-axis
        self.canvas.create_line(
            margin_left, margin_top, margin_left, height - margin_bottom, fill="#2a3f5a", width=1
        )

        # X-axis
        self.canvas.create_line(
            margin_left,
            height - margin_bottom,
            width - margin_right,
            height - margin_bottom,
            fill="#2a3f5a",
            width=1,
        )

        # Draw temperature curve
        points = []
        for i, (temp, t) in enumerate(zip(temps, times)):
            if time_range > 0:
                x = margin_left + ((t - min_time) / time_range) * plot_width
            else:
                x = margin_left + (i / (len(temps) - 1)) * plot_width

            y = height - margin_bottom - ((temp - min_temp) / temp_range) * plot_height
            points.extend([x, y])

        if len(points) >= 4:
            # TradingView style: Fill area under the curve with gradient effect
            # Create filled polygon for area under curve
            fill_points = points.copy()
            fill_points.extend([width - margin_right, height - margin_bottom])
            fill_points.extend([margin_left, height - margin_bottom])

            # Semi-transparent fill under the line (like TradingView)
            self.canvas.create_polygon(
                fill_points,
                fill="#26a69a",  # Teal/green color
                outline="",
                stipple="gray25"  # Creates transparency effect
            )

            # Draw the main line (TradingView green)
            self.canvas.create_line(
                points,
                fill="#26a69a",  # TradingView teal/green
                width=2,
                smooth=True
            )

            # Draw glowing effect line (brighter overlay)
            self.canvas.create_line(
                points,
                fill="#4ade80",  # Bright green glow
                width=1,
                smooth=True
            )

            # Draw points for each data point (TradingView style - small dots)
            for i in range(0, len(points), 2):
                x, y = points[i], points[i + 1]
                self.canvas.create_oval(
                    x - 1.5, y - 1.5, x + 1.5, y + 1.5,
                    fill="#4ade80",  # Bright green
                    outline="#26a69a",
                    width=1
                )
