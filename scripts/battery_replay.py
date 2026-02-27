import serial
import time
import csv
import sys
import argparse
import board, busio
from adafruit_ina219 import INA219
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# ---- Arguments ----
parser = argparse.ArgumentParser(description='Battery discharge replay and power profiling')
parser.add_argument('-i', '--input', default='battery_profile.csv', help='Input battery profile CSV')
parser.add_argument('-o', '--output', default='power_log.csv', help='Output power log CSV')
parser.add_argument('-p', '--plot', default='power_report.png', help='Output plot filename')
parser.add_argument('--port', default='/dev/serial0', help='Serial port for KA3005P')
parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
parser.add_argument('--current-limit', type=float, default=0.500, help='PSU current limit (A)')
parser.add_argument('--sample-interval', type=float, default=0.05, help='INA219 sample interval (s)')
args = parser.parse_args()

# ---- Helpers ----
def progress_bar(pct, width=30):
    filled = int(width * pct)
    bar = '█' * filled + '░' * (width - filled)
    return f'[{bar}] {pct*100:5.1f}%'

def print_header(text):
    print(f'\n{"="*60}')
    print(f'  {text}')
    print(f'{"="*60}')

# ---- Init ----
print_header('POWER PROFILE TEST BENCH')
print(f'  Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# ---- INA219 Setup ----
print('[INIT] Connecting to INA219 ...', end=' ', flush=True)
i2c = busio.I2C(board.SCL, board.SDA)
ina = INA219(i2c)
print('OK ✓')

# ---- KA3005P Setup ----
print(f'[INIT] Connecting to PSU ({args.port}) ...', end=' ', flush=True)
psu = serial.Serial(args.port, args.baud, timeout=1)
time.sleep(0.1)
psu.write(b'*IDN?')
time.sleep(0.1)
idn = psu.read(psu.in_waiting).decode().strip()
if not idn:
    print('FAIL ✗')
    print('       Could not communicate with power supply.')
    sys.exit(2)
print(f'OK ✓')
print(f'       PSU: {idn}')

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
print(f'[INIT] Loading profile ({args.input}) ...', end=' ', flush=True)
profile_times = []
profile_voltages = []
with open(args.input, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        profile_times.append(float(row['epoch']))
        profile_voltages.append(float(row['voltage']))

if len(profile_times) < 2:
    print('FAIL ✗')
    print('       Need at least 2 data points.')
    sys.exit(2)

t_start_profile = profile_times[0]
offsets = [t - t_start_profile for t in profile_times]
total_duration = offsets[-1]
print(f'OK ✓ ({len(offsets)} points)')

print()
print(f'  Profile:    {total_duration:.1f}s, {profile_voltages[0]:.2f}V → {profile_voltages[-1]:.2f}V')
print(f'  Output:     {args.output}')
print(f'  Plot:       {args.plot}')

# ---- Run Interpolated Discharge ----
print_header('RUNNING DISCHARGE SWEEP')

set_current(args.current_limit)
set_voltage(profile_voltages[0])
output_on()
time.sleep(0.5)

# Verify output is on
v_check = ina.bus_voltage
print(f'[START] Output ON — initial reading: {v_check:.2f}V')
print()

start_time = time.time()
sample_count = 0
last_set_voltage = None
last_print_time = 0

# Data arrays for plotting
data_time = []
data_set_v = []
data_bus_v = []
data_current = []
data_power = []

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

            data_time.append(elapsed)
            data_set_v.append(target_v)
            data_bus_v.append(v)
            data_current.append(i)
            data_power.append(p)

            sample_count += 1

            # Print live status every 1 second
            if now - last_print_time >= 1.0:
                pct = elapsed / total_duration
                bar = progress_bar(pct)
                remaining = total_duration - elapsed
                print(f'  {bar}  {target_v:.2f}V  {i:.1f}mA  {v*i/1000:.3f}W  ETA:{remaining:.0f}s', flush=True)
                last_print_time = now

            time.sleep(args.sample_interval)

except Exception as e:
    print(f'\n[ERROR] {e}')
    output_off()
    psu.close()
    sys.exit(2)

output_off()
psu.close()

# ---- Compute Stats ----
data_current = np.array(data_current)
data_bus_v = np.array(data_bus_v)
data_power = np.array(data_power)
data_time = np.array(data_time)

avg_current = np.mean(data_current)
peak_current = np.max(data_current)
min_current = np.min(data_current)
std_current = np.std(data_current)
avg_power = np.mean(data_bus_v * data_current / 1000)  # watts
peak_power = np.max(data_bus_v * data_current / 1000)
min_voltage_seen = np.min(data_bus_v)
max_voltage_seen = np.max(data_bus_v)

# ---- Print Summary ----
print_header('RESULTS')
print(f'  Samples:        {sample_count}')
print(f'  Duration:       {data_time[-1]:.1f}s')
print()
print(f'  Avg Current:    {avg_current:.1f} mA')
print(f'  Peak Current:   {peak_current:.1f} mA')
print(f'  Min Current:    {min_current:.1f} mA')
print(f'  Std Dev:        {std_current:.2f} mA')
print()
print(f'  Avg Power:      {avg_power:.3f} W')
print(f'  Peak Power:     {peak_power:.3f} W')
print()
print(f'  Voltage Range:  {min_voltage_seen:.2f}V — {max_voltage_seen:.2f}V')
print(f'  Min Survived:   {min_voltage_seen:.2f}V')
print('=' * 60)

# ---- Generate Plot ----
print(f'\n[PLOT] Generating report → {args.plot}')

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                 gridspec_kw={'height_ratios': [2, 1]})
fig.suptitle('Power Profile Report', fontsize=14, fontweight='bold', y=0.98)

# Subtitle with key stats
fig.text(0.5, 0.94,
         f'Avg: {avg_current:.1f} mA  |  Peak: {peak_current:.1f} mA  |  '
         f'Avg Power: {avg_power:.3f} W  |  Min Voltage: {min_voltage_seen:.2f} V',
         ha='center', fontsize=10, color='#555555',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#f0f0f0', edgecolor='#cccccc'))

# Top plot: Current over time
ax1.plot(data_time, data_current, color='#2196F3', linewidth=0.8, alpha=0.7, label='Current')
ax1.axhline(y=avg_current, color='#4CAF50', linewidth=2, linestyle='-',
            label=f'Avg: {avg_current:.1f} mA')
ax1.axhline(y=peak_current, color='#FF5722', linewidth=1, linestyle='--', alpha=0.7,
            label=f'Peak: {peak_current:.1f} mA')
ax1.fill_between(data_time,
                 avg_current - std_current,
                 avg_current + std_current,
                 alpha=0.15, color='#4CAF50', label=f'±1σ ({std_current:.1f} mA)')
ax1.set_ylabel('Current (mA)')
ax1.legend(loc='upper right', fontsize=9)
ax1.grid(True, alpha=0.3)

# Bottom plot: Voltage over time
ax2.plot(data_time, data_bus_v, color='#9C27B0', linewidth=1, alpha=0.8, label='Measured')
ax2.plot(data_time, data_set_v, color='#FF9800', linewidth=1, linestyle='--', alpha=0.6, label='Set')
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Voltage (V)')
ax2.legend(loc='upper right', fontsize=9)
ax2.grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig(args.plot, dpi=150, bbox_inches='tight')
print(f'[DONE] Report saved. {sample_count} samples collected.')
sys.exit(0)
