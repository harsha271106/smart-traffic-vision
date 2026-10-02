import time
import random
import threading
import tkinter as tk
from tkinter import scrolledtext
import cv2
import numpy as np
from PIL import Image, ImageTk
from ultralytics import YOLO

# ==============================================================================
# 1. EMULATOR: INDIAN LEFT-HAND DRIVE
# ==============================================================================
class TrafficSimulatorLHD:
    def __init__(self, width=640, height=360):
        self.width = width
        self.height = height
        
        self.cx = 320
        self.cy = 180
        self.road_half = 50 

        # Stop lines on incoming left lanes:
        # South: y = 236
        # North: y = 124
        # West (coming from left): x = 264 (on BOTTOM lane y: 180 to 230)
        # East (coming from right): x = 376 (on TOP lane y: 130 to 180)
        self.stop_lines = {
            'S': 236,
            'N': 124,
            'W': 264,
            'E': 376
        }

        self.signal_is_green = False
        
        self.vehicle_specs = {
            'bike': {'w': 8, 'h': 18, 'color': (70, 70, 70), 'speed': 3.2},
            'auto': {'w': 14, 'h': 24, 'color': (0, 215, 255), 'speed': 2.6},
            'car':  {'w': 20, 'h': 36, 'color': (210, 210, 210), 'speed': 2.8},
            'bus':  {'w': 26, 'h': 56, 'color': (220, 110, 50), 'speed': 2.0}
        }
        
        self.vehicles = []
        self.spawn_timer = 0
        self.emergency_strobe_state = False
        self.last_strobe_toggle = time.time()

    def spawn_vehicle(self, direction=None, is_emergency=False):
        if direction is None:
            direction = random.choices(['S', 'N', 'W', 'E'], weights=[0.35, 0.20, 0.25, 0.20])[0]

        if is_emergency:
            w, h = 22, 44
            color = (245, 245, 245)
            speed = 3.5
        else:
            v_type = random.choices(['bike', 'auto', 'car', 'bus'], weights=[0.45, 0.25, 0.20, 0.10])[0]
            spec = self.vehicle_specs[v_type]
            w, h = spec['w'], spec['h']
            color = spec['color']
            speed = spec['speed'] + random.uniform(-0.2, 0.2)

        # Indian Left-Hand Drive Placements:
        if direction == 'S':
            # South approach, driving UP: Left lane x in [270, 320]
            x = random.randint(self.cx - self.road_half + 4, self.cx - w - 4)
            y = float(self.height + 10)
            render_w, render_h = w, h
        elif direction == 'N':
            # North approach, driving DOWN: Left lane x in [320, 370]
            x = random.randint(self.cx + 4, self.cx + self.road_half - w - 4)
            y = float(-h - 10)
            render_w, render_h = w, h
        elif direction == 'W':
            # West approach, driving EAST: BOTTOM lane y in [180, 230]
            x = float(-h - 10)
            y = random.randint(self.cy + 4, self.cy + self.road_half - w - 4)
            render_w, render_h = h, w
        else: # 'E'
            # East approach, driving WEST: TOP lane y in [130, 180]
            x = float(self.width + 10)
            y = random.randint(self.cy - self.road_half + 4, self.cy - w - 4)
            render_w, render_h = h, w

        for existing in self.vehicles:
            if existing['dir'] == direction:
                if abs(existing['x'] - x) < 25 and abs(existing['y'] - y) < 40:
                    return

        self.vehicles.append({
            'dir': direction,
            'x': float(x),
            'y': float(y),
            'w': render_w,
            'h': render_h,
            'color': color,
            'speed': speed,
            'is_emergency': is_emergency
        })

    def trigger_emergency(self):
        self.spawn_vehicle(direction='S', is_emergency=True)

    def update(self):
        self.spawn_timer += 1
        if self.spawn_timer > 18:
            if len(self.vehicles) < 24:
                self.spawn_vehicle()
            self.spawn_timer = 0

        if time.time() - self.last_strobe_toggle > 0.10:
            self.emergency_strobe_state = not self.emergency_strobe_state
            self.last_strobe_toggle = time.time()

        min_gap = 14.0

        for i, v in enumerate(self.vehicles):
            target_speed = v['speed']
            d = v['dir']
            dist_to_leader = 999.0

            for j, other in enumerate(self.vehicles):
                if i != j and other['dir'] == d:
                    if d == 'S' and other['y'] < v['y']:
                        gap = v['y'] - (other['y'] + other['h'])
                        if gap > 0: dist_to_leader = min(dist_to_leader, gap)
                    elif d == 'N' and other['y'] > v['y']:
                        gap = other['y'] - (v['y'] + v['h'])
                        if gap > 0: dist_to_leader = min(dist_to_leader, gap)
                    elif d == 'W' and other['x'] > v['x']:
                        gap = other['x'] - (v['x'] + v['w'])
                        if gap > 0: dist_to_leader = min(dist_to_leader, gap)
                    elif d == 'E' and other['x'] < v['x']:
                        gap = v['x'] - (other['x'] + other['w'])
                        if gap > 0: dist_to_leader = min(dist_to_leader, gap)

            is_green = self.signal_is_green if (d in ['S', 'N']) else (not self.signal_is_green)
            stop = self.stop_lines[d]

            if d == 'S': dist_to_stop = v['y'] - stop
            elif d == 'N': dist_to_stop = stop - (v['y'] + v['h'])
            elif d == 'W': dist_to_stop = stop - (v['x'] + v['w'])
            elif d == 'E': dist_to_stop = v['x'] - stop

            if not is_green and 0 < dist_to_stop < 55:
                target_speed = min(target_speed, max(0.0, (dist_to_stop - 2) * 0.08))

            if dist_to_leader < 35:
                if dist_to_leader <= min_gap:
                    target_speed = 0.0
                else:
                    target_speed = min(target_speed, (dist_to_leader - min_gap) * 0.12)

            if d == 'S': v['y'] -= target_speed
            elif d == 'N': v['y'] += target_speed
            elif d == 'W': v['x'] += target_speed
            elif d == 'E': v['x'] -= target_speed

        self.vehicles = [
            v for v in self.vehicles 
            if -70 < v['x'] < self.width + 70 and -70 < v['y'] < self.height + 70
        ]

    def render(self):
        self.update()
        frame = np.full((self.height, self.width, 3), 35, dtype=np.uint8)

        # 4-Way Road Surfaces
        cv2.rectangle(frame, (self.cx - self.road_half, 0), (self.cx + self.road_half, self.height), (60, 60, 60), -1)
        cv2.rectangle(frame, (0, self.cy - self.road_half), (self.width, self.cy + self.road_half), (60, 60, 60), -1)
        cv2.rectangle(frame, (self.cx - self.road_half, self.cy - self.road_half), 
                             (self.cx + self.road_half, self.cy + self.road_half), (55, 55, 55), -1)

        # Center Dotted Lines
        for y in range(0, self.height, 20):
            if abs(y - self.cy) > self.road_half:
                cv2.line(frame, (self.cx, y), (self.cx, y + 10), (160, 160, 160), 1)
        for x in range(0, self.width, 20):
            if abs(x - self.cx) > self.road_half:
                cv2.line(frame, (x, self.cy), (x + 10, self.cy), (160, 160, 160), 1)

        # STOP LINES (White lines across incoming lanes):
        # South: Left lane [270, 320] at y=236
        cv2.line(frame, (270, 236), (320, 236), (255, 255, 255), 2)
        # North: Left lane [320, 370] at y=124
        cv2.line(frame, (320, 124), (370, 124), (255, 255, 255), 2)
        # West (driving East): BOTTOM lane [180, 230] at x=264
        cv2.line(frame, (264, 180), (264, 230), (255, 255, 255), 2)
        # East (driving West): TOP lane [130, 180] at x=376
        cv2.line(frame, (376, 130), (376, 180), (255, 255, 255), 2)

        # Draw Vehicles
        for v in self.vehicles:
            x1, y1 = int(v['x']), int(v['y'])
            x2, y2 = int(x1 + v['w']), int(y1 + v['h'])
            cv2.rectangle(frame, (x1, y1), (x2, y2), v['color'], -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (20, 20, 20), 1)

            if v['is_emergency']:
                c1 = (0, 0, 255) if self.emergency_strobe_state else (255, 0, 0)
                c2 = (255, 0, 0) if self.emergency_strobe_state else (0, 0, 255)
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                cv2.circle(frame, (mid_x - 3, mid_y), 3, c1, -1)
                cv2.circle(frame, (mid_x + 3, mid_y), 3, c2, -1)

        return frame

