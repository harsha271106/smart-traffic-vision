import time
import threading
import tkinter as tk
from tkinter import scrolledtext
import cv2
import numpy as np
from PIL import Image, ImageTk
from ultralytics import YOLO

from intersection_manager import process_lane_roi
from traffic_emulator import TrafficSimulator

class SmartTrafficGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Traffic Vision - 4-Way Control Dashboard")
        self.root.geometry("1120x700")
        self.root.configure(bg="#1e1e1e")

        self.is_running = False
        self.active_sim = None
        self.yolo_model = YOLO("yolov8n.pt")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        title_frame = tk.Frame(self.root, bg="#0d1117", height=50)
        title_frame.pack(fill=tk.X)
        title_label = tk.Label(
            title_frame, 
            text="ADAPTIVE 4-WAY TRAFFIC CONTROL SYSTEM (LHD)", 
            font=("Helvetica", 16, "bold"), 
            fg="#58a6ff", 
            bg="#0d1117"
        )
        title_label.pack(pady=10)

        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.video_label = tk.Label(main_frame, bg="black", text="Simulation Offline", fg="white", font=("Helvetica", 12))
        self.video_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        right_panel = tk.Frame(main_frame, bg="#2d2d2d", width=340)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)

        ctrl_label = tk.Label(right_panel, text="System Controls", font=("Helvetica", 12, "bold"), fg="white", bg="#2d2d2d")
        ctrl_label.pack(pady=(10, 5))

        self.start_btn = tk.Button(right_panel, text="▶ Start Simulation", font=("Helvetica", 10, "bold"), bg="#238636", fg="white", command=self.start_sim, width=22, height=2)
        self.start_btn.pack(pady=4)

        self.stop_btn = tk.Button(right_panel, text="⏹ Stop Simulation", font=("Helvetica", 10, "bold"), bg="#da3633", fg="white", command=self.stop_sim, state=tk.DISABLED, width=22, height=2)
        self.stop_btn.pack(pady=4)

        self.emg_btn = tk.Button(right_panel, text="🚨 Spawn Emergency Vehicle", font=("Helvetica", 9, "bold"), bg="#d97706", fg="white", command=self.trigger_emergency, width=22, height=2)
        self.emg_btn.pack(pady=6)

        sig_label = tk.Label(right_panel, text="Corridor Status", font=("Helvetica", 11, "bold"), fg="white", bg="#2d2d2d")
        sig_label.pack(pady=(10, 2))

        self.c_signal = tk.Canvas(right_panel, width=50, height=50, bg="#2d2d2d", highlightthickness=0)
        self.c_signal.pack(pady=2)
        self.signal_circle = self.c_signal.create_oval(5, 5, 45, 45, fill="#da3633")

        self.timer_label = tk.Label(right_panel, text="Timer: Idle", font=("Helvetica", 11, "bold"), fg="#e3b341", bg="#2d2d2d")
        self.timer_label.pack(pady=2)

        log_label = tk.Label(right_panel, text="Real-Time Event Logs", font=("Helvetica", 11, "bold"), fg="white", bg="#2d2d2d")
        log_label.pack(pady=(10, 2))

        self.log_area = scrolledtext.ScrolledText(right_panel, width=38, height=14, font=("Consolas", 8), bg="#0d1117", fg="#7ee787")
        self.log_area.pack(pady=5, padx=5)

        self.log("4-Way Intersection System ready.")

    def log(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_area.see(tk.END)

    def set_signal_light(self, is_green):
        color = "#238636" if is_green else "#da3633"
        self.c_signal.itemconfig(self.signal_circle, fill=color)

    def set_timer_text(self, text):
        self.timer_label.config(text=text)

    def trigger_emergency(self):
        if self.active_sim and self.is_running:
            self.active_sim.trigger_emergency()
            self.log("EVENT: Ambulance spawned on South approach!")
        else:
            self.log("Notice: Click Start Simulation first.")

    def start_sim(self):
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("Adaptive 4-way traffic loop active...")
        threading.Thread(target=self.run_video_loop, daemon=True).start()

    def stop_sim(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("Simulation stopped by user.")

    def on_close(self):
        self.is_running = False
        self.root.destroy()

    def run_video_loop(self):
        self.active_sim = TrafficSimulator(width=640, height=360)
        subtractor = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False)

        # EXACT INDIAN LEFT-HAND DRIVE CORRIDOR BOXES:
        corridor_rois = {
            # South: Left lane going UP (x: 270 to 320, y: 240 to 350)
            'S': [[270, 240], [320, 240], [320, 350], [270, 350]],
            
            # North: Left lane going DOWN (x: 320 to 370, y: 10 to 120)
            'N': [[320, 10],  [370, 10],  [370, 120], [320, 120]],
            
            # West Approach (Coming from West moving East -> BOTTOM Lane: y from 180 to 230, right before stop line x=264)
            'W_side': [[145, 180], [260, 180], [260, 230], [145, 230]],
            
            # East Approach (Coming from East moving West -> TOP Lane: y from 130 to 180, right before stop line x=376)
            'E_side': [[380, 130], [495, 130], [495, 180], [380, 180]]
        }

        is_green = False
        green_until_time = 0.0
        last_logged_state = None

        try:
            while self.is_running:
                frame = self.active_sim.render()
                
                # Monitor South Corridor
                density, emergency = process_lane_roi(frame, corridor_rois['S'], subtractor, self.yolo_model)
                current_time = time.time()

                # 60s Locked Green Phase Logic
                if emergency:
                    is_green = True
                    green_until_time = 0.0
                    if last_logged_state != "EMERGENCY":
                        self.root.after(0, self.log, "ALERT: Ambulance strobe detected! EMERGENCY OVERRIDE.")
                        last_logged_state = "EMERGENCY"
                    timer_str = "EMERGENCY OVERRIDE"

                elif current_time < green_until_time:
                    is_green = True
                    remaining = int(green_until_time - current_time)
                    timer_str = f"NS GREEN: {remaining}s left"

                else:
                    if density > 800:
                        is_green = True
                        green_until_time = current_time + 60.0
                        self.root.after(0, self.log, f"High Density ({density} px) -> NS GREEN locked for 60s.")
                        last_logged_state = "GREEN_LOCKED"
                        timer_str = "NS GREEN: 60s left"
                    else:
                        is_green = False
                        green_until_time = 0.0
                        if last_logged_state != "RED":
                            self.root.after(0, self.log, f"Low Demand ({density} px) -> NS RED (EW Green).")
                            last_logged_state = "RED"
                        timer_str = "NS RED (EW Green)"

                self.active_sim.signal_is_green = is_green
                self.root.after(0, self.set_signal_light, is_green)
                self.root.after(0, self.set_timer_text, timer_str)

                # Draw Flush Boxes
                ns_color = (0, 255, 0) if is_green else (0, 0, 255)
                ew_color = (0, 0, 255) if is_green else (0, 255, 0)

                for name, pts_list in corridor_rois.items():
                    pts = np.array(pts_list, dtype=np.int32)
                    col = ns_color if name in ['N', 'S'] else ew_color
                    cv2.polylines(frame, [pts], True, col, 2)

                # On-Screen Readouts
                cv2.putText(frame, f"S-ROI DENSITY: {density}", (20, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.putText(frame, timer_str, (330, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.55, ns_color, 2)

                # Push to Tkinter
                cv2_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(cv2_rgb)
                tk_img = ImageTk.PhotoImage(image=pil_img)

                def update_display(photo=tk_img):
                    if self.is_running:
                        self.video_label.imgtk = photo
                        self.video_label.configure(image=photo, text="")

                self.root.after(0, update_display)
                time.sleep(0.025)

        except Exception as err:
            self.root.after(0, self.log, f"Runtime Error: {err}")
            print(f"[Thread Error]: {err}")
        finally:
            self.root.after(0, lambda: self.video_label.configure(image='', text="Simulation Offline"))

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartTrafficGUI(root)
    root.mainloop()