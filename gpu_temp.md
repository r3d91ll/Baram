**Hardware Requirements:**
- Asus Rog Strix B550-XE Gaming WiFi motherboard
- Nvidia P40 GPU
- 3D printed fan shroud for the P40 GPU (available on eBay: [https://www.ebay.com/itm/155965387407](https://www.ebay.com/itm/155965387407))
- 2x 15k Blower fans (available on Amazon: [https://www.amazon.com/gp/product/B09SB3Z6ND](https://www.amazon.com/gp/product/B09SB3Z6ND))

**Software Requirements:**
- Linux operating system
- Nvidia driver and nvidia-smi utility

**Setup Instructions:**

1. Install the Nvidia P40 GPU on the Asus Rog Strix B550-XE Gaming WiFi motherboard.

2. Attach the 3D printed fan shroud to the P40 GPU and mount the 2x 15k Blower fans.

3. Connect the fans to the appropriate fan headers on the motherboard.

4. Create a new script file called `gpu_temp.sh` with the following content:

   ```bash
   #!/bin/bash

   # Define thresholds for temperature
   MIN_TEMP=50
   MAX_TEMP=85

   # Define PWM values
   MIN_PWM=0
   MAX_PWM=255

   # PWM control file
   PWM_FILE="/sys/class/hwmon/hwmon2/pwm1"
   PWM_ENABLE_FILE="/sys/class/hwmon/hwmon2/pwm1_enable"

   # Log file
   LOG_FILE="/var/log/gpu_temp.log"

   # Function to set PWM control mode
   set_pwm_control_mode() {
       local mode=$1
       sudo echo $mode > $PWM_ENABLE_FILE
       if [ $? -ne 0 ]; then
           echo "$(date) - Failed to set PWM control mode to $mode" | sudo tee -a $LOG_FILE
       else
           echo "$(date) - PWM control mode set to $mode" | sudo tee -a $LOG_FILE
       fi
   }

   # Check and set PWM control mode to manual (1)
   current_mode=$(cat $PWM_ENABLE_FILE)
   if [ "$current_mode" != "1" ]; then
       set_pwm_control_mode 1
   fi

   while true; do
       # Get GPU temperature
       GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader --id=1)

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
       if [ $? -ne 0 ]; then
           echo "$(date) - Failed to write PWM value to $PWM_FILE" | sudo tee -a $LOG_FILE
       else
           echo "$(date) - PWM value set to $PWM_VALUE" | sudo tee -a $LOG_FILE
       fi

       # Wait for a short interval before the next iteration
       sleep 5
   done
   ```

5. Make the script executable:

   ```bash
   chmod +x gpu_temp.sh
   ```

6. Create a new systemd service file called `gpu_temp.service` with the following content:

   ```
   [Unit]
   Description=GPU Temperature Based Fan Control Service

   [Service]
   ExecStart=/path/to/gpu_temp.sh
   Restart=always
   User=root

   [Install]
   WantedBy=multi-user.target
   ```

   Replace `/path/to/gpu_temp.sh` with the actual path to the `gpu_temp.sh` script.

7. Reload the systemd daemon and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start gpu_temp.service
   ```

8. Check the service status to ensure it is running correctly:

   ```bash
   systemctl status gpu_temp.service
   ```

**Troubleshooting:**

- If the fan speed is not changing, make sure that the `pwm1_enable` file is set to "1" (manual PWM control mode). You can check the value by running:

  ```bash
  cat /sys/class/hwmon/hwmon2/pwm1_enable
  ```

  If the value is not "1", you can set it manually by running:

  ```bash
  sudo echo 1 > /sys/class/hwmon/hwmon2/pwm1_enable
  ```

- Check the log file `/var/log/gpu_temp.log` for any error messages or indications of issues with the script or PWM control.

- Ensure that the script has the necessary permissions to write to the PWM control file and log file.

- Verify that the Nvidia driver and nvidia-smi utility are properly installed and functioning.

- If the issue persists, you may need to review the BIOS settings related to fan control and ensure that manual PWM control is enabled.

With these instructions and troubleshooting steps, you should be able to set up the fan control script for the Nvidia P40 GPU on your Asus Rog Strix B550-XE Gaming WiFi motherboard.
