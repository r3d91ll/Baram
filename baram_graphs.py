import pandas as pd
import matplotlib.pyplot as plt

# Read the test data from the CSV file
data = pd.read_csv('testdata.txt')

# Convert the 'date' column to datetime format
data['date'] = pd.to_datetime(data['date'])

# Create a figure with two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# Plot GPU temperature and power
ax1.plot(data['date'].to_numpy(), data['gpu_temp'].to_numpy(), label='GPU Temperature (°C)', color='red')
ax1.set_ylabel('Temperature (°C)', color='red')
ax1.tick_params(axis='y', labelcolor='red')

ax1_twin = ax1.twinx()
ax1_twin.plot(data['date'].to_numpy(), data['gpu_power'].to_numpy(), label='GPU Power (W)', color='green')
ax1_twin.set_ylabel('Power (W)', color='green')
ax1_twin.tick_params(axis='y', labelcolor='green')

# Plot fan speed and PWM values
ax2.plot(data['date'].to_numpy(), data['fan_speed'].to_numpy(), label='Fan Speed (RPM)', color='blue')
ax2.set_ylabel('Fan Speed (RPM)', color='blue')
ax2.tick_params(axis='y', labelcolor='blue')

ax2_twin = ax2.twinx()
ax2_twin.plot(data['date'].to_numpy(), data['pwm_value'].to_numpy(), label='PWM Value', color='purple')
ax2_twin.set_ylabel('PWM Value', color='purple')
ax2_twin.tick_params(axis='y', labelcolor='purple')

# Set labels and title
ax1.set_title('GPU Temperature and Power')
ax2.set_title('Fan Speed and PWM Value')
ax2.set_xlabel('Time')

# Add legends
ax1.legend(loc='upper left')
ax1_twin.legend(loc='upper right')
ax2.legend(loc='upper left')
ax2_twin.legend(loc='upper right')

# Rotate x-axis labels for better readability
plt.xticks(rotation=45)

# Adjust layout and display the graph
plt.tight_layout()
plt.show()