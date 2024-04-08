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
parser.add_argument('--min-temp', type=int, default=50, help='Minimum temperature threshold (default: 50)')
parser.add_argument('--max-temp', type=int, default=80, help='Maximum temperature threshold (default: 80)')
parser.add_argument('--max-fan-speed', type=int, default=12000, help='Maximum fan speed (default: 12000)')
parser.add_argument('--temp-drop', type=int, default=3, help='Temperature drop threshold for fan speed reduction (default: 3)')
args = parser.parse_args()

# Define thresholds for temperature
MIN_TEMP = args.min_temp
MAX_TEMP = args.max_temp

# Define maximum fan speed
MAX_FAN_SPEED = args.max_fan_speed

# Define temperature drop threshold for fan speed reduction
TEMP_DROP = args.temp_drop

# Define PWM values
MIN_PWM = 80
MAX_PWM = 255

# Define thresholds for temperature and corresponding PWM values
TEMP_THRESHOLDS = [50, 60, 70, 72, 76]
PWM_RANGES = [(80, 80), (80, 100), (100, 150), (150, 200), (200, MAX_PWM), (MAX_PWM, MAX_PWM)]

# PWM control file and fan speed file
# need doc string here giving a breif explaination of how to adjust this
PWM_FILE = "/sys/class/hwmon/hwmon2/pwm1" # Adjust based on your system
FAN_SPEED_FILE = "/sys/class/hwmon/hwmon2/fan1_input"  # Adjust based on your system
PWM_ENABLE_FILE = "/sys/class/hwmon/hwmon2/pwm1_enable" # Adjust based on your system

# Log file
LOG_FILE = "/var/log/gpu_temp.log"

# Variables for tracking temperature oscillation
oscillation_count = 0
oscillation_threshold = 3
oscillation_interval = 30
last_oscillation_time = None
high_temp_reached = False

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

def log_data(data):
    try:
        with open(LOG_FILE, "a") as file:
            writer = csv.writer(file)
            writer.writerow(data)
    except IOError as e:
        print(f"Failed to write to log file: {str(e)}")

# Check and set PWM control mode to manual (1)
try:
    with open(PWM_ENABLE_FILE, "r") as file:
        current_mode = int(file.read().strip())
except IOError as e:
    print(f"Failed to read PWM control mode: {str(e)}")
    current_mode = None

if current_mode != 1:
    set_pwm_control_mode(1)

# Write CSV header to log file
log_data(["date", "gpu_temp", "fan_speed", "pwm_value", "gpu_power"])

while True:
    gpu_temp = get_gpu_temp()
    gpu_power = get_gpu_power()
    fan_speed = get_fan_speed()

    if gpu_temp >= 76:
        high_temp_reached = True
        oscillation_count += 1
        current_time = time.time()
        if last_oscillation_time is None or current_time - last_oscillation_time >= oscillation_interval:
            last_oscillation_time = current_time
            oscillation_count = 1
        if oscillation_count >= oscillation_threshold:
            gpu_temp = 76
    elif high_temp_reached and gpu_temp <= 76 - TEMP_DROP:
        high_temp_reached = False
        oscillation_count = 0
    else:
        oscillation_count = 0

    pwm_value = MIN_PWM
    for i in range(len(TEMP_THRESHOLDS)):
        if i == 0:
            if gpu_temp <= TEMP_THRESHOLDS[i]:
                pwm_value = PWM_RANGES[i][0]
                break
        else:
            if TEMP_THRESHOLDS[i-1] < gpu_temp <= TEMP_THRESHOLDS[i]:
                pwm_value = PWM_RANGES[i][0] + (gpu_temp - TEMP_THRESHOLDS[i-1]) * (PWM_RANGES[i][1] - PWM_RANGES[i][0]) // (TEMP_THRESHOLDS[i] - TEMP_THRESHOLDS[i-1])
                break
    else:
        pwm_value = PWM_RANGES[-1][1]

    if fan_speed > MAX_FAN_SPEED:
        pwm_value = PWM_RANGES[-2][1]  # Set PWM value to the second-to-last range

    set_pwm_value(pwm_value)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    log_data([timestamp, gpu_temp, fan_speed, pwm_value, gpu_power])
    logging.debug(f"Timestamp: {timestamp}, GPU Temp: {gpu_temp}, Fan Speed: {fan_speed}, PWM Value: {pwm_value}, GPU Power: {gpu_power}")

    time.sleep(2)