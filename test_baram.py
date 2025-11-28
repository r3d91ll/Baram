#!/usr/bin/env python3
"""Unit tests for Baram cooling controller."""

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from baram import Baram, Config, DataLogger, HwmonDetector


class TestConfig(unittest.TestCase):
    """Tests for Config dataclass."""

    def test_default_values(self):
        """Test that Config has sensible defaults."""
        config = Config()
        self.assertEqual(config.min_temp, 40)
        self.assertEqual(config.max_temp, 80)
        self.assertEqual(config.min_pwm_value, 20)
        self.assertEqual(config.max_pwm_value, 255)
        self.assertEqual(config.gpu_index, 0)
        self.assertEqual(config.sleep_interval, 2)

    def test_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            min_temp=30,
            max_temp=90,
            gpu_index=1,
            hwmon_device="hwmon3"
        )
        self.assertEqual(config.min_temp, 30)
        self.assertEqual(config.max_temp, 90)
        self.assertEqual(config.gpu_index, 1)
        self.assertEqual(config.hwmon_device, "hwmon3")


class TestBaramPWMCalculation(unittest.TestCase):
    """Tests for Baram._calculate_pwm method."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(
            min_temp=40,
            max_temp=80,
            min_pwm_value=20,
            max_pwm_value=255
        )
        self.baram = Baram(self.config)

    def test_below_min_temp(self):
        """Test PWM at temperatures below minimum."""
        # Below min_temp should return actual_min_pwm
        self.assertEqual(self.baram._calculate_pwm(20), 20)
        self.assertEqual(self.baram._calculate_pwm(30), 20)
        self.assertEqual(self.baram._calculate_pwm(39), 20)

    def test_at_min_temp(self):
        """Test PWM at exactly min_temp."""
        # At 40°C, should be in the 30-40 range, returning at least min_pwm
        pwm = self.baram._calculate_pwm(40)
        self.assertGreaterEqual(pwm, 20)

    def test_mid_range_temps(self):
        """Test PWM increases with temperature."""
        pwm_50 = self.baram._calculate_pwm(50)
        pwm_60 = self.baram._calculate_pwm(60)
        pwm_70 = self.baram._calculate_pwm(70)

        # PWM should increase with temperature
        self.assertLess(pwm_50, pwm_60)
        self.assertLess(pwm_60, pwm_70)

    def test_at_max_temp(self):
        """Test PWM at maximum temperature."""
        pwm = self.baram._calculate_pwm(80)
        self.assertEqual(pwm, 255)

    def test_above_max_temp(self):
        """Test PWM above maximum temperature."""
        pwm = self.baram._calculate_pwm(90)
        self.assertEqual(pwm, 255)

    def test_spike_raises_minimum(self):
        """Test that wattage spike raises minimum PWM."""
        self.baram.actual_min_pwm = 100  # Simulate spike condition
        pwm = self.baram._calculate_pwm(30)  # Below min_temp
        self.assertEqual(pwm, 100)


class TestBaramSpikeTracking(unittest.TestCase):
    """Tests for Baram._update_spike_tracking method."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(
            wattage_threshold=200,
            wattage_spike_count=3,
            wattage_pwm_value=100,
            min_pwm_value=20
        )
        self.baram = Baram(self.config)

    def test_no_spike_below_threshold(self):
        """Test no spike detected below threshold."""
        self.baram._update_spike_tracking(150)
        self.assertEqual(self.baram.spike_count, 0)
        self.assertEqual(self.baram.actual_min_pwm, 20)

    def test_spike_increments_counter(self):
        """Test spike increments counter."""
        self.baram._update_spike_tracking(250)
        self.assertEqual(self.baram.spike_count, 1)
        self.assertEqual(self.baram.actual_min_pwm, 20)  # Not triggered yet

    def test_spike_triggers_after_count(self):
        """Test spike triggers after consecutive spikes."""
        for _ in range(4):  # Need > spike_count (3)
            self.baram._update_spike_tracking(250)

        self.assertGreater(self.baram.spike_count, 3)
        self.assertEqual(self.baram.actual_min_pwm, 100)

    def test_spike_decrements_when_normal(self):
        """Test spike counter decrements when power is normal."""
        # First trigger spike
        for _ in range(4):
            self.baram._update_spike_tracking(250)

        self.assertEqual(self.baram.actual_min_pwm, 100)

        # Now send normal readings
        for _ in range(5):
            self.baram._update_spike_tracking(150)

        self.assertEqual(self.baram.spike_count, 0)
        self.assertEqual(self.baram.actual_min_pwm, 20)


