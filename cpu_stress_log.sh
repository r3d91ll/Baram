#!/bin/bash

# Log files
CPU_LOG_FILE="/var/log/cpu_stress.log"
GPU_LOG_FILE="/var/log/gpu_temp.log"

# Stress test duration in seconds (10 minutes)
DURATION=600

# Capture the start timestamp
START_TIME=$(date +%Y-%m-%d-%H:%M:%S)

# Initialize log files with headers and start markers
echo "CPU_GPU_Testing_Start - $START_TIME" | sudo tee -a $CPU_LOG_FILE $GPU_LOG_FILE
echo "date,cpu_temp,fan_speed,pwm_value,watt" | sudo tee -a $CPU_LOG_FILE
echo "date,gpu_temp,fan_speed,pwm_value,watt" | sudo tee -a $GPU_LOG_FILE

# Start GPU burn test in Docker for 10 minutes and capture its PID
docker run --rm --gpus all gpu_burn &
GPU_BURN_PID=$!

# Start the stress-ng test for 10 minutes
stress-ng --cpu 24 --io 4 --vm 2 --vm-bytes 12G --timeout ${DURATION}s &
STRESS_PID=$!

# Read initial energy value for power calculation
initial_energy=$(cat /sys/class/powercap/intel-rapl:0/energy_uj)
prev_energy=$initial_energy

# Monitor and log while either stress-ng or gpu_burn is running
while [ $(ps -p $STRESS_PID -o comm=) ] || [ $(ps -p $GPU_BURN_PID -o comm=) ]; do
    DATE=$(date +%Y-%m-%d-%H:%M:%S)
    CPU_TEMP=$(sensors | grep 'Tctl:' | awk '{print $2}' | tr -d '+°C')
    CPU_FAN_SPEED=$(cat /sys/class/hwmon/hwmon2/fan2_input) # Ensure hwmonX and fanY are correctly identified
    PWM_VALUE=$(cat /sys/class/hwmon/hwmon2/pwm2) # Ensure hwmonX and pwmY are correctly identified

    # Calculate power usage in watts
    current_energy=$(cat /sys/class/powercap/intel-rapl:0/energy_uj)
    energy_diff=$((current_energy - prev_energy))
    power_usage_watts=$(echo "scale=2; $energy_diff / 1000000" | bc)
    prev_energy=$current_energy

    # Log CPU metrics with power usage
    echo "$DATE,$CPU_TEMP,$CPU_FAN_SPEED,$PWM_VALUE,$power_usage_watts" | sudo tee -a $CPU_LOG_FILE

    sleep 2 # Adjust sleep as necessary
done

# Capture the end timestamp
END_TIME=$(date +%Y-%m-%d-%H:%M:%S)

# Log the end of the test with the captured timestamp
echo "CPU_GPU_Testing_Stop - $END_TIME" | sudo tee -a $CPU_LOG_FILE $GPU_LOG_FILE
