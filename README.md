# Baram: Advanced System Cooling Management Tool

A Linux utility designed to manage fans on Tesla Datacenter GPUs mounted in ATX cases. Named after the Korean word for wind, Baram provides an intuitive, CLI-based interface for optimizing cooling performance and noise management in Linux systems.

## Overview

Baram is a specialized cooling management tool developed for Nvidia data center GPUs repurposed in ATX-like cases. It enhances thermal performance, extends component longevity, and minimizes noise, making it ideal for enthusiasts and newcomers alike.

## Inspiration

The genesis of this tool was sparked by an incredible find on Ebay—an Nvidia P40 for $175. The snag came when I tried integrating this powerhouse into a non-server setup. Cooling it outside of its native server habitat proved daunting. While hardware adaptations were somewhat navigated by others, an intuitive method to regulate fan speed in response to the GPU's temperature or power consumption—especially within the confines of a consumer-grade motherboard—was conspicuously absent.

This challenge morphed into an opportunity. My initial testing has shown that cooling a datacenter grade GPU within an ATX case is not only feasible but can be done in such a way as to minimize the excess noise of a blower fan. The strategic placement of the GPU's blower fans directly in front of the ATX case's intake fans facilitated a more effective cooling mechanism. Unlike in server cases, where the GPUs are relegated to the rear and subjected to pre-warmed air post-CPU cooling, my setup benefitted from a direct blast of fresh air. This not only enhanced cooling efficiency but also significantly reduced noise levels, making it an effective solution for enthusiasts venturing into machine learning with high-performance, datacenter-grade GPUs in consumer setups.

## Current State

Baram.py is currently functional and uses NVML (NVIDIA Management Library) for retrieving GPU information. The baram_graphs.py script, which provides real-time graphing capabilities, is currently under development and has been moved to a separate branch.

## Requirements

The current version of Baram has the following Python dependencies:

- pandas
- matplotlib
- pynvml

These dependencies are listed in the `requirements.txt` file. To install them, run:

```bash
pip install -r requirements.txt
```

## Key Features

- **Dynamic Temperature and Power Monitoring**: Adaptive fan control based on real-time GPU temperature and power consumption.
- **Configurable Thresholds**: Customizable temperature and power thresholds for fine-tuned cooling performance.
- **Logging**: Detailed logging of GPU temperature, fan speed, PWM values, and power consumption for analysis and troubleshooting.

## Getting Started

### Installation

1. Ensure Python3 and Pip are installed on your system.
2. Install the required Python libraries:

    ```bash
    pip install -r requirements.txt
    ```

### Running Baram

Execute the following command to start Baram:

```bash
python baram.py
```

### Creating a Service for Ubuntu

To ensure Baram runs as a service on Ubuntu, follow these steps:

1. Create a systemd service file:

    ```bash
    sudo nano /etc/systemd/system/baram.service
    ```

2. Add the following configuration, modifying the `ExecStart` path as necessary:

    ```ini
    [Unit]
    Description=Baram Cooling Management Service
    After=network.target

    [Service]
    Type=simple
    User=your_user
    ExecStart=/usr/bin/python3 /path/to/baram.py

    [Install]
    WantedBy=multi-user.target
    ```

3. Enable and start the Baram service:

    ```bash
    sudo systemctl enable baram.service
    sudo systemctl start baram.service
    ```

4. Check the service status with:

    ```bash
    sudo systemctl status baram.service
    ```

### Usage

- To view available commands, use:

    ```bash
    python baram.py --help
    ```

- For creating and managing profiles, consult the Baram documentation or the help command output.

## Hardware Setup

- The fan shroud used in this project can be found here: [3D Printed Fan Shroud](https://www.ebay.com/itm/155965387407?itmmeta=01HV1N68NJBGHTPM9B78S7X0R8&hash=item245042f28f:g:U20AAOSwpi1l30ge&itmprp=enc%3AAQAJAAAA4Pbx8AObvgfLFoghvfT1R%2BbKVBW0Jo1FLJWKyaardEWk8yBvklT%2FTwew6a5Co1fipRfaeWK%2Bsw5bjUgC1WqYNNzbUVDclpdPM4bqoR0FWnbj9wF8m%2BbeDG5sxgsvhDP4YSGW655UR8oyVHCSuo8%2BLbKTle7yghaEnPzLfTDELi8UIUVxtkfwjU4TKEYhrwR0d5I0CWrmEP5rb2huM2m%2BWa6XZKno3Zxd5sGAbexlqIWN2oXVdxAdU15fSdjWG31QMlqhnp6AFVTAjAorrm8dXhiOqcf5Twxrk1YsR3hUSmLx%7Ctkp%3ABk9SR\_SKmbXYYw)
- The fans used are ARCTIC S4028-15K - 40x40x28 mm Server Fan, 1400-15000 RPM, PWM Regulated, 4-pin Connector, 12 V DC, Rack Cooling Fan.

## GPU Load Testing

For load testing the GPU, we recommend using gpu_burn, which can be found here: [gpu_burn](https://github.com/wilicc/gpu-burn)

## Compatibility Note

It's important to recognize that each chipset is unique, which means that both the access points for fan control interfaces and the module names within the Linux operating system can vary significantly across different motherboards. Specifically, compatibility with 'Baram' has been verified for the Asus Rog Strix B550xe motherboard, which utilizes an AMD chipset. However, given the vast diversity of hardware configurations and specific edge cases, we cannot assure universal compatibility. We recommend consulting your motherboard's documentation or seeking community support for configurations not explicitly mentioned.

## Contributing

We welcome contributions of all kinds, from code to documentation, from all members of the community. Please see our contributing guidelines for more information on how to get involved.

## License

Details about the project's license are included here, outlining the permissions and restrictions for using and distributing Baram.
