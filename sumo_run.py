import os
import sys
import time
import random
import threading
import queue
import tkinter as tk

if 'SUMO_HOME' not in os.environ:
    possible_paths = [
        r"C:\Program Files (x86)\Eclipse\Sumo",
        r"C:\Program Files\Eclipse\Sumo",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Eclipse\Sumo")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            os.environ['SUMO_HOME'] = p
            break

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    if tools not in sys.path:
        sys.path.append(tools)
else:
    sys.exit("Error: SUMO_HOME could not be found.")

import traci
import sumolib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUMO_CONFIG = os.path.join(BASE_DIR, "sumo_sim", "intersection.sumocfg")
SUMO_BINARY = sumolib.checkBinary("sumo-gui")
TL_ID = "center"

STANDARD_GREEN_DURATION = 30.0
YELLOW_DURATION = 4.0
EMERGENCY_CLEARANCE_WINDOW = 20.0

EDGE_MAP = {
    "N": {"edge": "N2C", "route": "r_N", "axis": "NS", "name": "North"},
    "S": {"edge": "S2C", "route": "r_S", "axis": "NS", "name": "South"},
    "E": {"edge": "E2C", "route": "r_E", "axis": "EW", "name": "East"},
    "W": {"edge": "W2C", "route": "r_W", "axis": "EW", "name": "West"},
}

ambulance_queue = queue.Queue()

def launch_control_panel():
    root = tk.Tk()
    root.title("Emergency Dispatch Panel")
    root.geometry("300x260+50+50")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    lbl = tk.Label(root, text="Dispatch Ambulance From:", font=("Segoe UI", 10, "bold"))
    lbl.pack(pady=6)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=4)

    def dispatch(direction):
        ambulance_queue.put(direction)

    btn_n = tk.Button(btn_frame, text="? NORTH", bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), width=12, command=lambda: dispatch("N"))
    btn_n.grid(row=0, column=0, columnspan=2, pady=3)

    btn_w = tk.Button(btn_frame, text="? WEST", bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), width=10, command=lambda: dispatch("W"))
    btn_w.grid(row=1, column=0, padx=4, pady=3)

    btn_e = tk.Button(btn_frame, text="EAST ?", bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), width=10, command=lambda: dispatch("E"))
    btn_e.grid(row=1, column=1, padx=4, pady=3)

    btn_s = tk.Button(btn_frame, text="? SOUTH", bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), width=12, command=lambda: dispatch("S"))
    btn_s.grid(row=2, column=0, columnspan=2, pady=3)

    def dispatch_all():
        for d in ["N", "S", "E", "W"]:
            ambulance_queue.put(d)

    btn_all = tk.Button(root, text="DISPATCH ALL 4 WAYS", bg="#7B1FA2", fg="white", font=("Segoe UI", 9, "bold"), padx=8, pady=4, command=dispatch_all)
    btn_all.pack(pady=8)

    root.mainloop()

def log_green_phase(axis_name, start_time, end_time, reason="Standard Cycle"):
    duration = end_time - start_time
    print(f"\n[PHASE LOG] ?? Axis: {axis_name:<11} | Started: {start_time:>5.1f}s | Ended: {end_time:>5.1f}s | Green Duration: {duration:>5.1f}s ({reason})")

