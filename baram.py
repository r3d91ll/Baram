#!/usr/bin/env python3
"""
Baram - Advanced System Cooling Management Tool

A Linux utility for managing fans on datacenter GPUs (like Tesla P40) mounted
in ATX cases. Named after the Korean word for wind.

This tool monitors GPU temperature and power consumption via NVML and controls
motherboard fan headers via the Linux hwmon interface.
"""

import argparse
import configparser
import csv
import datetime
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

try:
    import pynvml
except ImportError:
    print("Error: pynvml not installed. Run: pip install pynvml", file=sys.stderr)
    sys.exit(1)


@dataclass
class Config:
    """Configuration settings for Baram."""
    min_temp: int = 40
    max_temp: int = 80
    min_pwm_value: int = 20
    max_pwm_value: int = 255
    pwm_step: int = 5
    temp_drop: int = 3
    wattage_threshold: int = 200
    wattage_pwm_value: int = 100
    wattage_spike_count: int = 3
    sleep_interval: int = 2
    gpu_index: int = 0
    hwmon_device: str = ""  # Auto-detected if empty
    pwm_channel: int = 1
    log_dir: str = "/var/log/baram"
    config_file: str = "/etc/baram/baram.conf"


class HwmonDetector:
    """Detects and validates hwmon devices for fan control."""

    HWMON_BASE = Path("/sys/class/hwmon")

    @classmethod
    def find_pwm_devices(cls) -> List[Tuple[str, str, List[int]]]:
        """
        Find all hwmon devices that support PWM fan control.

        Returns:
            List of tuples: (hwmon_path, device_name, available_pwm_channels)
        """
        devices = []

        if not cls.HWMON_BASE.exists():
            return devices

        for hwmon_dir in sorted(cls.HWMON_BASE.iterdir()):
            if not hwmon_dir.is_dir():
                continue

            # Get device name
            name_file = hwmon_dir / "name"
            device_name = "unknown"
            if name_file.exists():
                device_name = name_file.read_text().strip()

            # Find available PWM channels
            pwm_channels = []
            for i in range(1, 10):  # Check pwm1 through pwm9
                pwm_file = hwmon_dir / f"pwm{i}"
                pwm_enable = hwmon_dir / f"pwm{i}_enable"
                if pwm_file.exists() and pwm_enable.exists():
                    pwm_channels.append(i)

            if pwm_channels:
                devices.append((str(hwmon_dir), device_name, pwm_channels))

        return devices

    @classmethod
    def auto_detect(cls, preferred_names: Optional[List[str]] = None) -> Optional[Tuple[str, int]]:
        """
        Auto-detect the best hwmon device for fan control.

        Args:
            preferred_names: List of preferred device names to prioritize

        Returns:
            Tuple of (hwmon_path, pwm_channel) or None if not found
        """
        devices = cls.find_pwm_devices()

        if not devices:
            return None

        # Common motherboard chip names for fan control
        if preferred_names is None:
            preferred_names = [
                "nct6775", "nct6776", "nct6779", "nct6791", "nct6792",
                "nct6793", "nct6795", "nct6796", "nct6797", "nct6798",
                "it8720", "it8721", "it8728", "it8732", "it8771", "it8772",
                "it8781", "it8782", "it8783", "it8786", "it8790",
                "w83627", "w83667", "w83795",
                "f71882fg", "f71889fg",
                "asus_wmi_sensors", "asus-ec-sensors",
            ]

        # Try preferred devices first
        for hwmon_path, name, channels in devices:
            if any(pref.lower() in name.lower() for pref in preferred_names):
                return (hwmon_path, channels[0])

        # Fall back to first available device with PWM
        if devices:
            return (devices[0][0], devices[0][2][0])

        return None