# ==============================================================================
# 2. DENSITY & PREEMPTION
# ==============================================================================
yolo_model = YOLO("yolov8n.pt")
strobe_hist = []

def detect_flashing_strobe(crop):
    global strobe_hist
    if crop.size == 0: return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    m_red = cv2.bitwise_or(cv2.inRange(hsv, np.array([0, 150, 150]), np.array([10, 255, 255])),
                           cv2.inRange(hsv, np.array([170, 150, 150]), np.array([180, 255, 255])))
    m_blue = cv2.inRange(hsv, np.array([100, 170, 150]), np.array([140, 255, 255]))
    cnt = cv2.countNonZero(cv2.bitwise_or(m_red, m_blue))
    strobe_hist.append(cnt)
    if len(strobe_hist) > 10: strobe_hist.pop(0)
    if len(strobe_hist) < 6: return False
    return np.std(strobe_hist) > 200.0 and np.max(strobe_hist) > 150

def analyze_corridor(frame, roi_pts, subtractor):
    pts_int = np.array(roi_pts, dtype=np.int32)
    pts_float = pts_int.astype(np.float32)

    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    fg = subtractor.apply(blurred)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [pts_int], 255)
    mog_density = cv2.countNonZero(cv2.bitwise_and(fg, fg, mask=mask))

    results = yolo_model(frame, verbose=False)
    yolo_boost = 0
    emergency = False

    if results and len(results[0].boxes) > 0:
        for box in results[0].boxes:
            cls = int(box.cls[0].cpu().numpy())
            conf = float(box.conf[0].cpu().numpy())
            if cls in [2, 3, 5, 7] and conf > 0.35:
                xyxy = box.xyxy[0].cpu().numpy()
                cx = float((xyxy[0] + xyxy[2]) / 2.0)
                cy = float(xyxy[3])
                
                if cv2.pointPolygonTest(pts_float, (cx, cy), False) >= 0:
                    if cls == 3: yolo_boost += 350
                    elif cls in [5, 7]: yolo_boost += 2500
                    else: yolo_boost += 850

                    if cls in [2, 5, 7] and conf > 0.50:
                        x1, y1 = max(0, int(xyxy[0])), max(0, int(xyxy[1]))
                        x2, y2 = min(frame.shape[1], int(xyxy[2])), min(frame.shape[0], int(xyxy[3]))
                        if detect_flashing_strobe(frame[y1:y2, x1:x2]):
                            emergency = True

    return max(mog_density, yolo_boost), emergency

