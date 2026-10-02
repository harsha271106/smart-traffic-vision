import os
import sys
import random
import threading
import tkinter as tk

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Error: SUMO_HOME environment variable is not defined.")

import traci

SUMO_BINARY = "sumo-gui"
SUMO_CONFIG = "sumo_sim/intersection.sumocfg"
if not os.path.exists(SUMO_CONFIG):
    SUMO_CONFIG = "intersection.sumocfg"

TL_ID = "center"
PHASE_NS_GREEN = 0
PHASE_NS_YELLOW = 1
PHASE_EW_GREEN = 2
PHASE_EW_YELLOW = 3

YELLOW_TIME = 4.0
MIN_GREEN = 15.0
MAX_GREEN = 60.0

dispatch_queue = []

def launch_dispatch_ui():
    root = tk.Tk()
    root.title("Emergency Dispatch Panel")
    root.geometry("300x340")
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    tk.Label(root, text="EMERGENCY DISPATCH", font=("Arial", 11, "bold")).pack(pady=10)
    tk.Label(root, text="Inject priority ambulance:", font=("Arial", 9)).pack(pady=2)

    def trigger(corridor):
        dispatch_queue.append(corridor)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Dispatch North (N)", width=20, bg="#d9534f", fg="white", font=("Arial", 9, "bold"),
              command=lambda: trigger("N")).pack(pady=4)
    tk.Button(btn_frame, text="Dispatch South (S)", width=20, bg="#d9534f", fg="white", font=("Arial", 9, "bold"),
              command=lambda: trigger("S")).pack(pady=4)
    tk.Button(btn_frame, text="Dispatch East (E)", width=20, bg="#d9534f", fg="white", font=("Arial", 9, "bold"),
              command=lambda: trigger("E")).pack(pady=4)
    tk.Button(btn_frame, text="Dispatch West (W)", width=20, bg="#d9534f", fg="white", font=("Arial", 9, "bold"),
              command=lambda: trigger("W")).pack(pady=4)
    tk.Button(btn_frame, text="Dispatch All 4 Ways", width=20, bg="#c9302c", fg="white", font=("Arial", 9, "bold"),
              command=lambda: trigger("ALL")).pack(pady=6)

    root.mainloop()

def log_phase(axis_name, start_t, end_t, reason):
    dur = end_t - start_t
    print(f"[PHASE LOG] Axis: {axis_name:<10} | Started: {start_t:5.1f}s | Ended: {end_t:5.1f}s | Green Duration: {dur:4.1f}s ({reason})")

