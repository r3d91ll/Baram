import subprocess
import time
import csv
import datetime
import argparse
import os
import sys
import logging
import configparser
from pynvml import *  # Added for configuration file handling

# Parse command line arguments
parser = argparse.ArgumentParser(description='Baram - Advanced System Cooling Management Tool')
parser.add_argument('--min-temp', type=int, default=20, help='Minimum temperature threshold (default: 20)')
parser.add_argument('--max-temp', type=int, default=80, help='Maximum temperature threshold (default: 80)')
parser.add_argument('--min-pwm-value', type=int, default=0, help='Minimum PWM Value for fan speed 0-255 value (default: 0)')
parser.add_argument('--max-pwm-value', type=int, default=255, help='Maximum PWM Value for fan speed 0-255 value (default: 255)')
parser.add_argument('--pwm-step', type=int, default=5, help='The PWM value step size for adjusting fan speed (default: 5)')
parser.add_argument('--temp-drop', type=int, default=3, help='Temperature drop threshold for fan speed reduction (default: 3)')
parser.add_argument('--config', type=str, default='/etc/baram/baram.conf', help='Path to configuration file')  # Added for config file
parser.add_argument('--max-pwm-below-65', type=int, default=80, help='Max PWM value when temp is below 65C (default: 80)')
parser.add_argument('--wattage-threshold', type=int, default=240, help='Wattage threshold for triggering increased fan speed (default: 240)')
parser.add_argument('--wattage-interval', type=int, default=30, help='Time interval in seconds for monitoring wattage spikes (default: 30)')
parser.add_argument('--wattage-spike-count', type=int, default=3, help='Number of wattage spikes within the interval to trigger increased fan speed (default: 3)')
parser.add_argument('--wattage-pwm-value', type=int, default=125, help='PWM value to set when wattage spike conditions are met (default: 125)')
parser.add_argument('--wattage-spike-duration', type=int, default=6, help='Duration in seconds for a wattage spike to trigger increased fan speed (default: 6)')
args.wattage_threshold = config.getint('Settings', 'wattage_threshold', fallback=args.wattage_threshold)
args.spike_threshold = config.getint('Settings', 'spike_threshold', fallback=3)
args.spike_interval = config.getint('Settings', 'spike_interval', fallback=3)
args = parser.parse_args()