# ==============================================================================
# 3. GUI DASHBOARD
# ==============================================================================
class MainDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Adaptive Smart Traffic Management - LHD Intersection")
        self.root.geometry("1120x700")
        self.root.configure(bg="#1e1e1e")

        self.is_running = False
        self.sim = None

        t_frame = tk.Frame(root, bg="#0d1117", height=50)
        t_frame.pack(fill=tk.X)
        tk.Label(t_frame, text="4-WAY SMART TRAFFIC CONTROLLER (LHD INDIA)", 
                 font=("Helvetica", 16, "bold"), fg="#58a6ff", bg="#0d1117").pack(pady=10)

        m_frame = tk.Frame(root, bg="#1e1e1e")
        m_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.feed = tk.Label(m_frame, bg="black", text="Stream Offline", fg="white", font=("Helvetica", 12))
        self.feed.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        panel = tk.Frame(m_frame, bg="#2d2d2d", width=340)
        panel.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(panel, text="Controls", font=("Helvetica", 12, "bold"), fg="white", bg="#2d2d2d").pack(pady=8)
        self.btn_start = tk.Button(panel, text="▶ Start Simulation", font=("Helvetica", 10, "bold"), 
                                   bg="#238636", fg="white", width=22, height=2, command=self.start)
        self.btn_start.pack(pady=4)

        self.btn_stop = tk.Button(panel, text="⏹ Stop Simulation", font=("Helvetica", 10, "bold"), 
                                  bg="#da3633", fg="white", width=22, height=2, state=tk.DISABLED, command=self.stop)
        self.btn_stop.pack(pady=4)

        tk.Button(panel, text="🚨 Spawn Emergency Vehicle", font=("Helvetica", 9, "bold"), 
                  bg="#d97706", fg="white", width=22, height=2, command=self.inject_emg).pack(pady=6)

        tk.Label(panel, text="Signal Phase", font=("Helvetica", 11, "bold"), fg="white", bg="#2d2d2d").pack(pady=10)
        self.canv = tk.Canvas(panel, width=50, height=50, bg="#2d2d2d", highlightthickness=0)
        self.canv.pack()
        self.circle = self.canv.create_oval(5, 5, 45, 45, fill="#da3633")

        self.lbl_timer = tk.Label(panel, text="Timer: Idle", font=("Helvetica", 11, "bold"), fg="#e3b341", bg="#2d2d2d")
        self.lbl_timer.pack(pady=5)

        tk.Label(panel, text="System Log Console", font=("Helvetica", 11, "bold"), fg="white", bg="#2d2d2d").pack(pady=5)
        self.logs = scrolledtext.ScrolledText(panel, width=38, height=14, font=("Consolas", 8), bg="#0d1117", fg="#7ee787")
        self.logs.pack(pady=5, padx=5)

    def log(self, text):
        self.logs.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {text}\n")
        self.logs.see(tk.END)

    def inject_emg(self):
        if self.sim and self.is_running:
            self.sim.trigger_emergency()
            self.log("ACTION: Injected Ambulance onto South Corridor!")

    def start(self):
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.log("Starting simulation loop...")
        threading.Thread(target=self.run_loop, daemon=True).start()

    def stop(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.log("Simulation halted.")

    def run_loop(self):
        self.sim = TrafficSimulatorLHD(640, 360)
        subtractor = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False)

        # CORRIDOR BOXES (DIRECTLY BEHIND STOP LINES ON THE LEFT LANES):
        boxes = {
            # South: Left lane going UP -> x: [270, 320], y: [240, 350]
            'S': [[270, 240], [320, 240], [320, 350], [270, 350]],
            
            # North: Left lane going DOWN -> x: [320, 370], y: [10, 120]
            'N': [[320, 10],  [370, 10],  [370, 120], [320, 120]],
            
            # West (driving East): BOTTOM lane y: [180, 230], x: [150, 260]
            'W': [[150, 180], [260, 180], [260, 230], [150, 230]],
            
            # East (driving West): TOP lane y: [130, 180], x: [380, 490]
            'E': [[380, 130], [490, 130], [490, 180], [380, 180]]
        }

        is_green = False
        green_lock_until = 0.0

        while self.is_running:
            frame = self.sim.render()
            density, emergency = analyze_corridor(frame, boxes['S'], subtractor)
            curr = time.time()

            if emergency:
                is_green = True
                green_lock_until = 0.0
                timer_str = "EMERGENCY OVERRIDE (GREEN)"
            elif curr < green_lock_until:
                is_green = True
                remaining = int(green_lock_until - curr)
                timer_str = f"NS GREEN LOCKED: {remaining}s left"
            else:
                if density > 800:
                    is_green = True
                    green_lock_until = curr + 60.0
                    self.root.after(0, self.log, f"High Density ({density} px) -> 60s Green Locked!")
                    timer_str = "NS GREEN LOCKED: 60s left"
                else:
                    is_green = False
                    green_lock_until = 0.0
                    timer_str = "NS RED (EW Cross Traffic Green)"

            self.sim.signal_is_green = is_green
            self.root.after(0, self.canv.itemconfig, self.circle, {'fill': '#238636' if is_green else '#da3633'})
            self.root.after(0, self.lbl_timer.config, {'text': timer_str})

            ns_col = (0, 255, 0) if is_green else (0, 0, 255)
            ew_col = (0, 0, 255) if is_green else (0, 255, 0)

            for key, pts in boxes.items():
                col = ns_col if key in ['S', 'N'] else ew_col
                cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, col, 2)

            cv2.putText(frame, f"S-ROI DENSITY: {density}", (20, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.putText(frame, timer_str, (320, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.52, ns_col, 2)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(image=Image.fromarray(rgb))

            def draw(photo=img):
                if self.is_running:
                    self.feed.imgtk = photo
                    self.feed.configure(image=photo, text="")

            self.root.after(0, draw)
            time.sleep(0.025)

        self.root.after(0, lambda: self.feed.configure(image='', text="Stream Offline"))

if __name__ == "__main__":
    root = tk.Tk()
    app = MainDashboard(root)
    root.mainloop()