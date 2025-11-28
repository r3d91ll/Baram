# Baram: Advanced System Cooling Management Tool

A Linux utility designed to manage fans on datacenter GPUs (like Tesla P40) mounted in ATX cases. Named after the Korean word for wind (바람), Baram provides intelligent, adaptive fan control based on GPU temperature and power consumption.

## Overview

Baram is a specialized cooling management tool developed for NVIDIA datacenter GPUs repurposed in consumer ATX cases. It monitors GPU temperature and power via NVML and controls motherboard fan headers via the Linux hwmon interface.

### Key Features

- **Automatic hwmon Detection**: Automatically finds compatible fan control interfaces
- **Dynamic Temperature Control**: Adaptive fan curves based on real-time GPU temperature
- **Power Spike Detection**: Proactive cooling boost when GPU power consumption spikes
- **Graceful Shutdown**: Proper signal handling and resource cleanup
- **Configurable**: Full configuration via file or command line
- **Systemd Integration**: Production-ready service file included
- **CSV Logging**: Detailed telemetry logging for analysis

## Inspiration

The genesis of this tool was sparked by an incredible find on eBay—an NVIDIA P40 for $175. The challenge was cooling a datacenter GPU outside its native server environment. While hardware adaptations existed, an intuitive method to regulate fan speed based on GPU temperature and power consumption was missing.

The solution: Position the GPU's intake directly in front of the ATX case's intake fans, providing fresh air directly to the GPU rather than pre-warmed air from CPU cooling. This not only enhanced cooling efficiency but also significantly reduced noise levels.

## Requirements

- Python 3.8+
- NVIDIA GPU with driver installed
- Linux with hwmon support (most motherboards)
- Root privileges (for hwmon access)

### Python Dependencies

```bash
pip install pynvml
```

## Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/r3d91ll/Baram.git
cd Baram

# Install dependencies
pip install -r requirements.txt

# List available hwmon devices
sudo python baram.py --list-hwmon

# Run with auto-detection
sudo python baram.py
```

### System Installation

```bash
# Install to /opt/baram
sudo mkdir -p /opt/baram /etc/baram /var/log/baram
sudo cp baram.py /opt/baram/
sudo cp baram.conf /etc/baram/

# Install systemd service
sudo cp baram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now baram
```

## Usage

### Command Line

```bash
# Show help
python baram.py --help

# List available hwmon devices and PWM channels
sudo python baram.py --list-hwmon

# Run with defaults (auto-detect hwmon)
sudo python baram.py

# Specify GPU index and hwmon device
sudo python baram.py --gpu-index 0 --hwmon-device hwmon2 --pwm-channel 1

# Override temperature thresholds
sudo python baram.py --min-temp 35 --max-temp 75
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config` | Path to configuration file | `/etc/baram/baram.conf` |
| `--gpu-index` | GPU index to monitor (0-based) | `0` |
| `--hwmon-device` | Hwmon device path/name (empty = auto) | Auto-detect |
| `--pwm-channel` | PWM channel number (1-based) | `1` |
| `--min-temp` | Minimum temperature threshold (°C) | `40` |
| `--max-temp` | Maximum temperature threshold (°C) | `80` |
| `--min-pwm-value` | Minimum PWM value (0-255) | `20` |
| `--max-pwm-value` | Maximum PWM value (0-255) | `255` |
| `--list-hwmon` | List available hwmon devices and exit | - |

### Configuration File

Copy `baram.conf` to `/etc/baram/baram.conf` and edit as needed. Command line arguments override configuration file settings.

See `baram.conf` for all available options with detailed comments.

### Systemd Service

```bash
# Start the service
sudo systemctl start baram

# Check status
sudo systemctl status baram

# View logs
sudo journalctl -u baram -f

# Enable at boot
sudo systemctl enable baram
```

## How It Works

### Temperature-Based Fan Curve

Baram uses a linear interpolation between temperature thresholds:

| GPU Temp | PWM Range |
|----------|-----------|
| < 30°C | 0-0 |
| 30-40°C | 0-30 |
| 40-50°C | 30-60 |
| 50-60°C | 60-90 |
| 60-70°C | 90-120 |
| 70-max°C | 120-255 |

### Power Spike Detection

When GPU power consumption exceeds the threshold for consecutive readings:
1. Spike counter increments
2. After `wattage_spike_count` spikes, minimum PWM is raised to `wattage_pwm_value`
3. When power drops, counter decrements
4. When counter reaches 0, minimum PWM returns to normal

This provides proactive cooling before temperature rises during heavy GPU loads.

## Hardware Setup

### Tested Configuration

- **Motherboard**: ASUS ROG Strix B550-XE Gaming (AMD chipset)
- **GPU**: NVIDIA Tesla P40 24GB
- **Fan Shroud**: [3D Printed Fan Shroud](https://www.ebay.com/itm/155965387407)
- **Fans**: ARCTIC S4028-15K (40x40x28mm, 1400-15000 RPM, PWM)

### Finding Your hwmon Device

```bash
# List all hwmon devices
ls -la /sys/class/hwmon/

# Check device names
for d in /sys/class/hwmon/hwmon*; do echo "$d: $(cat $d/name 2>/dev/null)"; done

# Or use Baram's built-in detection
sudo python baram.py --list-hwmon
```

Common motherboard sensor chips:
- **Nuvoton**: nct6775, nct6776, nct6779, nct6791-nct6798
- **ITE**: it8720, it8721, it8728, it8771, it8772
- **Winbond**: w83627, w83667, w83795
- **ASUS**: asus_wmi_sensors, asus-ec-sensors

## Logging

Baram creates two log files in `/var/log/baram/`:

- `baram.log` - Application logs (startup, errors, debug info)
- `baram.csv` - Telemetry data (timestamp, temp, RPM, PWM, power)

## Troubleshooting

### Permission Denied

Hwmon files require root access:
```bash
sudo python baram.py
```

### No hwmon Device Found

1. Check if your motherboard's sensor driver is loaded:
   ```bash
   lsmod | grep -E "nct6775|it87|w83627"
   ```

2. Try loading the driver manually:
   ```bash
   sudo modprobe nct6775  # or it87, etc.
   ```

3. Add to `/etc/modules` for persistence

### Wrong Fan Responding

Use `--list-hwmon` to identify the correct device and channel, then specify explicitly:
```bash
sudo python baram.py --hwmon-device /sys/class/hwmon/hwmon3 --pwm-channel 2
```

## GPU Load Testing

For testing cooling performance under load:
- [gpu-burn](https://github.com/wilicc/gpu-burn) - GPU stress test

## Compatibility

### Verified Working

- ASUS ROG Strix B550-XE Gaming (AMD, nct6775)

### Should Work

- Most motherboards with Linux hwmon support
- Any NVIDIA GPU supported by NVML

### Known Limitations

- hwmon paths (`/sys/class/hwmon/hwmonN`) can change between boots
- Some motherboards require specific kernel modules
- Virtual machines may not expose hwmon interfaces

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.
