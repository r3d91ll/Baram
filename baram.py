import subprocess
import time
import csv
import datetime

# Define thresholds for temperature
MIN_TEMP = 50
MAX_TEMP = 85

# Define PWM values
MIN_PWM = 0
MAX_PWM = 255

# PWM control file and fan speed file
PWM_FILE = "/sys/class/hwmon/hwmon2/pwm1"
FAN_SPEED_FILE = "/sys/class/hwmon/hwmon2/fan1_input"  # Adjust based on your system
PWM_ENABLE_FILE = "/sys/class/hwmon/hwmon2/pwm1_enable"

# Log file
LOG_FILE = "/var/log/gpu_temp.log"

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
log_data(["date", "cpu_temp", "fan_speed", "pwm_value", "gpu_power"])

while True:
    gpu_temp = get_gpu_temp()
    gpu_power = get_gpu_power()
    fan_speed = get_fan_speed()

    if gpu_temp <= MIN_TEMP:
        pwm_value = MIN_PWM
    elif gpu_temp >= MAX_TEMP:
        pwm_value = MAX_PWM
    else:
        pwm_value = MIN_PWM + (gpu_temp - MIN_TEMP) * (MAX_PWM - MIN_PWM) // (MAX_TEMP - MIN_TEMP)

    set_pwm_value(pwm_value)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    log_data([timestamp, gpu_temp, fan_speed, pwm_value, gpu_power])

    time.sleep(2)