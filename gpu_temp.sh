#!/bin/bash

# Define thresholds for temperature
MIN_TEMP=50
MAX_TEMP=85

# Define PWM values
MIN_PWM=0
MAX_PWM=255

# PWM control file and fan speed file
PWM_FILE="/sys/class/hwmon/hwmon2/pwm1"
FAN_SPEED_FILE="/sys/class/hwmon/hwmon2/fan1_input" # Adjust based on your system
PWM_ENABLE_FILE="/sys/class/hwmon/hwmon2/pwm1_enable"
GPU_POWER=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits --id=1)

# Log file
LOG_FILE="/var/log/gpu_temp.log"

# Write CSV header to log file
echo "date,cpu_temp,fan_speed,pwm_value,gpu_power" | sudo tee -a $LOG_FILE

# Function to set PWM control mode
set_pwm_control_mode() {
    local mode=$1
    echo $mode | sudo tee $PWM_ENABLE_FILE > /dev/null
    if [ $? -ne 0 ]; then
        echo "$(date +%Y-%m-%d-%H:%M:%S),NA,NA,NA - Failed to set PWM control mode to $mode" | sudo tee -a $LOG_FILE
    else
        echo "$(date +%Y-%m-%d-%H:%M:%S),NA,NA,NA - PWM control mode set to $mode" | sudo tee -a $LOG_FILE
    fi
}

# Check and set PWM control mode to manual (1)
current_mode=$(cat $PWM_ENABLE_FILE)
if [ "$current_mode" != "1" ]; then
    set_pwm_control_mode 1
fi

while true; do
    # Refresh GPU temperature
    GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits --id=1)
    
    # Refresh GPU power draw
    GPU_POWER=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits --id=1)
    
    # Read current fan speed in RPM
    FAN_SPEED=$(cat $FAN_SPEED_FILE)

    # Calculate PWM value based on GPU_TEMP
    if [ "$GPU_TEMP" -le "$MIN_TEMP" ]; then
        PWM_VALUE=$MIN_PWM
    elif [ "$GPU_TEMP" -ge "$MAX_TEMP" ]; then
        PWM_VALUE=$MAX_PWM
    else
        # Scale PWM value within the temperature range
        RANGE=$(($MAX_TEMP - $MIN_TEMP))
        DELTA=$(($GPU_TEMP - $MIN_TEMP))
        PWM_VALUE=$(($MIN_PWM + ($DELTA * ($MAX_PWM - $MIN_PWM) / $RANGE)))
    fi

    # Write the calculated PWM value to the fan control
    echo $PWM_VALUE | sudo tee $PWM_FILE > /dev/null

    # Log the date, GPU temp, fan speed, PWM value, and GPU power in CSV format
    echo "$(date +%Y-%m-%d-%H:%M:%S),$GPU_TEMP,$FAN_SPEED,$PWM_VALUE,$GPU_POWER" | sudo tee -a $LOG_FILE

    # Wait for a short interval before the next iteration
    sleep 2
done