class FanController:
    """Controls fan speed via hwmon PWM interface."""

    def __init__(self, hwmon_path: str, pwm_channel: int = 1):
        """
        Initialize fan controller.

        Args:
            hwmon_path: Path to hwmon device (e.g., /sys/class/hwmon/hwmon2)
            pwm_channel: PWM channel number (default: 1)
        """
        self.hwmon_path = Path(hwmon_path)
        self.pwm_channel = pwm_channel

        self.pwm_file = self.hwmon_path / f"pwm{pwm_channel}"
        self.pwm_enable_file = self.hwmon_path / f"pwm{pwm_channel}_enable"
        self.fan_input_file = self.hwmon_path / f"fan{pwm_channel}_input"

        self._validate_paths()

    def _validate_paths(self) -> None:
        """Validate that required sysfs files exist."""
        if not self.pwm_file.exists():
            raise FileNotFoundError(f"PWM file not found: {self.pwm_file}")
        if not self.pwm_enable_file.exists():
            raise FileNotFoundError(f"PWM enable file not found: {self.pwm_enable_file}")

    def set_manual_mode(self) -> bool:
        """
        Set PWM control to manual mode.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.pwm_enable_file.write_text("1")
            return True
        except (IOError, PermissionError) as e:
            logging.error(f"Failed to set manual PWM mode: {e}")
            return False

    def get_mode(self) -> Optional[int]:
        """Get current PWM control mode."""
        try:
            return int(self.pwm_enable_file.read_text().strip())
        except (IOError, ValueError) as e:
            logging.error(f"Failed to read PWM mode: {e}")
            return None

    def set_pwm(self, value: int) -> bool:
        """
        Set PWM value (0-255).

        Args:
            value: PWM value between 0 and 255

        Returns:
            True if successful, False otherwise
        """
        value = max(0, min(255, value))
        try:
            self.pwm_file.write_text(str(value))
            return True
        except (IOError, PermissionError) as e:
            logging.error(f"Failed to set PWM value: {e}")
            return False

    def get_pwm(self) -> Optional[int]:
        """Get current PWM value."""
        try:
            return int(self.pwm_file.read_text().strip())
        except (IOError, ValueError) as e:
            logging.error(f"Failed to read PWM value: {e}")
            return None

    def get_fan_rpm(self) -> Optional[int]:
        """Get current fan speed in RPM."""
        if not self.fan_input_file.exists():
            return None
        try:
            return int(self.fan_input_file.read_text().strip())
        except (IOError, ValueError) as e:
            logging.debug(f"Failed to read fan RPM: {e}")
            return None


class GPUMonitor:
    """Monitors GPU temperature and power via NVML."""

    def __init__(self, gpu_index: int = 0):
        """
        Initialize GPU monitor.

        Args:
            gpu_index: GPU index (0-based)
        """
        self.gpu_index = gpu_index
        self.handle = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize NVML and get GPU handle."""
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()

            if self.gpu_index >= device_count:
                logging.error(f"GPU index {self.gpu_index} invalid. Found {device_count} GPU(s).")
                return False

            self.handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_index)
            name = pynvml.nvmlDeviceGetName(self.handle)
            logging.info(f"Monitoring GPU {self.gpu_index}: {name}")
            self._initialized = True
            return True

        except pynvml.NVMLError as e:
            logging.error(f"Failed to initialize NVML: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown NVML."""
        if self._initialized:
            try:
                pynvml.nvmlShutdown()
                self._initialized = False
            except pynvml.NVMLError:
                pass

    def get_temperature(self) -> Optional[int]:
        """Get GPU temperature in Celsius."""
        if not self.handle:
            return None
        try:
            return pynvml.nvmlDeviceGetTemperature(
                self.handle, pynvml.NVML_TEMPERATURE_GPU
            )
        except pynvml.NVMLError as e:
            logging.error(f"Failed to read GPU temperature: {e}")
            return None

    def get_power(self) -> Optional[float]:
        """Get GPU power consumption in Watts."""
        if not self.handle:
            return None
        try:
            # NVML returns milliwatts
            return pynvml.nvmlDeviceGetPowerUsage(self.handle) / 1000.0
        except pynvml.NVMLError as e:
            logging.error(f"Failed to read GPU power: {e}")
            return None


class DataLogger:
    """Logs telemetry data to CSV file."""

    def __init__(self, log_file: Path):
        """
        Initialize data logger.

        Args:
            log_file: Path to CSV log file
        """
        self.log_file = log_file
        self._header_written = False

    def _ensure_header(self) -> None:
        """Write CSV header if file is new or empty."""
        if self._header_written:
            return

        write_header = not self.log_file.exists() or self.log_file.stat().st_size == 0

        if write_header:
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "gpu_temp", "fan_rpm", "pwm_value", "gpu_power"])

        self._header_written = True

    def log(self, gpu_temp: int, fan_rpm: Optional[int], pwm_value: int, gpu_power: float) -> None:
        """Log a data point."""
        self._ensure_header()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, gpu_temp, fan_rpm or "N/A", pwm_value, f"{gpu_power:.1f}"])


