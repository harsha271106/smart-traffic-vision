import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import cv2
import numpy as np
from PIL import Image, ImageTk
from ultralytics import YOLO

# Import processing logic from your intersection manager
from intersection_manager import process_lane_roi

class SmartTrafficGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Traffic Vision - Control Dashboard")
        self.root.geometry("1100x680")
        self.root.configure(bg="#1e1e1e")

        self.is_running = False
        self.cap = None

        # --- Top Title Banner ---
        title_frame = tk.Frame(self.root, bg="#0d1117", height=50)
        title_frame.pack(fill=tk.X)
        title_label = tk.Label(
            title_frame, 
            text="SMART TRAFFIC MANAGEMENT SYSTEM", 
            font=("Helvetica", 16, "bold"), 
            fg="#58a6ff", 
            bg="#0d1117"
        )
        title_label.pack(pady=10)

        # --- Main Layout Frames ---
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Column: Video Feed
        self.video_label = tk.Label(main_frame, bg="black", text="Video Stream Offline", fg="white", font=("Helvetica", 12))
        self.video_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Right Column: Control & Status Panel
        right_panel = tk.Frame(main_frame, bg="#2d2d2d", width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Control Buttons ---
        ctrl_label = tk.Label(right_panel, text="System Controls", font=("Helvetica", 12, "bold"), fg="white", bg="#2d2d2d")
        ctrl_label.pack(pady=(10, 5))

        self.start_btn = tk.Button(right_panel, text="▶ Start Simulation", font=("Helvetica", 10, "bold"), bg="#238636", fg="white", command=self.start_sim, width=20, height=2)
        self.start_btn.pack(pady=5)

        self.stop_btn = tk.Button(right_panel, text="⏹ Stop Simulation", font=("Helvetica", 10, "bold"), bg="#da3633", fg="white", command=self.stop_sim, state=tk.DISABLED, width=20, height=2)
        self.stop_btn.pack(pady=5)

        # --- Active Signal Visualizer ---
        sig_label = tk.Label(right_panel, text="Intersection Signals", font=("Helvetica", 12, "bold"), fg="white", bg="#2d2d2d")
        sig_label.pack(pady=(15, 5))

        self.canvas_lights = {}
        light_frame = tk.Frame(right_panel, bg="#2d2d2d")
        light_frame.pack(pady=5)

        for i in range(4):
            l_box = tk.Frame(light_frame, bg="#2d2d2d")
            l_box.pack(side=tk.LEFT, padx=5)
            
            lbl = tk.Label(l_box, text=f"L{i+1}", font=("Helvetica", 9, "bold"), fg="white", bg="#2d2d2d")
            lbl.pack()
            
            c = tk.Canvas(l_box, width=30, height=30, bg="#2d2d2d", highlightthickness=0)
            c.pack()
            circle = c.create_oval(3, 3, 27, 27, fill="red")
            self.canvas_lights[i] = (c, circle)

        # --- Live Log Console ---
        log_label = tk.Label(right_panel, text="Event Logs", font=("Helvetica", 12, "bold"), fg="white", bg="#2d2d2d")
        log_label.pack(pady=(15, 5))

        self.log_area = scrolledtext.ScrolledText(right_panel, width=35, height=14, font=("Consolas", 8), bg="#0d1117", fg="#7ee787")
        self.log_area.pack(pady=5, padx=5)

        self.log("System initialized and ready.")

    def log(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_area.see(tk.END)

    def set_signal_light(self, active_index):
        for i in range(4):
            c, circle = self.canvas_lights[i]
            color = "#238636" if i == active_index else "#da3633"
            c.itemconfig(circle, fill=color)

    def start_sim(self):
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("Starting multi-lane simulation...")
        threading.Thread(target=self.run_video_loop, daemon=True).start()

    def stop_sim(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("Simulation stopped.")

    def run_video_loop(self):
        video_path = 'Light_Traffic.mp4'
        if not os.path.exists(video_path):
            self.log(f"Error: {video_path} not found!")
            self.stop_sim()
            return

        self.cap = cv2.VideoCapture(video_path)
        subtractors = [cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False) for _ in range(4)]
        lane_rois = [
            [[400, 90], [445, 90], [380, 360], [250, 360]],
            [[445, 90], [485, 90], [475, 360], [380, 360]],
            [[485, 90], [530, 90], [565, 360], [475, 360]],
            [[530, 90], [585, 90], [640, 360], [565, 360]]
        ]

        last_active = -1

        while self.is_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (640, 360))
            densities = []
            emergencies = []

            for i in range(4):
                density, emergency = process_lane_roi(frame, lane_rois[i], subtractors[i])
                densities.append(density)
                emergencies.append(emergency)

            if any(emergencies):
                active_lane = emergencies.index(True)
                if active_lane != last_active:
                    self.log(f"ALERT: Emergency in Lane {active_lane+1}! Override active.")
            else:
                active_lane = int(np.argmax(densities))
                if active_lane != last_active:
                    self.log(f"Priority Shift: Lane {active_lane+1} selected ({densities[active_lane]} px).")

            last_active = active_lane
            self.set_signal_light(active_lane)

            # Overlay Lane Polygons
            for i in range(4):
                pts = np.array(lane_rois[i], dtype=np.int32)
                color = (0, 255, 0) if i == active_lane else (0, 0, 255)
                cv2.polylines(frame, [pts], True, color, 2)

            # Convert OpenCV Frame (BGR) to Tkinter Image (RGB)
            cv2_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2_image)
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            time.sleep(0.02)

        if self.cap:
            self.cap.release()
        self.video_label.configure(image='', text="Video Stream Offline")

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartTrafficGUI(root)
    root.mainloop()