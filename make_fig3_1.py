import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
ax.set_xlim(0, 11)
ax.set_ylim(0, 7)
ax.axis('off')

# Style palettes
box_sim = dict(boxstyle="round,pad=0.6", fc="#E8F4F8", ec="#2980B9", lw=2)
box_controller = dict(boxstyle="round,pad=0.6", fc="#EAFAF1", ec="#27AE60", lw=2)
box_ui = dict(boxstyle="round,pad=0.6", fc="#FDEDEC", ec="#E74C3C", lw=2)
box_inner = dict(boxstyle="square,pad=0.4", fc="#FFFFFF", ec="#BDC3C7", lw=1)

arrow_fw = dict(arrowstyle="->", lw=2, color="#2C3E50")
arrow_bw = dict(arrowstyle="->", lw=2, color="#8E44AD")
arrow_event = dict(arrowstyle="->", lw=1.8, color="#C0392B", linestyle="--")

# SUMO Simulation Server Block (Left)
ax.text(2.2, 4.0, "SUMO Microscopic Engine\n(TCP Server: Port 8813)", ha="center", va="center", bbox=box_sim, fontsize=10.5, fontweight="bold")
ax.text(2.2, 5.2, "Network Topology\n(intersection.net.xml)\nLHT Dual-Lane 0.5m Sublanes", ha="center", va="center", bbox=box_inner, fontsize=8.5)
ax.text(2.2, 2.6, "Heterogeneous Fleet\n(traffic.rou.xml)\nCars, Bikes, Autos, Buses", ha="center", va="center", bbox=box_inner, fontsize=8.5)

# Python TraCI Controller Core (Right)
ax.text(8.8, 4.0, "Python Controller Engine\n(TraCI Socket Client: sumo_run.py)", ha="center", va="center", bbox=box_controller, fontsize=10.5, fontweight="bold")
ax.text(8.8, 5.3, "Queue Length Engine\nHalting Count Metric\n(speed < 0.1 m/s)", ha="center", va="center", bbox=box_inner, fontsize=8.5)
ax.text(8.8, 2.7, "Adaptive Timing & Preemption\n15s Min | 60s Max Green\n4.0s Yellow Clearance FSM", ha="center", va="center", bbox=box_inner, fontsize=8.5)

# Tkinter UI Preemption Block (Top-Center)
ax.text(5.5, 6.2, "Operator Emergency Dispatch\n(Tkinter Daemon Thread)", ha="center", va="center", bbox=box_ui, fontsize=9.5, fontweight="bold")

# Channel / Data Stream Arrows
# Telemetry Stream (SUMO -> Python)
ax.annotate("", xy=(6.5, 4.4), xytext=(4.4, 4.4), arrowprops=arrow_fw)
ax.text(5.45, 4.65, "Telemetry Extraction\ngetLastStepHaltingNumber()\ngetLastStepVehicleIDs()", ha="center", va="bottom", fontsize=8.2, fontweight="semibold", color="#2C3E50")

# Command Stream (Python -> SUMO)
ax.annotate("", xy=(4.4, 3.4), xytext=(6.5, 3.4), arrowprops=arrow_bw)
ax.text(5.45, 3.15, "Signal Actuation Commands\ntraci.trafficlight.setPhase()\nvehicle.add(ambulance)", ha="center", va="top", fontsize=8.2, fontweight="semibold", color="#8E44AD")

# Preemption dispatch event to TraCI
ax.annotate("", xy=(7.2, 4.8), xytext=(6.6, 5.7), arrowprops=arrow_event)
ax.text(7.3, 5.5, "Asynchronous\nAmbulance Event", ha="left", va="center", fontsize=8, color="#C0392B", fontweight="bold")

plt.tight_layout()
plt.savefig("figure_3_1.png", dpi=300, bbox_inches='tight')
print("Successfully generated figure_3_1.png")