class Baram:
    """Main Baram cooling controller."""

    # Temperature thresholds and corresponding PWM ranges
    TEMP_THRESHOLDS = [30, 40, 50, 60, 70]
    PWM_RANGES = [(0, 0), (0, 30), (30, 60), (60, 90), (90, 120)]

    def __init__(self, config: Config):
        """
        Initialize Baram controller.

        Args:
            config: Configuration settings
        """
        self.config = config
        self.running = False
        self.spike_count = 0
        self.actual_min_pwm = config.min_pwm_value

        # Components (initialized in start())
        self.fan_controller: Optional[FanController] = None
        self.gpu_monitor: Optional[GPUMonitor] = None
        self.data_logger: Optional[DataLogger] = None

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "baram.log"

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        sig_name = signal.Signals(signum).name
        logging.info(f"Received {sig_name}, shutting down...")
        self.running = False

    def _detect_hwmon(self) -> Optional[Tuple[str, int]]:
        """Detect hwmon device for fan control."""
        if self.config.hwmon_device:
            # Use configured device
            hwmon_path = self.config.hwmon_device
            if not hwmon_path.startswith("/sys"):
                hwmon_path = f"/sys/class/hwmon/{hwmon_path}"
            return (hwmon_path, self.config.pwm_channel)

        # Auto-detect
        logging.info("Auto-detecting hwmon device...")
        result = HwmonDetector.auto_detect()

        if result:
            logging.info(f"Found hwmon device: {result[0]}, PWM channel: {result[1]}")
        else:
            logging.error("No suitable hwmon device found for fan control")

            # List available devices for debugging
            devices = HwmonDetector.find_pwm_devices()
            if devices:
                logging.info("Available hwmon devices with PWM:")
                for path, name, channels in devices:
                    logging.info(f"  {path} ({name}): PWM channels {channels}")

        return result

    def _calculate_pwm(self, gpu_temp: int) -> int:
        """
        Calculate target PWM value based on temperature.

        Args:
            gpu_temp: Current GPU temperature in Celsius

        Returns:
            Target PWM value (0-255)
        """
        if gpu_temp < self.config.min_temp:
            return self.actual_min_pwm

        # Extended thresholds including max_temp
        thresholds = self.TEMP_THRESHOLDS + [self.config.max_temp]
        pwm_ranges = self.PWM_RANGES + [(120, self.config.max_pwm_value)]

        # Find the appropriate range
        for i, threshold in enumerate(thresholds):
            if gpu_temp <= threshold:
                if i == 0:
                    # Below first threshold
                    return max(pwm_ranges[0][1], self.actual_min_pwm)

                # Linear interpolation between ranges
                prev_threshold = thresholds[i - 1]
                prev_pwm = pwm_ranges[i - 1][1]
                curr_pwm = pwm_ranges[i][1]

                # Calculate interpolated PWM
                temp_range = threshold - prev_threshold
                pwm_range = curr_pwm - prev_pwm
                temp_offset = gpu_temp - prev_threshold

                pwm_value = prev_pwm + (temp_offset * pwm_range // temp_range)
                return max(pwm_value, self.actual_min_pwm)

        # Above max threshold
        return max(self.config.max_pwm_value, self.actual_min_pwm)

    def _update_spike_tracking(self, gpu_power: float) -> None:
        """Update wattage spike tracking."""
        if gpu_power >= self.config.wattage_threshold:
            self.spike_count += 1
            if self.spike_count > self.config.wattage_spike_count:
                if self.actual_min_pwm != self.config.wattage_pwm_value:
                    self.actual_min_pwm = self.config.wattage_pwm_value
                    logging.debug(f"Wattage spike: raising min PWM to {self.actual_min_pwm}")
        else:
            if self.spike_count > 0:
                self.spike_count -= 1
                if self.spike_count == 0 and self.actual_min_pwm != self.config.min_pwm_value:
                    self.actual_min_pwm = self.config.min_pwm_value
                    logging.debug(f"Wattage normal: resetting min PWM to {self.actual_min_pwm}")

    def start(self) -> int:
        """
        Start the Baram controller.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        self._setup_logging()
        self._setup_signal_handlers()

        logging.info("Baram cooling controller starting...")
        logging.info(f"Configuration: min_temp={self.config.min_temp}, max_temp={self.config.max_temp}, "
                    f"min_pwm={self.config.min_pwm_value}, max_pwm={self.config.max_pwm_value}")

        # Detect hwmon device
        hwmon_result = self._detect_hwmon()
        if not hwmon_result:
            return 1

        hwmon_path, pwm_channel = hwmon_result

        # Initialize components
        try:
            self.fan_controller = FanController(hwmon_path, pwm_channel)
        except FileNotFoundError as e:
            logging.error(f"Fan controller initialization failed: {e}")
            return 1

        self.gpu_monitor = GPUMonitor(self.config.gpu_index)
        if not self.gpu_monitor.initialize():
            return 1

        # Set fan to manual control
        current_mode = self.fan_controller.get_mode()
        if current_mode != 1:
            if not self.fan_controller.set_manual_mode():
                logging.error("Failed to set fan to manual mode")
                return 1
            logging.info("Set fan control to manual mode")

        # Initialize data logger
        log_dir = Path(self.config.log_dir)
        self.data_logger = DataLogger(log_dir / "baram.csv")

        logging.info(f"Monitoring GPU {self.config.gpu_index}, controlling {hwmon_path}/pwm{pwm_channel}")

        # Main control loop
        self.running = True
        try:
            while self.running:
                self._control_loop_iteration()
                time.sleep(self.config.sleep_interval)
        except Exception as e:
            logging.error(f"Unexpected error in control loop: {e}")
            return 1
        finally:
            self._cleanup()

        logging.info("Baram shutdown complete")
        return 0

    def _control_loop_iteration(self) -> None:
        """Execute one iteration of the control loop."""
        # Read sensors
        gpu_temp = self.gpu_monitor.get_temperature()
        gpu_power = self.gpu_monitor.get_power()
        fan_rpm = self.fan_controller.get_fan_rpm()

        if gpu_temp is None or gpu_power is None:
            logging.warning("Failed to read GPU sensors, skipping iteration")
            return

        # Update spike tracking
        self._update_spike_tracking(gpu_power)

        # Calculate and set PWM
        pwm_value = self._calculate_pwm(gpu_temp)
        self.fan_controller.set_pwm(pwm_value)

        # Log data
        self.data_logger.log(gpu_temp, fan_rpm, pwm_value, gpu_power)

        logging.debug(f"Temp: {gpu_temp}°C, Power: {gpu_power:.1f}W, "
                     f"Fan: {fan_rpm or 'N/A'} RPM, PWM: {pwm_value}")

    def _cleanup(self) -> None:
        """Cleanup resources."""
        if self.gpu_monitor:
            self.gpu_monitor.shutdown()

        # Optionally restore automatic fan control
        if self.fan_controller:
            logging.info("Restoring automatic fan control...")
            try:
                Path(self.fan_controller.pwm_enable_file).write_text("2")
            except (IOError, PermissionError):
                logging.warning("Could not restore automatic fan control")


def load_config(config_file: str, args: argparse.Namespace) -> Config:
    """
    Load configuration from file and command line arguments.

    Command line arguments override config file settings.
    """
    config = Config()

    # Load from config file if it exists
    if os.path.exists(config_file):
        parser = configparser.ConfigParser()
        parser.read(config_file)

        if parser.has_section("Settings"):
            config.min_temp = parser.getint("Settings", "min_temp", fallback=config.min_temp)
            config.max_temp = parser.getint("Settings", "max_temp", fallback=config.max_temp)
            config.min_pwm_value = parser.getint("Settings", "min_pwm_value", fallback=config.min_pwm_value)
            config.max_pwm_value = parser.getint("Settings", "max_pwm_value", fallback=config.max_pwm_value)
            config.pwm_step = parser.getint("Settings", "pwm_step", fallback=config.pwm_step)
            config.temp_drop = parser.getint("Settings", "temp_drop", fallback=config.temp_drop)
            config.wattage_threshold = parser.getint("Settings", "wattage_threshold", fallback=config.wattage_threshold)
            config.wattage_pwm_value = parser.getint("Settings", "wattage_pwm_value", fallback=config.wattage_pwm_value)
            config.wattage_spike_count = parser.getint("Settings", "wattage_spike_count", fallback=config.wattage_spike_count)
            config.sleep_interval = parser.getint("Settings", "sleep_interval", fallback=config.sleep_interval)
            config.gpu_index = parser.getint("Settings", "gpu_index", fallback=config.gpu_index)
            config.hwmon_device = parser.get("Settings", "hwmon_device", fallback=config.hwmon_device)
            config.pwm_channel = parser.getint("Settings", "pwm_channel", fallback=config.pwm_channel)

    # Override with command line arguments
    if args.min_temp is not None:
        config.min_temp = args.min_temp
    if args.max_temp is not None:
        config.max_temp = args.max_temp
    if args.min_pwm_value is not None:
        config.min_pwm_value = args.min_pwm_value
    if args.max_pwm_value is not None:
        config.max_pwm_value = args.max_pwm_value
    if args.gpu_index is not None:
        config.gpu_index = args.gpu_index
    if args.hwmon_device:
        config.hwmon_device = args.hwmon_device
    if args.pwm_channel is not None:
        config.pwm_channel = args.pwm_channel

    config.config_file = config_file

    return config


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Baram - Advanced System Cooling Management Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--config", type=str, default="/etc/baram/baram.conf",
                       help="Path to configuration file")
    parser.add_argument("--min-temp", type=int, default=None,
                       help="Minimum temperature threshold (°C)")
    parser.add_argument("--max-temp", type=int, default=None,
                       help="Maximum temperature threshold (°C)")
    parser.add_argument("--min-pwm-value", type=int, default=None,
                       help="Minimum PWM value (0-255)")
    parser.add_argument("--max-pwm-value", type=int, default=None,
                       help="Maximum PWM value (0-255)")
    parser.add_argument("--gpu-index", type=int, default=None,
                       help="GPU index to monitor (0-based)")
    parser.add_argument("--hwmon-device", type=str, default="",
                       help="Hwmon device path or name (auto-detect if empty)")
    parser.add_argument("--pwm-channel", type=int, default=None,
                       help="PWM channel number (1-based)")
    parser.add_argument("--list-hwmon", action="store_true",
                       help="List available hwmon devices and exit")

    args = parser.parse_args()

    # List hwmon devices if requested
    if args.list_hwmon:
        print("Available hwmon devices with PWM control:")
        devices = HwmonDetector.find_pwm_devices()
        if not devices:
            print("  No devices found")
        else:
            for path, name, channels in devices:
                print(f"  {path}")
                print(f"    Name: {name}")
                print(f"    PWM channels: {channels}")
        return 0

    # Load configuration
    config = load_config(args.config, args)

    # Create and run controller
    controller = Baram(config)
    return controller.start()


if __name__ == "__main__":
    sys.exit(main())
