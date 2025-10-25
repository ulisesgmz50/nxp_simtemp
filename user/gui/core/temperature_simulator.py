"""
Temperature Simulator
Generates realistic temperature data for monitoring
"""

import math
import random
from collections import deque


class TemperatureSimulator:
    """Simulates temperature sensor readings"""

    def __init__(self):
        """Initialize the temperature simulator"""
        self.base_temp = 25.0
        self.tick_count = 0
        self.noise_factor = 0.5

        # Statistics tracking
        self.temperature_history = deque(maxlen=1000)
        self.max_recorded = 25.0
        self.min_recorded = 25.0

        # Wave parameters for realistic variation
        self.wave1_freq = 0.05
        self.wave1_amp = 15.0
        self.wave2_freq = 0.13
        self.wave2_amp = 8.0
        self.wave3_freq = 0.31
        self.wave3_amp = 3.0

        # Drift parameters
        self.drift_rate = 0.01
        self.drift_target = 25.0

    def get_temperature(self):
        """Generate a temperature reading"""
        # Calculate base temperature with multiple sine waves
        temp = self.base_temp
        temp += self.wave1_amp * math.sin(self.tick_count * self.wave1_freq)
        temp += self.wave2_amp * math.sin(self.tick_count * self.wave2_freq)
        temp += self.wave3_amp * math.sin(self.tick_count * self.wave3_freq)

        # Add some random noise
        temp += random.gauss(0, self.noise_factor)

        # Apply gradual drift
        self.base_temp += (self.drift_target - self.base_temp) * self.drift_rate

        # Occasionally change drift target
        if random.random() < 0.01:
            self.drift_target = random.uniform(20, 35)

        # Simulate occasional spikes
        if random.random() < 0.005:
            temp += random.uniform(10, 25)

        # Clamp to realistic range
        temp = max(15, min(100, temp))

        # Update statistics
        self.temperature_history.append(temp)
        self.max_recorded = max(self.max_recorded, temp)
        self.min_recorded = min(self.min_recorded, temp)

        self.tick_count += 1

        return temp

    def get_average(self):
        """Calculate average temperature"""
        if not self.temperature_history:
            return self.base_temp
        return sum(self.temperature_history) / len(self.temperature_history)

    def update_config(self, config):
        """Update simulator based on configuration changes"""
        # Adjust simulation parameters based on thresholds
        if config.max_temp > 80:
            self.drift_target = random.uniform(25, 40)
        else:
            self.drift_target = random.uniform(20, 30)

    def reset(self):
        """Reset the simulator"""
        self.base_temp = 25.0
        self.tick_count = 0
        self.temperature_history.clear()
        self.max_recorded = 25.0
        self.min_recorded = 25.0
        self.drift_target = 25.0
