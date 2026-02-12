import serial
import time
import csv
import sys
import argparse
import board, busio
from adafruit_ina219 import INA219
import numpy as np

# ---- Arguments ----
parser = argparse.ArgumentParser(description='Battery discharge replay and power profiling')
parser.add_argument('-i', '--input', default='battery_profile.csv', help='Input battery profile CSV')
parser.add_argument('-o', '--output', default='power_log.csv', help='Output power log CSV')
parser.add_argument('--port', default='/dev/serial0', help='Serial port for KA3005P')
parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
parser.add_argument('--current-limit', type=float, default=0.500, help='PSU current limit (A)')
parser.add_argument('--sample-interval', type=float, default=0.05, help='INA219 sample interval (s)')
args = parser.parse_args()

# ---- INA219 Setup ----
i2c = busio.I2C(board.SCL, board.SDA)
ina = INA219(i2c)

# ---- KA3005P Setup ----
psu = serial.Serial(args.port, args.baud, timeout=1)
time.sleep(0.1)

def psu_write(cmd):
    psu.write(cmd.encode())
    time.sleep(0.05)

def set_voltage(v):
    v = round(v, 2)
    psu_write(f'VSET1:{v:05.2f}')

def set_current(i):
    psu_write(f'ISET1:{i:05.3f}')

def output_on():
    psu_write('OUT1')

def output_off():
    psu_write('OUT0')

# ---- Load Input Profile ----
profile_times = []
profile_voltages = []
with open(args.input, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        profile_times.append(float(row['epoch']))
        profile_voltages.append(float(row['voltage']))

if len(profile_times) < 2:
    print('Error: input CSV needs at least 2 rows.')
    sys.exit(2)

t_start_profile = profile_times[0]
offsets = [t - t_start_profile for t in profile_times]
total_duration = offsets[-1]

print(f'Loaded {len(offsets)} points from {args.input}')
print(f'Profile duration: {total_duration:.1f} seconds')
print(f'Voltage range: {profile_voltages[0]:.2f}V -> {profile_voltages[-1]:.2f}V')
print(f'Output file: {args.output}')

# ---- Run Interpolated Discharge ----
set_current(args.current_limit)
set_voltage(profile_voltages[0])
output_on()
time.sleep(0.5)

start_time = time.time()
sample_count = 0
last_set_voltage = None

try:
    with open(args.output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time_s', 'set_voltage_V', 'bus_voltage_V', 'current_mA', 'power_mW'])

        while True:
            now = time.time()
            elapsed = now - start_time

            if elapsed > total_duration:
                break

            target_v = round(float(np.interp(elapsed, offsets, profile_voltages)), 2)

            if target_v != last_set_voltage:
                set_voltage(target_v)
                last_set_voltage = target_v

            v = ina.bus_voltage
            i = ina.current
            p = ina.power

            writer.writerow([
                f'{elapsed:.3f}',
                f'{target_v:.2f}',
                f'{v:.3f}',
                f'{i:.3f}',
                f'{p:.3f}'
            ])

            sample_count += 1
            if sample_count % 20 == 0:
                print(f'{elapsed:.1f}s | Set: {target_v:.2f}V | Meas: {v:.2f}V | {i:.1f}mA | {p:.1f}mW')

            time.sleep(args.sample_interval)

except Exception as e:
    print(f'Error during sweep: {e}')
    output_off()
    psu.close()
    sys.exit(2)

output_off()
psu.close()
print(f'Done. {sample_count} samples saved to {args.output}')
sys.exit(0)