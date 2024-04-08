#!/bin/bash

# Log file
POWER_LOG_FILE="/var/log/power_usage.log"

# Duration for powerstat monitoring in seconds
DURATION=600

# Define a temporary file to capture powerstat's output
TEMP_FILE="/tmp/powerstat_output.tmp"

# Ensure the temporary file is cleaned up on script exit
trap "rm -f $TEMP_FILE" EXIT

# Start logging header for CSV
echo "date,power_usage" | sudo tee $POWER_LOG_FILE

# Run powerstat in the background to monitor power usage
# -R for raw data, 1 for 1 second interval
powerstat -R 1 $DURATION > $TEMP_FILE &

# Capture the PID of powerstat for later monitoring
POWERSTAT_PID=$!

# Monitor and log power usage
while sleep 5; do
    if ps -p $POWERSTAT_PID > /dev/null; then
        # Get the latest power usage value (Watts) from the last line of output
        POWER_USAGE=$(tail -n 1 $TEMP_FILE | awk '{print $NF}')
        
        # Validate and log only if it's a numerical value
        if [[ $POWER_USAGE =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            DATE=$(date +%Y-%m-%d-%H:%M:%S)
            echo "$DATE,$POWER_USAGE" | sudo tee -a $POWER_LOG_FILE
        fi
    else
        # Exit the loop if powerstat is no longer running
        break
    fi
done

sudo powerstat -R 1 $DURATION | awk '
{
    if ($NF > 1) {
        watts=$NF; 
        if (watts ~ /^[0-9]+(\.[0-9]+)?$/) { # Check if watts is a number
            printf "%s,%s\n", strftime("%Y-%m-%d-%H:%M:%S", systime()), watts;
        }
    }
}' | sudo tee -a $POWER_LOG_FILE