import pandas as pd
import matplotlib.pyplot as plt
import time
import os
from io import StringIO

# Enable interactive mode for real-time graph updates
plt.ion()

# Initialize the figure for plotting
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# Path to the data file and config file
data_file = '/var/log/baram/baram.out'
config_path = '/etc/baram/baram.conf'

# Function to read the sleep interval from the configuration file
def read_sleep_interval(config_path):
    with open(config_path, 'r') as file:
        for line in file:
            if line.startswith('sleep_interval'):
                _, value = line.split('=')
                return float(value.strip())
    return 2  # Default value if not found

# Function to read new data from the log file
def read_new_data(filepath, last_pos):
    with open(filepath, 'r') as file:
        # Move to the last read position
        file.seek(last_pos)
        # Read new data
        new_data = file.read()
        # Update the last read position
        last_pos = file.tell()
    # Return the new data and the updated position
    return new_data, last_pos

# Read the sleep interval from the configuration file
sleep_interval = read_sleep_interval(config_path)

# Initialize the last read position
last_pos = 0

# Set the y-axis limits and ticks for temperature and wattage
temp_lim = (25, 100)
temp_ticks = range(25, 101, 5)
wattage_lim = (10, 300)
wattage_ticks = range(10, 301, 20)

# Loop to update the graph with new data
while True:
    # Read new data
    new_data, last_pos = read_new_data(data_file, last_pos)

    # Check if there is new data
    if new_data:
        # Convert the new data to a DataFrame
        new_df = pd.read_csv(StringIO(new_data), header=None, names=['date', 'gpu_temp', 'fan_speed', 'pwm_value', 'gpu_power'])
        new_df['date'] = pd.to_datetime(new_df['date'], format='%Y-%m-%d-%H:%M:%S', errors='coerce')
        new_df.dropna(subset=['date'], inplace=True)

        # Update the GPU temperature plot
        ax1.clear()
        ax1.plot(new_df['date'], new_df['gpu_temp'], label='GPU Temperature')
        ax1.legend(loc="upper left")
        ax1.set_ylabel('Temperature (°C)')
        ax1.set_ylim(temp_lim)
        ax1.set_yticks(temp_ticks)

        # Update the GPU power plot
        ax2.clear()
        ax2.plot(new_df['date'], new_df['gpu_power'], label='GPU Power')
        ax2.legend(loc="upper left")
        ax2.set_ylabel('Power (W)')
        ax2.set_ylim(wattage_lim)
        ax2.set_yticks(wattage_ticks)

        # Set the x-axis label
        ax2.set_xlabel('Time')

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)

        # Redraw the figure to update the graph
        plt.tight_layout()
        plt.draw()
        plt.pause(0.1)  # Brief pause to allow the figure to update

    # Sleep for the interval specified in the configuration file
    time.sleep(sleep_interval)