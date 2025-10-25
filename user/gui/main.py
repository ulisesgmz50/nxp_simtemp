#!/usr/bin/env python3
"""
SimTemp Monitor - Real-time temperature monitoring for embedded systems
Main application entry point
"""

import tkinter as tk
from widgets.app import SimTempMonitor


def main():
    """Initialize and run the application"""
    root = tk.Tk()
    app = SimTempMonitor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