class TestDataLogger(unittest.TestCase):
    """Tests for DataLogger class."""

    def test_creates_header_on_new_file(self):
        """Test that header is written to new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.csv"
            logger = DataLogger(log_file)

            logger.log(50, 1500, 100, 150.5)

            # Read file and check header
            with open(log_file) as f:
                reader = csv.reader(f)
                header = next(reader)
                self.assertEqual(header, ["timestamp", "gpu_temp", "fan_rpm", "pwm_value", "gpu_power"])

    def test_logs_data_correctly(self):
        """Test that data is logged correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.csv"
            logger = DataLogger(log_file)

            logger.log(50, 1500, 100, 150.5)
            logger.log(60, 2000, 150, 200.0)

            # Read file and check data
            with open(log_file) as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                row1 = next(reader)
                row2 = next(reader)

            # Check data (skip timestamp)
            self.assertEqual(row1[1], "50")
            self.assertEqual(row1[2], "1500")
            self.assertEqual(row1[3], "100")
            self.assertEqual(row1[4], "150.5")

            self.assertEqual(row2[1], "60")
            self.assertEqual(row2[2], "2000")
            self.assertEqual(row2[3], "150")
            self.assertEqual(row2[4], "200.0")

    def test_handles_none_rpm(self):
        """Test that None RPM is handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.csv"
            logger = DataLogger(log_file)

            logger.log(50, None, 100, 150.5)

            with open(log_file) as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                row = next(reader)

            self.assertEqual(row[2], "N/A")


class TestHwmonDetector(unittest.TestCase):
    """Tests for HwmonDetector class."""

    def test_find_pwm_devices_empty_when_no_hwmon(self):
        """Test returns empty list when hwmon doesn't exist."""
        with patch.object(HwmonDetector, 'HWMON_BASE', Path('/nonexistent')):
            devices = HwmonDetector.find_pwm_devices()
            self.assertEqual(devices, [])

    def test_auto_detect_returns_none_when_no_devices(self):
        """Test auto_detect returns None when no devices found."""
        with patch.object(HwmonDetector, 'find_pwm_devices', return_value=[]):
            result = HwmonDetector.auto_detect()
            self.assertIsNone(result)

    def test_auto_detect_prefers_known_chips(self):
        """Test auto_detect prefers known motherboard chips."""
        mock_devices = [
            ("/sys/class/hwmon/hwmon0", "coretemp", [1]),
            ("/sys/class/hwmon/hwmon1", "nct6775", [1, 2, 3]),
            ("/sys/class/hwmon/hwmon2", "unknown", [1]),
        ]

        with patch.object(HwmonDetector, 'find_pwm_devices', return_value=mock_devices):
            result = HwmonDetector.auto_detect()
            self.assertEqual(result, ("/sys/class/hwmon/hwmon1", 1))

    def test_auto_detect_falls_back_to_first(self):
        """Test auto_detect falls back to first device if no preferred found."""
        mock_devices = [
            ("/sys/class/hwmon/hwmon0", "unknown1", [2, 3]),
            ("/sys/class/hwmon/hwmon1", "unknown2", [1]),
        ]

        with patch.object(HwmonDetector, 'find_pwm_devices', return_value=mock_devices):
            result = HwmonDetector.auto_detect()
            self.assertEqual(result, ("/sys/class/hwmon/hwmon0", 2))


if __name__ == "__main__":
    unittest.main()