def run():
    print(f"Loading config: {SUMO_CONFIG}")
    traci.start([
        SUMO_BINARY, 
        "-c", SUMO_CONFIG, 
        "--start", 
        "--delay", "90",
        "--lateral-resolution", "0.5"
    ])
    
    try:
        traci.gui.setOffset("View #0", 0.0, 0.0)
        traci.gui.setZoom("View #0", 250.0)
    except Exception:
        pass

    logic = traci.trafficlight.getAllProgramLogics(TL_ID)[0]
    total_phases = len(logic.phases)
    controlled_links = traci.trafficlight.getControlledLinks(TL_ID)
    
    ns_green_phase = None
    ew_green_phase = None
    ns_yellow_phase = None
    ew_yellow_phase = None

    for p_idx, phase in enumerate(logic.phases):
        state = phase.state.upper()
        has_ns_green = False
        has_ew_green = False
        for link_idx, links in enumerate(controlled_links):
            if link_idx < len(state) and state[link_idx] in ['G', 'Y']:
                for incoming, outgoing, _ in links:
                    if "S2C" in incoming or "N2C" in incoming:
                        if state[link_idx] == 'G': has_ns_green = True
                    if "E2C" in incoming or "W2C" in incoming:
                        if state[link_idx] == 'G': has_ew_green = True
        
        if 'Y' in state:
            if has_ns_green or ('Y' in [state[i] for i, links in enumerate(controlled_links) if any("S2C" in l[0] or "N2C" in l[0] for l in links)]):
                if ns_yellow_phase is None: ns_yellow_phase = p_idx
            else:
                if ew_yellow_phase is None: ew_yellow_phase = p_idx
        else:
            if has_ns_green and not has_ew_green:
                ns_green_phase = p_idx
            elif has_ew_green and not has_ns_green:
                ew_green_phase = p_idx

    if ns_green_phase is None: ns_green_phase = 0
    if ns_yellow_phase is None: ns_yellow_phase = (ns_green_phase + 1) % total_phases
    if ew_green_phase is None: ew_green_phase = (ns_yellow_phase + 1) % total_phases
    if ew_yellow_phase is None: ew_yellow_phase = (ew_green_phase + 1) % total_phases

    current_phase = ew_green_phase
    current_axis = "EW"
    phase_start_time = 0.0
    phase_end_time = STANDARD_GREEN_DURATION
    phase_reason = "Initial Cycle"
    traci.trafficlight.setPhase(TL_ID, current_phase)

    step = 0
    veh_counter = 0
    amb_counter = 0

    # Seed initial vehicles
    for r in ["r_S", "r_N", "r_W", "r_E"]:
        for _ in range(2):
            veh_counter += 1
            v_type = random.choice(["car", "bike", "auto"])
            try:
                traci.vehicle.add(f"init_{veh_counter}", r, typeID=v_type, depart="now", departLane="best", departSpeed="max")
            except Exception:
                pass

    print("\n" + "=" * 80)
    print(f" {'LIVE SIGNAL CONTROLLER & GREEN DURATION LOGGER':^78} ")
    print("=" * 80 + "\n")

    while traci.simulation.getTime() < 3600:
        traci.simulationStep()
        step += 1
        sim_time = traci.simulation.getTime()

        # Handle UI spawns
        while not ambulance_queue.empty():
            direction = ambulance_queue.get()
            amb_counter += 1
            amb_id = f"ambulance_{direction}_{amb_counter}"
            route_id = EDGE_MAP[direction]["route"]
            try:
                traci.vehicle.add(
                    vehID=amb_id,
                    routeID=route_id,
                    typeID="ambulance",
                    depart="now",
                    departLane="best",
                    departSpeed="max"
                )
                print(f"[{sim_time:5.1f}s] [DISPATCH] {amb_id} on {EDGE_MAP[direction]['name']} road.")
            except Exception as e:
                pass

        # Spawn normal vehicles regularly
        if step % 3 == 0:
            veh_counter += 1
            v_type = random.choices(["bike", "auto", "car", "bus"], weights=[0.50, 0.25, 0.18, 0.07])[0]
            route = random.choice(["r_S", "r_N", "r_W", "r_E"])
            try:
                traci.vehicle.add(
                    vehID=f"veh_{veh_counter}", 
                    routeID=route, 
                    typeID=v_type, 
                    depart="now", 
                    departLane="best",
                    departSpeed="max"
                )
            except Exception:
                pass

        # Emergency vehicle monitoring
        active_ns_ambulances = []
        active_ew_ambulances = []

        for veh_id in traci.edge.getLastStepVehicleIDs("N2C") + traci.edge.getLastStepVehicleIDs("S2C"):
            if traci.vehicle.getTypeID(veh_id) == "ambulance":
                active_ns_ambulances.append(veh_id)

        for veh_id in traci.edge.getLastStepVehicleIDs("E2C") + traci.edge.getLastStepVehicleIDs("W2C"):
            if traci.vehicle.getTypeID(veh_id) == "ambulance":
                active_ew_ambulances.append(veh_id)

        has_ns_amb = len(active_ns_ambulances) > 0
        has_ew_amb = len(active_ew_ambulances) > 0

        # Multi-Ambulance Priority Arbitration Logic
        if has_ns_amb and has_ew_amb:
            if sim_time >= phase_end_time:
                if current_axis == "NS":
                    if current_phase == ns_green_phase:
                        log_green_phase("North-South", phase_start_time, sim_time, phase_reason)
                        traci.trafficlight.setPhase(TL_ID, ns_yellow_phase)
                        current_phase = ns_yellow_phase
                        phase_end_time = sim_time + YELLOW_DURATION
                    elif current_phase == ns_yellow_phase:
                        traci.trafficlight.setPhase(TL_ID, ew_green_phase)
                        current_phase = ew_green_phase
                        current_axis = "EW"
                        phase_start_time = sim_time
                        phase_end_time = sim_time + EMERGENCY_CLEARANCE_WINDOW
                        phase_reason = "4-Way Emergency (EW Axis)"
                        print(f"[{sim_time:5.1f}s] [4-WAY ARBITRATION] Switch to EW Axis Priority.")
                else:
                    if current_phase == ew_green_phase:
                        log_green_phase("East-West", phase_start_time, sim_time, phase_reason)
                        traci.trafficlight.setPhase(TL_ID, ew_yellow_phase)
                        current_phase = ew_yellow_phase
                        phase_end_time = sim_time + YELLOW_DURATION
                    elif current_phase == ew_yellow_phase:
                        traci.trafficlight.setPhase(TL_ID, ns_green_phase)
                        current_phase = ns_green_phase
                        current_axis = "NS"
                        phase_start_time = sim_time
                        phase_end_time = sim_time + EMERGENCY_CLEARANCE_WINDOW
                        phase_reason = "4-Way Emergency (NS Axis)"
                        print(f"[{sim_time:5.1f}s] [4-WAY ARBITRATION] Switch to NS Axis Priority.")

        elif has_ns_amb and not has_ew_amb:
            if current_axis != "NS":
                if current_phase == ew_green_phase:
                    log_green_phase("East-West", phase_start_time, sim_time, phase_reason)
                    traci.trafficlight.setPhase(TL_ID, ew_yellow_phase)
                    current_phase = ew_yellow_phase
                    phase_end_time = sim_time + YELLOW_DURATION
                elif current_phase == ew_yellow_phase and sim_time >= phase_end_time:
                    traci.trafficlight.setPhase(TL_ID, ns_green_phase)
                    current_phase = ns_green_phase
                    current_axis = "NS"
                    phase_start_time = sim_time
                    phase_end_time = sim_time + EMERGENCY_CLEARANCE_WINDOW
                    phase_reason = "NS Emergency Preemption"
                    print(f"[{sim_time:5.1f}s] [PREEMPTION] Switched to NS Green for incoming NS emergency.")
            else:
                if sim_time >= phase_end_time - 2.0:
                    phase_end_time = sim_time + EMERGENCY_CLEARANCE_WINDOW
                    phase_reason = "NS Green Extended (Emergency)"

        elif has_ew_amb and not has_ns_amb:
            if current_axis != "EW":
                if current_phase == ns_green_phase:
                    log_green_phase("North-South", phase_start_time, sim_time, phase_reason)
                    traci.trafficlight.setPhase(TL_ID, ns_yellow_phase)
                    current_phase = ns_yellow_phase
                    phase_end_time = sim_time + YELLOW_DURATION
                elif current_phase == ns_yellow_phase and sim_time >= phase_end_time:
                    traci.trafficlight.setPhase(TL_ID, ew_green_phase)
                    current_phase = ew_green_phase
                    current_axis = "EW"
                    phase_start_time = sim_time
                    phase_end_time = sim_time + EMERGENCY_CLEARANCE_WINDOW
                    phase_reason = "EW Emergency Preemption"
                    print(f"[{sim_time:5.1f}s] [PREEMPTION] Switched to EW Green for incoming EW emergency.")
            else:
                if sim_time >= phase_end_time - 2.0:
                    phase_end_time = sim_time + EMERGENCY_CLEARANCE_WINDOW
                    phase_reason = "EW Green Extended (Emergency)"

        else:
            # Normal Signal Cycle
            if sim_time >= phase_end_time:
                if current_phase == ns_green_phase:
                    log_green_phase("North-South", phase_start_time, sim_time, phase_reason)
                    traci.trafficlight.setPhase(TL_ID, ns_yellow_phase)
                    current_phase = ns_yellow_phase
                    phase_end_time = sim_time + YELLOW_DURATION
                elif current_phase == ns_yellow_phase:
                    traci.trafficlight.setPhase(TL_ID, ew_green_phase)
                    current_phase = ew_green_phase
                    current_axis = "EW"
                    phase_start_time = sim_time
                    phase_end_time = sim_time + STANDARD_GREEN_DURATION
                    phase_reason = "Normal Fixed/Density Cycle"
                elif current_phase == ew_green_phase:
                    log_green_phase("East-West", phase_start_time, sim_time, phase_reason)
                    traci.trafficlight.setPhase(TL_ID, ew_yellow_phase)
                    current_phase = ew_yellow_phase
                    phase_end_time = sim_time + YELLOW_DURATION
                elif current_phase == ew_yellow_phase:
                    traci.trafficlight.setPhase(TL_ID, ns_green_phase)
                    current_phase = ns_green_phase
                    current_axis = "NS"
                    phase_start_time = sim_time
                    phase_end_time = sim_time + STANDARD_GREEN_DURATION
                    phase_reason = "Normal Fixed/Density Cycle"

    traci.close()

if __name__ == "__main__":
    ui_thread = threading.Thread(target=launch_control_panel, daemon=True)
    ui_thread.start()
    run()
