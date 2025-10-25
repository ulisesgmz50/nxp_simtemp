"""
Configuration Module
Manages application configuration settings
"""


class Config:
    """Application configuration settings"""

    # Default values
    DEFAULT_SAMPLING_PERIOD = 5  # seconds
    DEFAULT_MIN_TEMP = 75.0  # °C
    DEFAULT_MAX_TEMP = 90.0  # °C

    def __init__(self):
        """Initialize with default values"""
        self.reset_defaults()

    def reset_defaults(self):
        """Reset all settings to default values"""
        self.sampling_period = self.DEFAULT_SAMPLING_PERIOD
        self.min_temp = self.DEFAULT_MIN_TEMP
        self.max_temp = self.DEFAULT_MAX_TEMP

    @property
    def threshold_range(self):
        """Get the temperature threshold range"""
        return (self.min_temp, self.max_temp)

    def validate(self):
        """Validate configuration values"""
        # Ensure sampling period is within bounds
        self.sampling_period = max(1, min(10, self.sampling_period))

        # Ensure temperature thresholds are valid
        if self.min_temp >= self.max_temp:
            self.min_temp = self.max_temp - 1

        self.min_temp = max(0, min(100, self.min_temp))
        self.max_temp = max(self.min_temp + 1, min(150, self.max_temp))

        return True
