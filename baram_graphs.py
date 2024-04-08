import pandas as pd
import matplotlib.pyplot as plt

# Read the test data from the CSV file
data = pd.read_csv('testdata')

# Convert the 'date' column to datetime format
data['date'] = pd.to_datetime(data['date'])

# Create a figure and axis
fig, ax = plt.subplots(figsize=(12, 8))

# Plot GPU temperature
ax.plot(data['date'], data['cpu_temp'], label='GPU Temperature (°C)', color='red')

# Plot fan speed
ax.plot(data['date'], data['fan_speed'], label='Fan Speed (RPM)', color='blue')

# Plot GPU power
ax.plot(data['date'], data['gpu_power'], label='GPU Power (W)', color='green')

# Set labels and title
ax.set_xlabel('Time')
ax.set_ylabel('Value')
ax.set_title('GPU Temperature, Fan Speed, and Power')

# Add a legend
ax.legend()

# Rotate x-axis labels for better readability
plt.xticks(rotation=45)

# Adjust layout and display the graph
plt.tight_layout()
plt.show()