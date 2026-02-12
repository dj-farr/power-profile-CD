import serial
import time
import csv
import sys
import board, busio
from adafruit_ina219 import INA219
import numpy as np

# ---- Configuration ----
INPUT_CSV = sys.argv[1] if len(sys.argv) > 1 else 'battery_profile.csv'
OUTPUT_CSV = sys.argv[2] if len(sys.argv) > 2 else 'power_log.csv'
SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 115200
CURRENT_LIMIT = 0.500  # amps
SAMPLE_INTERVAL = 0.05  # seconds between INA219 readings

# ---- INA219 Setup ----
i2c = busio.I2C(board.SCL, board.SDA)
ina = INA219(i2c)

# ---- KA3005P Setup ----
psu = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(0.1)

def psu_write(cmd):
    psu.write(cmd.encode())
    time.sleep(0.05)

def set_voltage(v):
    # Clamp to PSU resolution (10 mV)
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
with open(INPUT_CSV, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        profile_times.append(float(row['epoch']))
        profile_voltages.append(float(row['voltage']))

if len(profile_times) < 2:
    print('Error: input CSV needs at least 2 rows.')
    sys.exit(1)

# Convert to offsets from start
t_start_profile = profile_times[0]
offsets = [t - t_start_profile for t in profile_times]
total_duration = offsets[-1]

print(f'Loaded {len(offsets)} points from {INPUT_CSV}')
print(f'Profile duration: {total_duration:.1f} seconds')
print(f'Voltage range: {profile_voltages[0]:.2f}V -> {profile_voltages[-1]:.2f}V')
print(f'Interpolation: linear between points')
print(f'Output file: {OUTPUT_CSV}')
print('Starting in 3 seconds...')
time.sleep(3)

# ---- Run Interpolated Discharge ----
set_current(CURRENT_LIMIT)
set_voltage(profile_voltages[0])
output_on()
time.sleep(0.5)

start_time = time.time()
sample_count = 0
last_set_voltage = None

with open(OUTPUT_CSV, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['time_s', 'set_voltage_V', 'bus_voltage_V', 'current_mA', 'power_mW'])

    try:
        while True:
            now = time.time()
            elapsed = now - start_time

            if elapsed > total_duration:
                break

            # Linearly interpolate voltage at current time
            target_v = round(float(np.interp(elapsed, offsets, profile_voltages)), 2)

            # Only send serial command if voltage actually changed (10 mV resolution)
            if target_v != last_set_voltage:
                set_voltage(target_v)
                last_set_voltage = target_v

            # Sample INA219
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

            time.sleep(SAMPLE_INTERVAL)

    except KeyboardInterrupt:
        print('\nStopped by user.')

output_off()
psu.close()
print(f'Done. {sample_count} samples saved to {OUTPUT_CSV}')
