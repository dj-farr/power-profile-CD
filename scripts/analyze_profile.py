import matplotlib.pyplot as plt
import csv
import sys
import numpy as np
import argparse

# ---- Arguments ----
parser = argparse.ArgumentParser(description='Power profile analysis for CI/CD pipeline')
parser.add_argument('input_csv', help='Path to power_log.csv from battery_replay.py')
parser.add_argument('-o', '--output', default='profile_report.png', help='Output plot filename')
parser.add_argument('--avg-budget', type=float, default=200.0, help='Max average current (mA) before FAIL')
parser.add_argument('--peak-budget', type=float, default=500.0, help='Max peak current (mA) before FAIL')
parser.add_argument('--min-voltage', type=float, default=5.60, help='Minimum voltage (V) device must survive')
args = parser.parse_args()

# ---- Load Data ----
time_s = []
bus_voltage = []
current_mA = []

with open(args.input_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        time_s.append(float(row['time_s']))
        bus_voltage.append(float(row['bus_voltage_V']))
        current_mA.append(float(row['current_mA']))

time_s = np.array(time_s)
bus_voltage = np.array(bus_voltage)
current_mA = np.array(current_mA)

# ---- Compute Metrics ----
avg_current = np.mean(current_mA)
peak_current = np.max(current_mA)
min_voltage = np.min(bus_voltage)

avg_pass = avg_current <= args.avg_budget
peak_pass = peak_current <= args.peak_budget
voltage_pass = min_voltage <= args.min_voltage + 0.1  # survived to within 100mV of target

all_pass = avg_pass and peak_pass and voltage_pass

# ---- Plot ----
fig, ax = plt.subplots(figsize=(12, 5))

ax.plot(time_s, current_mA, color='#2196F3', linewidth=0.8, alpha=0.7, label='Current')
ax.axhline(y=avg_current, color='#4CAF50', linewidth=2, linestyle='-', label=f'Avg: {avg_current:.1f} mA')
ax.axhline(y=args.avg_budget, color='#FF9800', linewidth=2, linestyle='--', label=f'Avg budget: {args.avg_budget:.0f} mA')
ax.axhline(y=args.peak_budget, color='#F44336', linewidth=2, linestyle='--', label=f'Peak budget: {args.peak_budget:.0f} mA')

ax.set_xlabel('Time (s)')
ax.set_ylabel('Current (mA)')
ax.set_title(f'Power Profile — {"PASS ✓" if all_pass else "FAIL ✗"}')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)

fig.tight_layout()
plt.savefig(args.output, dpi=150)

# ---- Summary ----
print('=' * 60)
print(f'  avg: {avg_current:.1f} mA | peak: {peak_current:.1f} mA | min voltage: {min_voltage:.2f}V')
print()
print(f'  Avg current:  {avg_current:.1f} / {args.avg_budget:.0f} mA  {"PASS" if avg_pass else "FAIL"}')
print(f'  Peak current: {peak_current:.1f} / {args.peak_budget:.0f} mA  {"PASS" if peak_pass else "FAIL"}')
print(f'  Min voltage:  {min_voltage:.2f} / {args.min_voltage:.2f} V     {"PASS" if voltage_pass else "FAIL"}')
print()
print(f'  RESULT: {"PASS" if all_pass else "FAIL"}')
print('=' * 60)
print(f'  Plot saved to {args.output}')

# Exit code for CI
sys.exit(0 if all_pass else 1)
