import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 5.5)
ax.axis('off')

box_style_open = dict(boxstyle="round,pad=0.5", fc="#F8D7DA", ec="#D9534F", lw=1.5)
box_style_closed = dict(boxstyle="round,pad=0.5", fc="#D1ECF1", ec="#0275D8", lw=1.5)
arrow_props = dict(arrowstyle="->", lw=1.5, color="#333333")
feedback_arrow = dict(arrowstyle="->", lw=1.8, color="#0275D8", connectionstyle="arc3,rad=-0.3")

ax.text(0.3, 4.8, "A. Traditional Open-Loop Control (Fixed-Time / Passive)", fontsize=11, fontweight="bold", color="#721C24")
ax.text(0.3, 2.5, "B. Closed-Loop Microscopic Feedback Control (Proposed)", fontsize=11, fontweight="bold", color="#0C5460")

ax.text(1.5, 3.8, "Pre-programmed\nCycle Timers", ha="center", va="center", bbox=box_style_open, fontsize=9.5)
ax.text(5.0, 3.8, "Static Phase Table\n(Fixed Green/Yellow)", ha="center", va="center", bbox=box_style_open, fontsize=9.5)
ax.text(8.5, 3.8, "Actuated Signal Head\n(No State Feedback)", ha="center", va="center", bbox=box_style_open, fontsize=9.5)

ax.annotate("", xy=(3.6, 3.8), xytext=(2.6, 3.8), arrowprops=arrow_props)
ax.annotate("", xy=(7.1, 3.8), xytext=(6.4, 3.8), arrowprops=arrow_props)

ax.text(1.5, 1.3, "SUMO Road Network\n& Edge Telemetry", ha="center", va="center", bbox=box_style_closed, fontsize=9.5)
ax.text(5.0, 1.3, "TraCI Python Engine\n(Density & Queue Check)", ha="center", va="center", bbox=box_style_closed, fontsize=9.5)
ax.text(8.5, 1.3, "Dynamic Phase & Preemption\nActuation (setPhase)", ha="center", va="center", bbox=box_style_closed, fontsize=9.5)

ax.annotate("", xy=(3.5, 1.3), xytext=(2.7, 1.3), arrowprops=arrow_props)
ax.annotate("", xy=(7.0, 1.3), xytext=(6.5, 1.3), arrowprops=arrow_props)

ax.annotate("Real-time State Feedback (TraCI Loop)", 
            xy=(1.5, 0.7), xytext=(8.5, 0.7),
            arrowprops=feedback_arrow, ha="center", va="top", fontsize=9, fontweight="bold", color="#0275D8")

plt.tight_layout()
plt.savefig("figure_2_1.png", dpi=300, bbox_inches='tight')
print("Successfully generated figure_2_1.png")