# Setup logging
logging.basicConfig(filename="/var/log/baram/baram.log", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
data_log_file = "/var/log/baram/baram.out"

# Read configuration file
# Read configuration file
config = configparser.ConfigParser()
config.read(args.config)
# Update arguments from configuration file
args.min_temp = config.getint('Settings', 'min_temp', fallback=args.min_temp)
args.max_temp = config.getint('Settings', 'max_temp', fallback=args.max_temp)
args.min_pwm_value = config.getint('Settings', 'min_pwm_value', fallback=args.min_pwm_value)
args.max_pwm_value = config.getint('Settings', 'max_pwm_value', fallback=args.max_pwm_value)
args.wattage_spike_duration = config.getint('Settings', 'wattage_spike_duration', fallback=args.wattage_spike_duration)
args.sleep_interval = config.getint('Settings', 'sleep_interval', fallback=2)

def log_data(data):
    with open(data_log_file, "a") as file:
        writer = csv.writer(file)
        writer.writerow(data)

MIN_TEMP = args.min_temp
MAX_TEMP = args.max_temp
MIN_PWM = args.min_pwm_value
MAX_PWM = args.max_pwm_value
TEMP_DROP = args.temp_drop  # Add this line to define TEMP_DROP

# Define temperature and corresponding PWM values with corrected list syntax
TEMP_THRESHOLDS = [30, 40, 50, 60, 70, MAX_TEMP]
PWM_RANGES = [(0, 0), (0, 30), (30, 60), (60, 90), (90, 120), (120, MAX_PWM)]

# PWM control file and fan speed file
PWM_FILE = "/sys/class/hwmon/hwmon2/pwm1"  # Adjust based on your system
FAN_SPEED_FILE = "/sys/class/hwmon/hwmon2/fan1_input"  # Adjust based on your system
PWM_ENABLE_FILE = "/sys/class/hwmon/hwmon2/pwm1_enable"  # Adjust based on your system

# Variables for tracking temperature oscillation
oscillation_count = 0
oscillation_threshold = 3
oscillation_interval = 30
last_oscillation_time = None
high_temp_reached = False


# Variables for tracking wattage spikes
wattage_spike_start_time = None
wattage_spike_detected = False
wattage_spike_min_pwm = args.min_pwm_value
spike_count = 0
last_spike_time = None
increased_fan_speed_time = None

def set_pwm_control_mode(mode):
    try:
        with open(PWM_ENABLE_FILE, "w") as file:
            file.write(str(mode))
        print(f"PWM control mode set to {mode}")
    except IOError as e:
        print(f"Failed to set PWM control mode to {mode}: {str(e)}")

def get_gpu_temp(handle):
    temperature = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
    return temperature

def get_gpu_power(handle):
    power = nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert milliwatts to watts
    return power

def get_fan_speed():
    try:
        with open(FAN_SPEED_FILE, "r") as file:
            return int(file.read().strip())
    except IOError as e:
        print(f"Failed to read fan speed: {str(e)}")
        return None

def set_pwm_value(value):
    try:
        with open(PWM_FILE, "w") as file:
            file.write(str(value))
    except IOError as e:
        print(f"Failed to write PWM value: {str(e)}")

def get_current_pwm_value():
    try:
        with open(PWM_FILE, "r") as file:
            return int(file.read().strip())
    except IOError as e:
        print(f"Failed to read current PWM value: {str(e)}")
        return None

def adjust_pwm_value(current_value, target_value, step):
    if current_value < target_value:
        return min(current_value + step, target_value)
    elif current_value > target_value:
        return max(current_value - step, target_value)
    return current_value

# Initialize NVML
nvmlInit()

# Get GPU handle
gpu_index = 1  
handle = nvmlDeviceGetHandleByIndex(gpu_index)

# Check and set PWM control mode to manual (1)
try:
    with open(PWM_ENABLE_FILE, "r") as file:
        current_mode = int(file.read().strip())
except IOError as e:
    logging.error(f"Failed to read PWM control mode: {str(e)}")

if current_mode != 1:
    set_pwm_control_mode(1)

# Write CSV header to log file
log_data(["date", "gpu_temp", "fan_speed", "pwm_value", "gpu_power"])

while True:
    gpu_temp = get_gpu_temp(handle)
    gpu_power = get_gpu_power(handle)
    fan_speed = get_fan_speed()

    # Fan speed adjustment logic
    if gpu_temp < args.min_temp:
        pwm_value = args.min_pwm_value  # Set PWM to args.min_pwm_value if below min-temp
    else:
        # Existing logic for adjusting PWM based on temperature
        if gpu_temp < 65:
            pwm_value = min(args.max_pwm_below_65, args.max_pwm_value)
        else:
            for i in range(len(TEMP_THRESHOLDS)):
                if gpu_temp <= TEMP_THRESHOLDS[i]:
                    if i == 0:
                        pwm_value = PWM_RANGES[i][0]
                    else:
                        pwm_value = PWM_RANGES[i-1][1] + (gpu_temp - TEMP_THRESHOLDS[i-1]) * (PWM_RANGES[i][1] - PWM_RANGES[i-1][1]) // (TEMP_THRESHOLDS[i] - TEMP_THRESHOLDS[i-1])
                    break
            else:
                pwm_value = PWM_RANGES[-1][1]

    current_time = time.time()

    if gpu_power >= args.wattage_threshold:
        if last_spike_time is None or (current_time - last_spike_time) >= args.sleep_interval:
            spike_count = 1
            last_spike_time = current_time
        else:
            spike_count += 1
            if spike_count >= args.spike_threshold:
                wattage_spike_detected = True
                wattage_spike_min_pwm = config.getint('Settings', 'wattage_pwm_value', fallback=75)
                spike_count = 0
    else:
        last_spike_time = None
        spike_count = 0
        wattage_spike_detected = False

    # If a wattage spike is detected, set the PWM value to the configured value
    if wattage_spike_detected:
        pwm_value = config.getint('Settings', 'wattage_pwm_value', fallback=75)
        logging.debug(f"Wattage spike detected for {args.wattage_spike_duration} seconds. Setting PWM value to {pwm_value}.")
    else:
        # If a wattage spike has not adjusted the PWM value, proceed with temperature-based adjustments
        if gpu_temp < args.min_temp:
            pwm_value = args.min_pwm_value  # Set PWM to 0 if below min-temp
        else:
            if gpu_temp < 65:
                pwm_value = min(args.max_pwm_below_65, args.max_pwm_value)
            else:
                for i in range(len(TEMP_THRESHOLDS)):
                    if gpu_temp <= TEMP_THRESHOLDS[i]:
                        if i == 0:
                            pwm_value = PWM_RANGES[i][0]
                        else:
                            pwm_value = PWM_RANGES[i-1][1] + (gpu_temp - TEMP_THRESHOLDS[i-1]) * (PWM_RANGES[i][1] - PWM_RANGES[i-1][1]) // (TEMP_THRESHOLDS[i] - TEMP_THRESHOLDS[i-1])
                        break
                else:
                    pwm_value = PWM_RANGES[-1][1]

            # If a wattage spike has not adjusted the PWM value, proceed with temperature-based adjustments
            if pwm_value != args.wattage_pwm_value:
                # Fan speed adjustment logic based on temperature
                if gpu_temp < args.min_temp:
                    pwm_value = args.min_pwm_value  # Set PWM to 0 if below min-temp
                else:
                    if gpu_temp < 65:
                        pwm_value = min(args.max_pwm_below_65, args.max_pwm_value)
                    else:
                        for i in range(len(TEMP_THRESHOLDS)):
                            if gpu_temp <= TEMP_THRESHOLDS[i]:
                                if i == 0:
                                    pwm_value = PWM_RANGES[i][0]
                                else:
                                    pwm_value = PWM_RANGES[i-1][1] + (gpu_temp - TEMP_THRESHOLDS[i-1]) * (PWM_RANGES[i][1] - PWM_RANGES[i-1][1]) // (TEMP_THRESHOLDS[i] - TEMP_THRESHOLDS[i-1])
                                break
                        else:
                            pwm_value = PWM_RANGES[-1][1]

# Set the new PWM value
    current_pwm_value = get_current_pwm_value()
    if current_pwm_value is not None:
        pwm_value = adjust_pwm_value(current_pwm_value, pwm_value, args.pwm_step)
        set_pwm_value(pwm_value)

        # Logging the data
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        log_data([timestamp, gpu_temp, fan_speed, pwm_value, gpu_power])
        logging.debug(f"Timestamp: {timestamp}, GPU Temp: {gpu_temp}, Fan Speed: {fan_speed}, PWM Value: {pwm_value}, GPU Power: {gpu_power}")

        time.sleep(args.sleep_interval)

# Shutdown NVML
nvmlShutdown()