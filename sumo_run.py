"""
Smart Traffic Management Framework and Logic Simulation
Controller: Direct-State 4-Way Controller with Anti-Deadlock Clearance & Instant Preemption
Calibrated for SUMO Left-Hand Traffic (LHT) Link Mapping: [0-3: SOUTH] [4-7: EAST] [8-11: NORTH] [12-15: WEST]
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk

# Verify SUMO_HOME path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

import traci

# Operational Constants
TLS_ID = "C"
MIN_GREEN = 15.0
MAX_GREEN = 60.0
YELLOW_TIME = 3.0
ALPHA_QUEUE = 2.0

# 16-character signal state strings calibrated to netconvert LHT link layout
# Verified Bit Blocks: [0-3: SOUTH] [4-7: EAST] [8-11: NORTH] [12-15: WEST]
STATES = {
    "NORTH": {
        "green":  "rrrr" + "rrrr" + "GGGG" + "rrrr",
        "yellow": "rrrr" + "rrrr" + "yyyy" + "rrrr",
        "edge": "N2C",
        "route_str": "r_N_straight",
        "route_lt":  "r_N_left",
        "route_rt":  "r_N_right"
    },
    "EAST": {
        "green":  "rrrr" + "GGGG" + "rrrr" + "rrrr",
        "yellow": "rrrr" + "yyyy" + "rrrr" + "rrrr",
        "edge": "E2C",
        "route_str": "r_E_straight",
        "route_lt":  "r_E_left",
        "route_rt":  "r_E_right"
    },
    "SOUTH": {
        "green":  "GGGG" + "rrrr" + "rrrr" + "rrrr",
        "yellow": "yyyy" + "rrrr" + "rrrr" + "rrrr",
        "edge": "S2C",
        "route_str": "r_S_straight",
        "route_lt":  "r_S_left",
        "route_rt":  "r_S_right"
    },
    "WEST": {
        "green":  "rrrr" + "rrrr" + "rrrr" + "GGGG",
        "yellow": "rrrr" + "rrrr" + "rrrr" + "yyyy",
        "edge": "W2C",
        "route_str": "r_W_straight",
        "route_lt":  "r_W_left",
        "route_rt":  "r_W_right"
    }
}

ORDER = ["NORTH", "EAST", "SOUTH", "WEST"]

# Global Preemption State Variables
amb_counter = 0
emergency_requested = False
target_corridor = None
active_ambulance_id = None
serviced_ambulances = set()


def inject_ambulance(corridor_key, route_type="straight"):
    """Dispatches an ambulance on the selected corridor and forces immediate preemption."""
    global amb_counter, emergency_requested, target_corridor, active_ambulance_id
    amb_counter += 1
    
    if route_type == "left":
        route_id = STATES[corridor_key]["route_lt"]
    elif route_type == "right":
        route_id = STATES[corridor_key]["route_rt"]
    else:
        route_id = STATES[corridor_key]["route_str"]

    amb_id = f"ambulance_{corridor_key[:1]}_{amb_counter}"
    try:
        traci.vehicle.add(
            vehID=amb_id,
            routeID=route_id,
            typeID="ambulance",
            depart="now",
            departLane="best",
            departSpeed="max"
        )
        traci.vehicle.setSpeedMode(amb_id, 31)
        
        target_corridor = corridor_key
        emergency_requested = True
        active_ambulance_id = amb_id
        print(f"\n🚨 [MANUAL DISPATCH] {amb_id} injected on {corridor_key} ({route_type}). Forcing Preemption.")
    except Exception as e:
        print(f"Error injecting ambulance: {e}")


def launch_dispatch_gui():
    """Tkinter control window for triggering emergency vehicles."""
    root = tk.Tk()
    root.title("Emergency Dispatch Panel")
    root.geometry("380x320")
    root.resizable(False, False)

    ttk.Label(root, text="Instant Preemption Controls", font=("Helvetica", 11, "bold")).pack(pady=8)

    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=5)

    ttk.Button(btn_frame, text="🚨 North (Straight)", command=lambda: inject_ambulance("NORTH", "straight")).grid(row=0, column=0, padx=5, pady=4)
    ttk.Button(btn_frame, text="North (Left)", command=lambda: inject_ambulance("NORTH", "left")).grid(row=0, column=1, padx=5, pady=4)

    ttk.Button(btn_frame, text="🚨 East (Straight)", command=lambda: inject_ambulance("EAST", "straight")).grid(row=1, column=0, padx=5, pady=4)
    ttk.Button(btn_frame, text="East (Right)", command=lambda: inject_ambulance("EAST", "right")).grid(row=1, column=1, padx=5, pady=4)

    ttk.Button(btn_frame, text="🚨 South (Straight)", command=lambda: inject_ambulance("SOUTH", "straight")).grid(row=2, column=0, padx=5, pady=4)
    ttk.Button(btn_frame, text="South (Left)", command=lambda: inject_ambulance("SOUTH", "left")).grid(row=2, column=1, padx=5, pady=4)

    ttk.Button(btn_frame, text="🚨 West (Straight)", command=lambda: inject_ambulance("WEST", "straight")).grid(row=3, column=0, padx=5, pady=4)
    ttk.Button(btn_frame, text="West (Right)", command=lambda: inject_ambulance("WEST", "right")).grid(row=3, column=1, padx=5, pady=4)

    ttk.Button(root, text="🔥 Dispatch All 4 Approaches", 
               command=lambda: [inject_ambulance(c, "straight") for c in ORDER]).pack(pady=10)
    root.mainloop()


def run_simulation():
    global emergency_requested, target_corridor, active_ambulance_id

    sumo_binary = "sumo-gui"
    config_path = os.path.join("sumo_sim", "intersection.sumocfg")
    
    cmd = [sumo_binary, "-c", config_path, "--start", "--quit-on-end"]
    traci.start(cmd)

    gui_thread = threading.Thread(target=launch_dispatch_gui, daemon=True)
    gui_thread.start()

    current_idx = 0
    current_corridor = ORDER[current_idx]
    
    # Initialize junction state
    traci.trafficlight.setRedYellowGreenState(TLS_ID, STATES[current_corridor]["green"])
    phase_start_time = 0.0
    in_yellow = False
    yellow_start_time = 0.0
    allocated_green = MIN_GREEN

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()

        # Step 1: Track if ambulance reached the junction center or exit edge
        if active_ambulance_id and active_ambulance_id in traci.vehicle.getIDList():
            road = traci.vehicle.getRoadID(active_ambulance_id)
            if road.startswith(":") or road.startswith("C2"):
                serviced_ambulances.add(active_ambulance_id)
                print(f"[{sim_time:.1f}s] [CLEARANCE] Ambulance cleared junction. Resuming standard cycles.")
                active_ambulance_id = None
                emergency_requested = False
                target_corridor = None

        # Step 2: Auto-detect scheduled or flowing ambulances across all corridors
        if not emergency_requested:
            for edge_id in ["N2C", "E2C", "S2C", "W2C"]:
                for v in traci.edge.getLastStepVehicleIDs(edge_id):
                    if traci.vehicle.getTypeID(v) == "ambulance" and v not in serviced_ambulances:
                        for c_name, c_data in STATES.items():
                            if c_data["edge"] == edge_id:
                                target_corridor = c_name
                                emergency_requested = True
                                active_ambulance_id = v
                                print(f"\n🚨 [AUTO-DETECT] Ambulance {v} detected on {c_name} approach. Initiating preemption.")
                                break
                    if emergency_requested:
                        break
                if emergency_requested:
                    break

        # Step 3: Handle Emergency Preemption Interrupt & Unblock Lead Vehicles
        if emergency_requested and target_corridor:
            target_edge = STATES[target_corridor]["edge"]
            for v in traci.edge.getLastStepVehicleIDs(target_edge):
                traci.vehicle.setSpeedMode(v, 31)
                traci.vehicle.setLaneChangeMode(v, 0)

            if current_corridor == target_corridor and not in_yellow:
                allocated_green = (sim_time - phase_start_time) + 20.0
            else:
                if not in_yellow:
                    in_yellow = True
                    yellow_start_time = sim_time
                    traci.trafficlight.setRedYellowGreenState(TLS_ID, STATES[current_corridor]["yellow"])
                    print(f"[{sim_time:.1f}s] [PREEMPTION CUT] {current_corridor} interrupted. Yellow clearance active.")

        # Step 4: Normal Dynamic Cycle, Anti-Starvation & Queue-Flow Acceleration
        if not in_yellow:
            active_edge = STATES[current_corridor]["edge"]
            
            # Smooth out queue flow so turning vehicles do not stall at yield points
            for v in traci.edge.getLastStepVehicleIDs(active_edge):
                traci.vehicle.setSpeedMode(v, 31)

            q = traci.edge.getLastStepHaltingNumber(active_edge)
            if not emergency_requested:
                allocated_green = min(MAX_GREEN, max(MIN_GREEN, MIN_GREEN + (ALPHA_QUEUE * q)))

            # If green period expires, transition to yellow
            if (sim_time - phase_start_time) >= allocated_green:
                in_yellow = True
                yellow_start_time = sim_time
                traci.trafficlight.setRedYellowGreenState(TLS_ID, STATES[current_corridor]["yellow"])

        else:
            # Yellow clearance interval
            if (sim_time - yellow_start_time) >= YELLOW_TIME:
                in_yellow = False
                phase_start_time = sim_time

                # Give immediate priority to preemption target
                if emergency_requested and target_corridor:
                    current_corridor = target_corridor
                    current_idx = ORDER.index(target_corridor)
                    allocated_green = 30.0
                    print(f"[{sim_time:.1f}s] [GREEN GRANTED] Emergency green active for: {current_corridor}")
                else:
                    # Sequential round-robin advance (N -> E -> S -> W)
                    current_idx = (current_idx + 1) % 4
                    current_corridor = ORDER[current_idx]

                traci.trafficlight.setRedYellowGreenState(TLS_ID, STATES[current_corridor]["green"])

    traci.close()


if __name__ == "__main__":
    run_simulation()