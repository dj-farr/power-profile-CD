import matplotlib.pyplot as plt
import csv
import sys
import numpy as np
from scipy import stats

INPUT_CSV = sys.argv[1] if len(sys.argv) > 1 else 'power_log.csv'

# ---- Load Data ----
time_s = []
bus_voltage = []
current_mA = []
power_mW = []

with open(INPUT_CSV, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        time_s.append(float(row['time_s']))
        bus_voltage.append(float(row['bus_voltage_V']))
        current_mA.append(float(row['current_mA']))
        power_mW.append(float(row['power_mW']))

time_s = np.array(time_s)
bus_voltage = np.array(bus_voltage)
current_mA = np.array(current_mA)
power_mW = np.array(power_mW)

# Recompute power from measured values for better accuracy
power_calc = bus_voltage * current_mA  # V * mA = mW

# ---- 1. Power vs Voltage Scatter with Regression ----
slope, intercept, r_value, p_value, std_err = stats.linregress(bus_voltage, power_calc)
fit_line = slope * bus_voltage + intercept

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
ax.scatter(bus_voltage, power_calc, s=2, alpha=0.4, color='#2196F3', label='Measured')
ax.plot(bus_voltage, fit_line, 'r-', linewidth=2,
        label=f'Fit: P = {slope:.2f}V + {intercept:.2f}\nR² = {r_value**2:.4f}, p = {p_value:.2e}')
ax.set_xlabel('Bus Voltage (V)')
ax.set_ylabel('Power (mW)')
ax.set_title('Power vs Voltage - Linear Regression')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# ---- 2. Current vs Voltage Scatter with Regression ----
slope_i, intercept_i, r_i, p_i, std_err_i = stats.linregress(bus_voltage, current_mA)
fit_line_i = slope_i * bus_voltage + intercept_i

ax = axes[0, 1]
ax.scatter(bus_voltage, current_mA, s=2, alpha=0.4, color='#FF5722', label='Measured')
ax.plot(bus_voltage, fit_line_i, 'r-', linewidth=2,
        label=f'Fit: I = {slope_i:.2f}V + {intercept_i:.2f}\nR² = {r_i**2:.4f}, p = {p_i:.2e}')
ax.set_xlabel('Bus Voltage (V)')
ax.set_ylabel('Current (mA)')
ax.set_title('Current vs Voltage - Linear Regression')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# ---- 3. Windowed Statistics ----
window_duration = 5.0  # seconds
window_starts = np.arange(time_s[0], time_s[-1], window_duration)

win_time = []
win_voltage_mean = []
win_power_mean = []
win_power_std = []
win_current_mean = []
win_current_std = []
win_current_min = []
win_current_max = []

for ws in window_starts:
    mask = (time_s >= ws) & (time_s < ws + window_duration)
    if np.sum(mask) < 5:
        continue
    win_time.append(ws + window_duration / 2)
    win_voltage_mean.append(np.mean(bus_voltage[mask]))
    win_power_mean.append(np.mean(power_calc[mask]))
    win_power_std.append(np.std(power_calc[mask]))
    win_current_mean.append(np.mean(current_mA[mask]))
    win_current_std.append(np.std(current_mA[mask]))
    win_current_min.append(np.min(current_mA[mask]))
    win_current_max.append(np.max(current_mA[mask]))

win_time = np.array(win_time)
win_voltage_mean = np.array(win_voltage_mean)
win_power_mean = np.array(win_power_mean)
win_power_std = np.array(win_power_std)
win_current_mean = np.array(win_current_mean)
win_current_std = np.array(win_current_std)
win_current_min = np.array(win_current_min)
win_current_max = np.array(win_current_max)

ax = axes[1, 0]
ax.plot(win_time, win_current_mean, 'o-', color='#FF5722', linewidth=1.5, label='Mean')
ax.fill_between(win_time, win_current_min, win_current_max, alpha=0.2, color='#FF5722', label='Min/Max')
ax.fill_between(win_time,
                win_current_mean - win_current_std,
                win_current_mean + win_current_std,
                alpha=0.3, color='#FF5722', label='±1σ')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Current (mA)')
ax.set_title(f'Windowed Current ({window_duration:.0f}s windows)')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# ---- 4. Windowed Power vs Voltage ----
ax = axes[1, 1]
ax.errorbar(win_voltage_mean, win_power_mean, yerr=win_power_std,
            fmt='o-', color='#9C27B0', capsize=4, linewidth=1.5, label='Mean ± 1σ')
ax.set_xlabel('Bus Voltage (V)')
ax.set_ylabel('Power (mW)')
ax.set_title(f'Windowed Power vs Voltage ({window_duration:.0f}s windows)')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

fig.suptitle('Battery Discharge - Statistical Analysis', fontsize=14, fontweight='bold')
fig.tight_layout()
plt.savefig('discharge_analysis.png', dpi=150)
plt.show()

# ---- Print Summary ----
print('=' * 60)
print('STATISTICAL SUMMARY')
print('=' * 60)
print(f'Total samples:    {len(time_s)}')
print(f'Duration:         {time_s[-1] - time_s[0]:.1f} s')
print(f'Voltage range:    {bus_voltage.min():.2f}V - {bus_voltage.max():.2f}V')
print(f'Current range:    {current_mA.min():.2f} - {current_mA.max():.2f} mA')
print(f'Power range:      {power_calc.min():.2f} - {power_calc.max():.2f} mW')
print()
print('POWER vs VOLTAGE REGRESSION:')
print(f'  Slope:          {slope:.4f} mW/V')
print(f'  Intercept:      {intercept:.4f} mW')
print(f'  R²:             {r_value**2:.6f}')
print(f'  p-value:        {p_value:.2e}')
print()
print('CURRENT vs VOLTAGE REGRESSION:')
print(f'  Slope:          {slope_i:.4f} mA/V')
print(f'  Intercept:      {intercept_i:.4f} mA')
print(f'  R²:             {r_i**2:.6f}')
print(f'  p-value:        {p_i:.2e}')
print()

# ---- Pearson Correlation ----
r_pv, p_pv = stats.pearsonr(bus_voltage, power_calc)
r_iv, p_iv = stats.pearsonr(bus_voltage, current_mA)
print('PEARSON CORRELATION:')
print(f'  Voltage-Power:   r = {r_pv:.4f}, p = {p_pv:.2e}')
print(f'  Voltage-Current: r = {r_iv:.4f}, p = {p_iv:.2e}')
print()

# ---- ANOVA across voltage bins ----
bin_edges = np.arange(np.floor(bus_voltage.min()), np.ceil(bus_voltage.max()) + 0.2, 0.2)
groups = []
for i in range(len(bin_edges) - 1):
    mask = (bus_voltage >= bin_edges[i]) & (bus_voltage < bin_edges[i + 1])
    if np.sum(mask) > 2:
        groups.append(power_calc[mask])

if len(groups) >= 2:
    f_stat, p_anova = stats.f_oneway(*groups)
    print('ONE-WAY ANOVA (power across 0.2V bins):')
    print(f'  F-statistic:    {f_stat:.4f}')
    print(f'  p-value:        {p_anova:.2e}')
    if p_anova < 0.05:
        print('  Result:         Significant difference in power across voltage bins')
    else:
        print('  Result:         No significant difference in power across voltage bins')

print('=' * 60)
print(f'Plot saved to discharge_analysis.png')
