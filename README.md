# Baram: Advanced System Cooling Management Tool

A Linux utility designed to manage fans on Tesla Datacenter GPUs mounted in ATX cases. Named after the Korean word for wind, Baram provides an intuitive, CLI-based interface for optimizing cooling performance and noise management in Linux systems.

## Overview

Baram is a specialized cooling management tool developed for Nvidia data center GPUs repurposed in ATX-like cases. It enhances thermal performance, extends component longevity, and minimizes noise, making it ideal for enthusiasts and newcomers alike.

## Mission

Our mission is to empower users to revitalize used data center GPUs with an advanced, accessible cooling management solution.

## Key Features

### Stage 1: Initial Release

- **Profile Management**: Users can create, save, and switch between multiple cooling profiles.
- **Dynamic Temperature Monitoring**: Adaptive fan control is based on real-time GPU and system temperatures.

### Stage 2: Logic Enhancement

- **System-Wide Fan Identification**: Configures GPU, CPU, and chassis fans for a unified cooling strategy.
- **Enhanced Temperature Logic**: Improves temperature monitoring and fan control algorithms.

### Stage 3: Optimization

- **Airflow Optimization Profiles**: Balances intake and exhaust to improve cooling and reduce noise.
- **Noise Optimization Mode**: Minimizes noise while maintaining effective cooling.

### Stage 4: Data Visualization and Monitoring

- **Historical Data Graphing**: Users can generate graphs from historical data for cooling performance over time.
- **Live Graphing**: Real-time graphing of temperature and fan speeds for immediate feedback. This will be implemented with the `baram_graphs.py` script.

## Roadmap

- **Graphing Function Integration**: The next major feature will be the addition of graphing functionalities through `baram_graphs.py`, which will handle both historical data visualization and real-time monitoring graphing.

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

## Contributing

We welcome contributions of all kinds, from code to documentation, from all members of the community. Please see our contributing guidelines for more information on how to get involved.

## License

Details about the project's license are included here, outlining the permissions and restrictions for using and distributing Baram.

## Acknowledgments

Our heartfelt thanks to the community, especially those who have contributed code, feedback, and support to the project.

