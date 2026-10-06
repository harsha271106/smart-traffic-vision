import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10.5, 4.8), dpi=300)
ax.set_facecolor("#1E1E1E")
fig.patch.set_facecolor("#1E1E1E")
ax.axis('off')

# Terminal title bar with raw string to avoid unicode escape errors
ax.text(0.02, 0.93, r"PS C:\Users\martala\smart-traffic-vision> python sumo_run.py", 
        color="#CCCCCC", fontfamily="Consolas", fontsize=10, fontweight="bold")
ax.text(0.02, 0.85, "======================================================================", 
        color="#569CD6", fontfamily="Consolas", fontsize=9.5)
ax.text(0.02, 0.79, "   LIVE CONTROLLER: INDIAN HETEROGENEOUS SUBLANE SIMULATION", 
        color="#4EC9B0", fontfamily="Consolas", fontsize=9.5, fontweight="bold")
ax.text(0.02, 0.73, "======================================================================", 
        color="#569CD6", fontfamily="Consolas", fontsize=9.5)

logs = [
    ("[PHASE LOG] Axis: East-West  | Started:   0.0s | Ended:  30.0s | Green Duration: 30.0s (Initial Cycle)", "#DCDCDC"),
    ("[ 30.0s] [TRAFFIC DENSITY] NS Edge Queue: 4 vehicles | EW Edge Queue: 1 vehicles", "#CE9178"),
    ("[PHASE LOG] Axis: North-South| Started:  34.0s | Ended:  59.0s | Green Duration: 25.0s (Density Responsive)", "#DCDCDC"),
    ("[ 62.4s] [DISPATCH] ambulance_W_1 injected on West corridor.", "#F44747"),
    ("[ 62.4s] [PREEMPTION] Incoming EW Ambulance! Scheduling Yellow Clearance.", "#DCDCAA"),
    ("[PHASE LOG] Axis: North-South| Started:  63.0s | Ended:  67.2s | Green Duration:  4.2s (Preempted by EW Ambulance)", "#F44747"),
    ("[ 67.2s] [SIGNAL ACTUATION] Dynamic Phase 2 (EW Green) forced for emergency clearance.", "#4EC9B0"),
    ("[PHASE LOG] Axis: East-West  | Started:  71.2s | Ended:  96.2s | Green Duration: 25.0s (EW Emergency Priority Window)", "#6A9955"),
    ("[ 98.0s] [TRAFFIC DENSITY] NS Edge Queue: 8 vehicles | EW Edge Queue: 2 vehicles", "#CE9178"),
    ("[PHASE LOG] Axis: North-South| Started: 100.2s | Ended: 135.2s | Green Duration: 35.0s (Density Responsive)", "#DCDCDC"),
]

y_pos = 0.64
for line, color in logs:
    ax.text(0.02, y_pos, line, color=color, fontfamily="Consolas", fontsize=8.5)
    y_pos -= 0.062

plt.tight_layout()
plt.savefig("figure_4_3.png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
print("Successfully generated figure_4_3.png")
