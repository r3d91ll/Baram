import subprocess
import time
import csv
import argparse

# Log file
LOG_FILE = "/var/log/cpu_power_log.csv"

# Stress test duration in seconds (e.g., 10 minutes)
DURATION = 600

def parse_args():
    parser = argparse.ArgumentParser(description="CPU stress testing and logging script")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (no actual stress test)")
    parser.add_argument("--cpu", action="store_true", help="Run CPU stress test")
    return parser.parse_args()

def main():
    args = parse_args()

    # Capture the start timestamp
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")

    # Open the log file in write mode
    with open(LOG_FILE, "w") as log_file:
        # Create a CSV writer
        csv_writer = csv.writer(log_file)

        # Write the header row
        csv_writer.writerow(["Timestamp", "Core", "Busy%", "PkgWatt"])

        stress_process = None

        if not args.debug:
            # Start the stress-ng test for the specified duration if --cpu flag is set
            if args.cpu:
                stress_process = subprocess.Popen(["stress-ng", "--cpu", "0", "--timeout", str(DURATION)])

        # Start turbostat as a subprocess
        turbostat_process = subprocess.Popen(["sudo", "./turbostat", "--interval", "1", "--quiet", "--show", "Core,PkgWatt,Busy%"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        total_energy = 0.0
        interval_count = 0

        # Monitor and log while stress-ng is running or in debug mode
        while (not args.debug and args.cpu and stress_process.poll() is None) or args.debug:
            # Read the output from turbostat
            output = turbostat_process.stdout.readline().strip()

            # Skip the header row
            if "Core" in output:
                continue

            # Split the output into columns
            columns = output.split()

            # Extract the relevant values
            core = columns[0]
            busy_percent = columns[1]
            pkg_watt = float(columns[2])

            # Get the current timestamp
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")

            # Write the data to the log file
            csv_writer.writerow([current_time, core, busy_percent, pkg_watt])

            # Accumulate the package power consumption
            total_energy += pkg_watt

            interval_count += 1

            if args.debug:
                break

        # Stop turbostat
        turbostat_process.terminate()

    # Calculate the average power consumption and total energy consumption
    avg_power = total_energy / interval_count
    total_energy_wh = total_energy / 3600  # Convert seconds to hours
    total_energy_kwh = total_energy_wh / 1000  # Convert Wh to kWh

    # Capture the end timestamp
    end_time = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Stress test and power logging completed.")
    print(f"Start time: {start_time}")
    print(f"End time: {end_time}")
    print(f"Average power consumption: {avg_power:.2f} W")
    print(f"Total energy consumption: {total_energy_wh:.2f} Wh ({total_energy_kwh:.2f} kWh)")
    print(f"Log file: {LOG_FILE}")

if __name__ == "__main__":
    main()