"""
Modern Rounded Button Widget
Pure Tkinter implementation without external dependencies
"""

import tkinter as tk


class RoundedButton(tk.Canvas):
    """Modern rounded button using Canvas"""

    def __init__(self, parent, text="Button", command=None, bg="#4a9eff", fg="white",
                 hover_bg="#6ab7ff", active_bg="#3a8eef", font=("Arial", 10, "bold"),
                 height=40, corner_radius=8, parent_bg="#2a2a3a", **kwargs):
        """
        Initialize rounded button

        Args:
            parent: Parent widget
            text: Button text
            command: Callback function
            bg: Background color
            fg: Text color
            hover_bg: Hover background color
            active_bg: Active (pressed) background color
            font: Text font
            height: Button height in pixels
            corner_radius: Corner radius in pixels
            parent_bg: Parent background color (to hide canvas edges)
        """
        super().__init__(parent, height=height, highlightthickness=0, bd=0, **kwargs)

        # Set canvas background to match parent (removes white borders)
        self.configure(bg=parent_bg)

        self.command = command
        self.text = text
        self.bg_color = bg
        self.fg_color = fg
        self.hover_bg_color = hover_bg
        self.active_bg_color = active_bg
        self.corner_radius = corner_radius
        self.font = font

        self.current_bg = bg
        self.is_pressed = False

        # Bind events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", self._on_configure)

        # Draw initial button
        self.after(10, self._draw_button)

    def _draw_button(self):
        """Draw the rounded button"""
        self.delete("all")

        width = self.winfo_width()
        height = self.winfo_height()

        if width < 2 or height < 2:
            width = 200
            height = 40

        # Draw rounded rectangle
        self._draw_rounded_rectangle(
            0, 0, width, height,
            self.corner_radius,
            fill=self.current_bg,
            outline=""
        )

        # Draw text
        self.create_text(
            width / 2, height / 2,
            text=self.text,
            fill=self.fg_color,
            font=self.font,
            tags="text"
        )

    def _draw_rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        """Draw a rounded rectangle on canvas"""
        points = [
            x1 + radius, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1 + radius,
            x1, y1
        ]

        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, event):
        """Handle mouse enter"""
        if not self.is_pressed:
            self.current_bg = self.hover_bg_color
            self._draw_button()
            self.config(cursor="hand2")

    def _on_leave(self, event):
        """Handle mouse leave"""
        if not self.is_pressed:
            self.current_bg = self.bg_color
            self._draw_button()
            self.config(cursor="")

    def _on_press(self, event):
        """Handle button press"""
        self.is_pressed = True
        self.current_bg = self.active_bg_color
        self._draw_button()

    def _on_release(self, event):
        """Handle button release"""
        self.is_pressed = False

        # Check if release is within button bounds
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.current_bg = self.hover_bg_color
            if self.command:
                self.command()
        else:
            self.current_bg = self.bg_color

        self._draw_button()

    def _on_configure(self, event):
        """Handle resize"""
        self._draw_button()

    def configure_text(self, text):
        """Update button text"""
        self.text = text
        self._draw_button()
