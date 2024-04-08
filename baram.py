import subprocess
import time
import csv
import datetime
import argparse
import os
import sys
import logging

# Parse command line arguments
parser = argparse.ArgumentParser(description='Baram - Advanced System Cooling Management Tool')
parser.add_argument('--min-temp', type=int, default=20, help='Minimum temperature threshold (default: 20)')
parser.add_argument('--max-temp', type=int, default=80, help='Maximum temperature threshold (default: 80)')
parser.add_argument('--min-pwm-value', type=int, default=0, help='Minimum PWM Value for fan speed 0-255 value (default: 0)')
parser.add_argument('--max-pwm-value', type=int, default=255, help='Maximum PWM Value for fan speed 0-255 value (default: 255)')
parser.add_argument('--pwm-step', type=int, default=5, help='The PWM value step size for adjusting fan speed (default: 5)')
parser.add_argument('--temp-drop', type=int, default=3, help='Temperature drop threshold for fan speed reduction (default: 3)')
parser.add_argument('--log-file', type=str, default="/var/log/baram/debug.log", help='Path to the script log file (default: /var/log/baram/debug.log)')
parser.add_argument('--data-log-file', type=str, default="/var/log/baram/baram.out", help='Path to the data output log file (default: /var/log/baram/baram.out)')
parser.add_argument('--max-pwm-below-65', type=int, default=80, help='Max PWM value when temp is below 65C (default: 80)')
parser.add_argument('--wattage-threshold', type=int, default=240, help='Wattage threshold for triggering increased fan speed (default: 240)')
parser.add_argument('--wattage-interval', type=int, default=30, help='Time interval in seconds for monitoring wattage spikes (default: 30)')
parser.add_argument('--wattage-spike-count', type=int, default=3, help='Number of wattage spikes within the interval to trigger increased fan speed (default: 3)')
parser.add_argument('--wattage-pwm-value', type=int, default=125, help='PWM value to set when wattage spike conditions are met (default: 125)')

args = parser.parse_args()

# Setup logging
logging.basicConfig(filename=args.log_file, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def log_data(data):
    with open(args.data_log_file, "a") as file:
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
wattage_threshold = 240
spike_count = 0
spike_threshold = 3
spike_interval = 30
last_spike_time = None
increased_fan_speed_time = None

def set_pwm_control_mode(mode):
    try:
        with open(PWM_ENABLE_FILE, "w") as file:
            file.write(str(mode))
        print(f"PWM control mode set to {mode}")
    except IOError as e:
        print(f"Failed to set PWM control mode to {mode}: {str(e)}")

def get_gpu_temp():
    output = subprocess.check_output(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits", "--id=1"])
    return int(output.decode().strip())

def get_gpu_power():
    output = subprocess.check_output(["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits", "--id=1"])
    return float(output.decode().strip())

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
    gpu_temp = get_gpu_temp()
    gpu_power = get_gpu_power()
    fan_speed = get_fan_speed()

    # Check for wattage spikes
    if gpu_power >= args.wattage_threshold:
        current_time = time.time()
        if last_spike_time is None or current_time - last_spike_time >= args.wattage_interval:
            spike_count = 1
            last_spike_time = current_time
        else:
            spike_count += 1
            if spike_count >= args.wattage_spike_count:
                if pwm_value < args.wattage_pwm_value:
                    pwm_value = args.wattage_pwm_value
                    increased_fan_speed_time = current_time
                    spike_count = 0
    else:
        if increased_fan_speed_time is not None and current_time - increased_fan_speed_time >= args.wattage_interval:
            increased_fan_speed_time = None
        spike_count = 0

    if gpu_temp >= MAX_TEMP:
        high_temp_reached = True
        oscillation_count += 1
        current_time = time.time()
        if last_oscillation_time is None or current_time - last_oscillation_time >= oscillation_interval:
            last_oscillation_time = current_time
            oscillation_count = 1
        if oscillation_count >= oscillation_threshold:
            gpu_temp = MAX_TEMP
    elif high_temp_reached and gpu_temp <= MAX_TEMP - TEMP_DROP:
        high_temp_reached = False
        oscillation_count = 0
    else:
        oscillation_count = 0

    if increased_fan_speed_time is None:
        if gpu_temp < 65:
            pwm_value = min(args.max_pwm_below_65, MAX_PWM)
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

    current_pwm_value = get_current_pwm_value()
    pwm_value = adjust_pwm_value(current_pwm_value, pwm_value, args.pwm_step)

    set_pwm_value(pwm_value)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    log_data([timestamp, gpu_temp, fan_speed, pwm_value, gpu_power])
    logging.debug(f"Timestamp: {timestamp}, GPU Temp: {gpu_temp}, Fan Speed: {fan_speed}, PWM Value: {pwm_value}, GPU Power: {gpu_power}")

    time.sleep(2)