def run():
    ui_thread = threading.Thread(target=launch_dispatch_ui, daemon=True)
    ui_thread.start()

    traci.start([SUMO_BINARY, "-c", SUMO_CONFIG, "--lateral-resolution", "0.5", "--start"])

    print("\n" + "=" * 70)
    print("   LIVE CONTROLLER: INDIAN HETEROGENEOUS SUBLANE SIMULATION")
    print("=" * 70 + "\n")

    step = 0
    veh_counter = 0
    amb_counter = 0

    current_phase = PHASE_EW_GREEN
    traci.trafficlight.setPhase(TL_ID, current_phase)
    phase_start_time = 0.0
    allocated_green = 30.0
    in_yellow = False
    yellow_start_time = 0.0
    target_green_phase = PHASE_EW_GREEN
    active_preemption = False
    reason_label = "Initial Cycle"

    routes = {"N": "r_N", "S": "r_S", "E": "r_E", "W": "r_W"}

    for _ in range(36000):
        traci.simulationStep()
        step += 1
        sim_time = traci.simulation.getTime()

        while dispatch_queue:
            req = dispatch_queue.pop(0)
            targets = ["N", "S", "E", "W"] if req == "ALL" else [req]
            for direction in targets:
                amb_counter += 1
                amb_id = f"ambulance_{direction}_{amb_counter}"
                try:
                    traci.vehicle.add(amb_id, routes[direction], typeID="ambulance", depart="now")
                    traci.vehicle.setColor(amb_id, (255, 0, 0, 255))
                    lat_pos = random.choice([-0.8, -0.4, 0.0, 0.4, 0.8])
                    traci.vehicle.setLateralLanePosition(amb_id, lat_pos)
                    print(f"[{sim_time:5.1f}s] [DISPATCH] {amb_id} injected on {direction} corridor.")
                except Exception as e:
                    print(f"[ERROR adding ambulance]: {e}")

        # Inject mixed traffic every 6 steps (~0.6 seconds)
        if step % 6 == 0:
            veh_counter += 1
            v_type = random.choices(["bike", "auto", "car", "bus"], weights=[0.55, 0.25, 0.15, 0.05])[0]
            r = random.choice(["N", "S", "E", "W"])
            veh_id = f"veh_{veh_counter}"
            try:
                # Spawn across lanes 0 and 1
                lane_idx = random.choice([0, 1])
                traci.vehicle.add(veh_id, routes[r], typeID=v_type, depart="now", departLane=str(lane_idx))
                # Squeeze vehicle laterally to create multi-vehicle abreast formation
                lat_pos = random.choice([-0.9, -0.5, 0.0, 0.5, 0.9]) if v_type in ["bike", "auto"] else 0.0
                traci.vehicle.setLateralLanePosition(veh_id, lat_pos)
            except Exception:
                pass

        ns_amb = any(traci.vehicle.getTypeID(v) == "ambulance" for edge in ["N2C", "S2C"] for v in traci.edge.getLastStepVehicleIDs(edge))
        ew_amb = any(traci.vehicle.getTypeID(v) == "ambulance" for edge in ["E2C", "W2C"] for v in traci.edge.getLastStepVehicleIDs(edge))

        ns_q = traci.edge.getLastStepHaltingNumber("N2C") + traci.edge.getLastStepHaltingNumber("S2C")
        ew_q = traci.edge.getLastStepHaltingNumber("E2C") + traci.edge.getLastStepHaltingNumber("W2C")

        if (ns_amb or ew_amb) and not in_yellow:
            if ns_amb and current_phase == PHASE_EW_GREEN:
                print(f"[{sim_time:5.1f}s] [PREEMPTION] Incoming NS Ambulance! Scheduling Yellow Clearance.")
                in_yellow = True
                yellow_start_time = sim_time
                target_green_phase = PHASE_NS_GREEN
                traci.trafficlight.setPhase(TL_ID, PHASE_EW_YELLOW)
                current_phase = PHASE_EW_YELLOW
                log_phase("East-West", phase_start_time, sim_time, "Preempted by NS Ambulance")
                active_preemption = True
                reason_label = "NS Emergency Priority Window"

            elif ew_amb and current_phase == PHASE_NS_GREEN:
                print(f"[{sim_time:5.1f}s] [PREEMPTION] Incoming EW Ambulance! Scheduling Yellow Clearance.")
                in_yellow = True
                yellow_start_time = sim_time
                target_green_phase = PHASE_EW_GREEN
                traci.trafficlight.setPhase(TL_ID, PHASE_NS_YELLOW)
                current_phase = PHASE_NS_YELLOW
                log_phase("North-South", phase_start_time, sim_time, "Preempted by EW Ambulance")
                active_preemption = True
                reason_label = "EW Emergency Priority Window"

            elif (ns_amb and current_phase == PHASE_NS_GREEN) or (ew_amb and current_phase == PHASE_EW_GREEN):
                allocated_green = max(allocated_green, (sim_time - phase_start_time) + 20.0)

        if in_yellow:
            if sim_time - yellow_start_time >= YELLOW_TIME:
                in_yellow = False
                current_phase = target_green_phase
                traci.trafficlight.setPhase(TL_ID, current_phase)
                phase_start_time = sim_time
                if active_preemption:
                    allocated_green = 25.0
                    active_preemption = False
                else:
                    q = ns_q if current_phase == PHASE_NS_GREEN else ew_q
                    allocated_green = min(MAX_GREEN, max(MIN_GREEN, 15.0 + (2.5 * q)))
                    reason_label = f"Density Responsive (Queue: {q})"
        else:
            if sim_time - phase_start_time >= allocated_green:
                in_yellow = True
                yellow_start_time = sim_time
                if current_phase == PHASE_NS_GREEN:
                    traci.trafficlight.setPhase(TL_ID, PHASE_NS_YELLOW)
                    target_green_phase = PHASE_EW_GREEN
                    log_phase("North-South", phase_start_time, sim_time, reason_label)
                else:
                    traci.trafficlight.setPhase(TL_ID, PHASE_EW_YELLOW)
                    target_green_phase = PHASE_NS_GREEN
                    log_phase("East-West", phase_start_time, sim_time, reason_label)
                current_phase = current_phase + 1

    traci.close()

if __name__ == "__main__":
    run()
