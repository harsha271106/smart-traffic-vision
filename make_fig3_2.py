import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.5)
ax.axis('off')

# Style configurations
box_green = dict(boxstyle="round,pad=0.5", fc="#D4EDDA", ec="#28A745", lw=2)
box_yellow = dict(boxstyle="round,pad=0.5", fc="#FFF3CD", ec="#FFC107", lw=2)
box_preempt = dict(boxstyle="round,pad=0.5", fc="#F8D7DA", ec="#DC3545", lw=2)

arrow_norm = dict(arrowstyle="->", lw=1.8, color="#2C3E50")
arrow_preempt = dict(arrowstyle="->", lw=1.8, color="#DC3545", linestyle="--")

# FSM Phase States (Nodes)
# State 0: NS Green (Top Left)
ax.text(2.2, 5.0, "State 0: NS Green\n(Active Green: 15s - 60s)\nAdaptive Queue Scaling", 
        ha="center", va="center", bbox=box_green, fontsize=9.5, fontweight="bold")

# State 1: NS Yellow (Top Right)
ax.text(7.8, 5.0, "State 1: NS Yellow\n(Fixed Clearance: 4.0s)\nStop-line Deceleration", 
        ha="center", va="center", bbox=box_yellow, fontsize=9.5, fontweight="bold")

# State 2: EW Green (Bottom Right)
ax.text(7.8, 1.8, "State 2: EW Green\n(Active Green: 15s - 60s)\nAdaptive Queue Scaling", 
        ha="center", va="center", bbox=box_green, fontsize=9.5, fontweight="bold")

# State 3: EW Yellow (Bottom Left)
ax.text(2.2, 1.8, "State 3: EW Yellow\n(Fixed Clearance: 4.0s)\nStop-line Deceleration", 
        ha="center", va="center", bbox=box_yellow, fontsize=9.5, fontweight="bold")

# Central Emergency Preemption Node
ax.text(5.0, 3.4, "Emergency Preemption Logic\nImmediate 4.0s Clearance Override\n(Ambulance Priority Corridor)", 
        ha="center", va="center", bbox=box_preempt, fontsize=9, fontweight="bold")

# Standard Round-Robin State Transitions
# State 0 -> State 1
ax.annotate("", xy=(6.3, 5.2), xytext=(3.7, 5.2), arrowprops=arrow_norm)
ax.text(5.0, 5.4, "Timer Expiry / Density Capped", ha="center", va="bottom", fontsize=8, color="#2C3E50")

# State 1 -> State 2
ax.annotate("", xy=(7.8, 2.6), xytext=(7.8, 4.2), arrowprops=arrow_norm)
ax.text(8.0, 3.4, "t >= 4.0s Clearance", ha="left", va="center", fontsize=8, color="#2C3E50")

# State 2 -> State 3
ax.annotate("", xy=(3.7, 1.6), xytext=(6.3, 1.6), arrowprops=arrow_norm)
ax.text(5.0, 1.35, "Timer Expiry / Density Capped", ha="center", va="top", fontsize=8, color="#2C3E50")

# State 3 -> State 0
ax.annotate("", xy=(2.2, 4.2), xytext=(2.2, 2.6), arrowprops=arrow_norm)
ax.text(2.0, 3.4, "t >= 4.0s Clearance", ha="right", va="center", fontsize=8, color="#2C3E50")

# Preemption Overrides
# Trigger from NS Green during EW ambulance
ax.annotate("", xy=(4.6, 3.9), xytext=(3.4, 4.4), arrowprops=arrow_preempt)
# Trigger from EW Green during NS ambulance
ax.annotate("", xy=(5.4, 2.9), xytext=(6.6, 2.4), arrowprops=arrow_preempt)

plt.tight_layout()
plt.savefig("figure_3_2.png", dpi=300, bbox_inches='tight')
print("Successfully generated figure_3_2.png")
