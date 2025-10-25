"""
Modern Rounded Slider Widget
Custom slider with rounded thumb button
"""

import tkinter as tk


class RoundedSlider(tk.Canvas):
    """Custom slider with rounded thumb button"""

    def __init__(
        self,
        parent,
        from_=0,
        to=100,
        variable=None,
        resolution=1,
        bg="#0a0a15",
        track_bg="#050510",
        thumb_bg="#4a9eff",
        thumb_hover_bg="#6ab7ff",
        thumb_active_bg="#3a8eef",
        track_height=6,
        thumb_radius=10,
        width=250,
        **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=thumb_radius * 2 + 10,
            bg=bg,
            highlightthickness=0,
            bd=0,
            **kwargs
        )

        self.from_ = from_
        self.to = to
        self.resolution = resolution
        self.variable = variable
        self.track_bg = track_bg
        self.thumb_bg = thumb_bg
        self.thumb_hover_bg = thumb_hover_bg
        self.thumb_active_bg = thumb_active_bg
        self.track_height = track_height
        self.thumb_radius = thumb_radius
        self.slider_width = width

        self.dragging = False
        self.hovering = False

        # Draw initial slider
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._on_hover)
        self.bind("<Leave>", self._on_leave)

        # Update when variable changes externally
        if self.variable:
            self.variable.trace_add("write", lambda *args: self._draw())

    def _get_value(self):
        """Get current value"""
        if self.variable:
            return self.variable.get()
        return self.from_

    def _set_value(self, value):
        """Set value with resolution rounding"""
        value = max(self.from_, min(self.to, value))
        value = round(value / self.resolution) * self.resolution
        if self.variable:
            self.variable.set(int(value))

    def _value_to_x(self, value):
        """Convert value to x coordinate"""
        width = self.winfo_width()
        if width <= 1:
            width = self.slider_width

        margin = self.thumb_radius + 5
        track_width = width - 2 * margin
        ratio = (value - self.from_) / (self.to - self.from_)
        return margin + ratio * track_width

    def _x_to_value(self, x):
        """Convert x coordinate to value"""
        width = self.winfo_width()
        if width <= 1:
            width = self.slider_width

        margin = self.thumb_radius + 5
        track_width = width - 2 * margin
        x = max(margin, min(width - margin, x))
        ratio = (x - margin) / track_width
        value = self.from_ + ratio * (self.to - self.from_)
        return value

    def _draw(self):
        """Draw the slider"""
        self.delete("all")

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1:
            width = self.slider_width
        if height <= 1:
            height = self.thumb_radius * 2 + 10

        center_y = height / 2
        margin = self.thumb_radius + 5

        # Draw track (rounded rectangle)
        track_radius = self.track_height / 2
        self.create_rounded_rect(
            margin,
            center_y - track_radius,
            width - margin,
            center_y + track_radius,
            track_radius,
            fill=self.track_bg,
            outline="",
        )

        # Draw filled portion (progress)
        value = self._get_value()
        thumb_x = self._value_to_x(value)
        self.create_rounded_rect(
            margin,
            center_y - track_radius,
            thumb_x,
            center_y + track_radius,
            track_radius,
            fill=self.thumb_bg,
            outline="",
        )

        # Draw thumb (rounded circle)
        thumb_color = self.thumb_bg
        if self.dragging:
            thumb_color = self.thumb_active_bg
        elif self.hovering:
            thumb_color = self.thumb_hover_bg

        self.create_oval(
            thumb_x - self.thumb_radius,
            center_y - self.thumb_radius,
            thumb_x + self.thumb_radius,
            center_y + self.thumb_radius,
            fill=thumb_color,
            outline="",
            tags="thumb",
        )

        # Add subtle shadow/depth to thumb
        self.create_oval(
            thumb_x - self.thumb_radius + 2,
            center_y - self.thumb_radius + 2,
            thumb_x + self.thumb_radius - 2,
            center_y + self.thumb_radius - 2,
            fill="",
            outline=self._lighten_color(thumb_color),
            width=1,
            tags="thumb",
        )

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Draw a rounded rectangle"""
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _lighten_color(self, color):
        """Lighten a hex color for highlight effect"""
        if color.startswith("#"):
            color = color[1:]
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r = min(255, r + 30)
        g = min(255, g + 30)
        b = min(255, b + 30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _is_over_thumb(self, x, y):
        """Check if mouse is over thumb"""
        value = self._get_value()
        thumb_x = self._value_to_x(value)
        height = self.winfo_height()
        if height <= 1:
            height = self.thumb_radius * 2 + 10
        center_y = height / 2

        distance = ((x - thumb_x) ** 2 + (y - center_y) ** 2) ** 0.5
        return distance <= self.thumb_radius

    def _on_press(self, event):
        """Handle mouse press"""
        if self._is_over_thumb(event.x, event.y):
            self.dragging = True
        else:
            # Jump to clicked position
            value = self._x_to_value(event.x)
            self._set_value(value)
            self.dragging = True
        self._draw()

    def _on_drag(self, event):
        """Handle mouse drag"""
        if self.dragging:
            value = self._x_to_value(event.x)
            self._set_value(value)
            self._draw()

    def _on_release(self, event):
        """Handle mouse release"""
        self.dragging = False
        self._draw()

    def _on_hover(self, event):
        """Handle mouse hover"""
        was_hovering = self.hovering
        self.hovering = self._is_over_thumb(event.x, event.y)
        if was_hovering != self.hovering:
            self._draw()

    def _on_leave(self, event):
        """Handle mouse leave"""
        self.hovering = False
        self._draw()
