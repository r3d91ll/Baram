import subprocess
import time
import csv
import datetime

# Define thresholds for temperature
MIN_TEMP = 50
MAX_TEMP = 80

# Define PWM values
MIN_PWM = 80
MAX_PWM = 255

# Define thresholds for temperature and corresponding PWM values
TEMP_THRESHOLDS = [50, 60, 70, 75, 80]
PWM_RANGES = [(80, 80), (80, 100), (100, 150), (150, 200), (200, 255), (255, 255)]

# PWM control file and fan speed file
PWM_FILE = "/sys/class/hwmon/hwmon2/pwm1"
FAN_SPEED_FILE = "/sys/class/hwmon/hwmon2/fan1_input"  # Adjust based on your system
PWM_ENABLE_FILE = "/sys/class/hwmon/hwmon2/pwm1_enable"

# Log file
LOG_FILE = "/var/log/gpu_temp.log"

# Variables for tracking extended high power consumption
HIGH_POWER_THRESHOLD = 200
HIGH_POWER_DURATION = 300  # 5 minutes in seconds
high_power_start_time = None

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

    if gpu_power >= HIGH_POWER_THRESHOLD:
        if high_power_start_time is None:
            high_power_start_time = time.time()
    else:
        high_power_start_time = None

    if high_power_start_time is not None and time.time() - high_power_start_time >= HIGH_POWER_DURATION:
        # Maintain 8000 RPM until temperature drops below 50°C
        if gpu_temp > MIN_TEMP:
            pwm_value = PWM_RANGES[-2][0]  # Use the PWM value corresponding to 8000 RPM
        else:
            high_power_start_time = None
    else:
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

    set_pwm_value(pwm_value)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    log_data([timestamp, gpu_temp, fan_speed, pwm_value, gpu_power])

    time.sleep(2)