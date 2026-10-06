import matplotlib.pyplot as plt
import numpy as np

# Simulation distance along corridor approaching stop line (meters from entry to junction)
distance = np.linspace(0, 300, 100)

# Velocity profile: Fixed-time vs Preemption (m/s)
speed_fixed = np.where(distance < 180, 13.8 - (distance/30), 
               np.where(distance < 260, 0.5, 12.0 * (1 - np.exp(-(distance-260)/15))))
speed_fixed = np.clip(speed_fixed, 0.0, 13.8)

# Under preemption, queue flushes early; velocity stays near free-flow (>= 11 m/s)
speed_adaptive = 13.8 - 2.2 * np.exp(-((distance - 240) / 40)**2)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)

# Subplot 1: Velocity vs Approach Distance
ax1.plot(distance, speed_fixed * 3.6, color='#D9534F', lw=2.2, linestyle='--', label='Fixed-Time Control')
ax1.plot(distance, speed_adaptive * 3.6, color='#0275D8', lw=2.4, label='Adaptive Preemption (TraCI)')
ax1.axvline(x=250, color='#666666', linestyle=':', label='Stop Bar Line')
ax1.set_xlabel('Approach Distance along Corridor (m)', fontsize=10, fontweight='bold')
ax1.set_ylabel('Vehicle Velocity (km/h)', fontsize=10, fontweight='bold')
ax1.set_title('Instantaneous Corridor Speed', fontsize=11, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.5)
ax1.legend(loc='lower left', fontsize=8.5)

# Subplot 2: Delay Comparison Bar Chart
metrics = ['Queue Waiting Delay', 'Total Corridor Transit Time']
fixed_metrics = [38.4, 61.2]
adaptive_metrics = [4.1, 26.5]

x = np.arange(len(metrics))
width = 0.32

rects1 = ax2.bar(x - width/2, fixed_metrics, width, label='Fixed-Time', color='#D9534F')
rects2 = ax2.bar(x + width/2, adaptive_metrics, width, label='Adaptive Preemption', color='#28A745')

ax2.set_ylabel('Time (seconds)', fontsize=10, fontweight='bold')
ax2.set_title('Transit Delay Reduction', fontsize=11, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(metrics, fontsize=9.5, fontweight='bold')
ax2.grid(True, axis='y', linestyle='--', alpha=0.5)
ax2.legend(fontsize=8.5)

for rect in rects1:
    h = rect.get_height()
    ax2.annotate(f'{h:.1f}s', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

for rect in rects2:
    h = rect.get_height()
    ax2.annotate(f'{h:.1f}s', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

plt.tight_layout()
plt.savefig("figure_4_2.png", dpi=300, bbox_inches='tight')
print("Successfully generated figure_4_2.png")
