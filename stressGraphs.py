import pandas as pd
import matplotlib.pyplot as plt

# Read the CPU and GPU data from the CSV files
cpu_data = pd.read_csv('/home/todd/git/r3d91lls_repo/CPULogs-FP-Off.csv')
gpu_data = pd.read_csv('/home/todd/git/r3d91lls_repo/GPULogs-FP-Off.csv')

# Convert the 'date' column to datetime format for both datasets
cpu_data['date'] = pd.to_datetime(cpu_data['date'])
gpu_data['date'] = pd.to_datetime(gpu_data['date'])

# Create a figure with subplots for CPU graphs
fig_cpu, axs_cpu = plt.subplots(3, 1, figsize=(10, 12))

# CPU Temperature Graph
axs_cpu[0].plot(cpu_data['date'], cpu_data['cpu_temp'])
axs_cpu[0].set_xlabel('Time')
axs_cpu[0].set_ylabel('Temperature (°C)')
axs_cpu[0].set_title('CPU Temperature')

# CPU Watts Graph
axs_cpu[1].plot(cpu_data['date'], cpu_data['watt'])
axs_cpu[1].set_xlabel('Time')
axs_cpu[1].set_ylabel('Watts')
axs_cpu[1].set_title('CPU Watts')

# CPU Fan Speed and PWM Value Graph
axs_cpu[2].plot(cpu_data['date'], cpu_data['fan_speed'], label='Fan Speed')
axs_cpu[2].plot(cpu_data['date'], cpu_data['pwm_value'], label='PWM Value')
axs_cpu[2].set_xlabel('Time')
axs_cpu[2].set_ylabel('Value')
axs_cpu[2].set_title('CPU Fan Speed and PWM Value')
axs_cpu[2].legend()

# Create a figure with subplots for GPU graphs
fig_gpu, axs_gpu = plt.subplots(3, 1, figsize=(10, 12))

# GPU Temperature Graph
axs_gpu[0].plot(gpu_data['date'], gpu_data['gpu_temp'])
axs_gpu[0].set_xlabel('Time')
axs_gpu[0].set_ylabel('Temperature (°C)')
axs_gpu[0].set_title('GPU Temperature')

# GPU Watts Graph
axs_gpu[1].plot(gpu_data['date'], gpu_data['watt'])
axs_gpu[1].set_xlabel('Time')
axs_gpu[1].set_ylabel('Watts')
axs_gpu[1].set_title('GPU Watts')

# GPU Fan Speed and PWM Value Graph
axs_gpu[2].plot(gpu_data['date'], gpu_data['fan_speed'], label='Fan Speed')
axs_gpu[2].plot(gpu_data['date'], gpu_data['pwm_value'], label='PWM Value')
axs_gpu[2].set_xlabel('Time')
axs_gpu[2].set_ylabel('Value')
axs_gpu[2].set_title('GPU Fan Speed and PWM Value')
axs_gpu[2].legend()

# Create a figure for the combined CPU and GPU graph
fig_combined, ax_combined = plt.subplots(figsize=(10, 6))

# Combined CPU and GPU Graph
ax_combined.plot(cpu_data['date'], cpu_data['cpu_temp'], label='CPU Temperature')
ax_combined.plot(cpu_data['date'], cpu_data['watt'], label='CPU Watts')
ax_combined.plot(cpu_data['date'], cpu_data['fan_speed'], label='CPU Fan Speed')
ax_combined.plot(gpu_data['date'], gpu_data['gpu_temp'], label='GPU Temperature')
ax_combined.plot(gpu_data['date'], gpu_data['watt'], label='GPU Watts')
ax_combined.plot(gpu_data['date'], gpu_data['fan_speed'], label='GPU Fan Speed')
ax_combined.set_xlabel('Time')
ax_combined.set_ylabel('Value')
ax_combined.set_title('Combined CPU and GPU Graph')
ax_combined.legend()

plt.tight_layout()
plt.show()