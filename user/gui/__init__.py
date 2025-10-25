"""
SimTemp GUI Application Package
Real-time temperature monitoring for embedded systems
Reading data from /dev/simtemp kernel module
"""

from widgets.app import SimTempMonitor
from core.config import Config

__all__ = ["SimTempMonitor", "Config"]
