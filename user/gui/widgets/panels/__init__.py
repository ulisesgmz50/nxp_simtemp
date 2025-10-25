"""
GUI Panels Package
UI panel components for the application
"""

from widgets.panels.configuration import ConfigurationPanel
from widgets.panels.live_data import LiveDataPanel
from widgets.panels.event_log import EventLogPanel
from widgets.panels.status_bar import StatusBar

__all__ = ["ConfigurationPanel", "LiveDataPanel", "EventLogPanel", "StatusBar"]
