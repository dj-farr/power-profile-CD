import matplotlib.pyplot as plt
import csv
import sys

INPUT_CSV = sys.argv[1] if len(sys.argv) > 1 else 'power_log.csv'

time_s = []
bus_voltage = []
current_mA = []

with open(INPUT_CSV, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        time_s.append(float(row['time_s']))
        bus_voltage.append(float(row['bus_voltage_V']))
        current_mA.append(float(row['current_mA']))

fig, ax1 = plt.subplots(figsize=(12, 6))

color1 = '#2196F3'
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Bus Voltage (V)', color=color1)
ax1.plot(time_s, bus_voltage, color=color1, linewidth=1, alpha=0.8, label='Bus Voltage')
ax1.tick_params(axis='y', labelcolor=color1)

ax2 = ax1.twinx()
color2 = '#FF5722'
ax2.set_ylabel('Current (mA)', color=color2)
ax2.plot(time_s, current_mA, color=color2, linewidth=1, alpha=0.8, label='Current')
ax2.tick_params(axis='y', labelcolor=color2)

plt.title('Battery Discharge Profile - Power Characterization')
fig.tight_layout()
plt.savefig('discharge_plot.png', dpi=150)
plt.show()
print(f'Plot saved to discharge_plot.png')
