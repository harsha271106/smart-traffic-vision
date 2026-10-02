import time
import random
import cv2
import numpy as np

class TrafficSimulator:
    def __init__(self, width=640, height=360):
        self.width = width
        self.height = height
        
        self.cx = width // 2   # 320
        self.cy = height // 2  # 180
        self.road_half = 50    # Road width = 100px (cx-50 to cx+50, cy-50 to cy+50)
        
        # Stop line coordinate boundaries for Left-Hand Drive (LHD):
        # S: y = 236
        # N: y = 124
        # W (coming from left, driving East on bottom lane): x = 264
        # E (coming from right, driving West on top lane): x = 376
        self.stop_lines = {
            'S': self.cy + self.road_half + 6,   # 236
            'N': self.cy - self.road_half - 6,   # 124
            'W': self.cx - self.road_half - 6,   # 264
            'E': self.cx + self.road_half + 6    # 376
        }
        
        self.signal_is_green = False  # True: NS Green / EW Red | False: NS Red / EW Green
        
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
            speed = 3.4
        else:
            v_type = random.choices(['bike', 'auto', 'car', 'bus'], weights=[0.45, 0.25, 0.20, 0.10])[0]
            spec = self.vehicle_specs[v_type]
            w, h = spec['w'], spec['h']
            color = spec['color']
            speed = spec['speed'] + random.uniform(-0.2, 0.2)

        # STRICT INDIAN LEFT-HAND DRIVE LANE ASSIGNMENTS:
        if direction == 'S': 
            # Moving South to North (UP): Left lane is [270, 320]
            x = random.randint(self.cx - self.road_half + 6, self.cx - w - 6)
            y = float(self.height + 15)
            vx, vy = 0.0, -speed
            rw, rh = w, h
        elif direction == 'N': 
            # Moving North to South (DOWN): Left lane is [320, 370]
            x = random.randint(self.cx + 6, self.cx + self.road_half - w - 6)
            y = float(-h - 15)
            vx, vy = 0.0, speed
            rw, rh = w, h
        elif direction == 'W': 
            # Coming from West, moving East (RIGHT): Indian Left lane is BOTTOM [180, 230]
            x = float(-h - 15)
            y = random.randint(self.cy + 6, self.cy + self.road_half - w - 6)
            vx, vy = speed, 0.0
            rw, rh = h, w
        else: # 'E'
            # Coming from East, moving West (LEFT): Indian Left lane is TOP [130, 180]
            x = float(self.width + 15)
            y = random.randint(self.cy - self.road_half + 6, self.cy - w - 6)
            vx, vy = -speed, 0.0
            rw, rh = h, w

        # Prevent overlapping spawns
        for existing in self.vehicles:
            if existing['dir'] == direction:
                if abs(existing['x'] - x) < 26 and abs(existing['y'] - y) < 45:
                    return

        self.vehicles.append({
            'dir': direction,
            'x': float(x),
            'y': float(y),
            'w': rw,
            'h': rh,
            'color': color,
            'speed': speed,
            'vx': vx,
            'vy': vy,
            'is_emergency': is_emergency
        })

    def trigger_emergency(self):
        self.spawn_vehicle(direction='S', is_emergency=True)

    def update(self):
        self.spawn_timer += 1
        if self.spawn_timer > 18:
            if len(self.vehicles) < 26:
                self.spawn_vehicle()
            self.spawn_timer = 0

        if time.time() - self.last_strobe_toggle > 0.10:
            self.emergency_strobe_state = not self.emergency_strobe_state
            self.last_strobe_toggle = time.time()

        for i, v in enumerate(self.vehicles):
            target_speed = v['speed']
            d = v['dir']
            min_bumper_gap = 16.0
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

            corridor_green = self.signal_is_green if (d in ['S', 'N']) else (not self.signal_is_green)
            stop_pos = self.stop_lines[d]

            if d == 'S': dist_to_stop = v['y'] - stop_pos
            elif d == 'N': dist_to_stop = stop_pos - (v['y'] + v['h'])
            elif d == 'W': dist_to_stop = stop_pos - (v['x'] + v['w'])
            elif d == 'E': dist_to_stop = v['x'] - stop_pos

            # Deceleration at stop line
            if not corridor_green and 0 < dist_to_stop < 60:
                target_speed = min(target_speed, max(0.0, (dist_to_stop - 4) * 0.08))

            # Maintain space to prevent stacking
            if dist_to_leader < 40:
                if dist_to_leader <= min_bumper_gap:
                    target_speed = 0.0
                else:
                    target_speed = min(target_speed, (dist_to_leader - min_bumper_gap) * 0.12)

            if d == 'S': v['y'] -= target_speed
            elif d == 'N': v['y'] += target_speed
            elif d == 'W': v['x'] += target_speed
            elif d == 'E': v['x'] -= target_speed

        self.vehicles = [
            v for v in self.vehicles 
            if -80 < v['x'] < self.width + 80 and -80 < v['y'] < self.height + 80
        ]

    def render(self):
        self.update()
        frame = np.full((self.height, self.width, 3), 35, dtype=np.uint8)

        # 4-Way Road Surfaces
        cv2.rectangle(frame, (self.cx - self.road_half, 0), (self.cx + self.road_half, self.height), (60, 60, 60), -1)
        cv2.rectangle(frame, (0, self.cy - self.road_half), (self.width, self.cy + self.road_half), (60, 60, 60), -1)
        cv2.rectangle(frame, (self.cx - self.road_half, self.cy - self.road_half), 
                             (self.cx + self.road_half, self.cy + self.road_half), (55, 55, 55), -1)

        # Center Dotted Dividers
        for y in range(0, self.height, 20):
            if abs(y - self.cy) > self.road_half:
                cv2.line(frame, (self.cx, y), (self.cx, y + 10), (160, 160, 160), 1)
        for x in range(0, self.width, 20):
            if abs(x - self.cx) > self.road_half:
                cv2.line(frame, (x, self.cy), (x + 10, self.cy), (160, 160, 160), 1)

        # STOP LINES (ACCURATE INDIAN LEFT-HAND DRIVE):
        # South approach (moving North): Left lane [270, 320]
        cv2.line(frame, (self.cx - self.road_half, self.stop_lines['S']), (self.cx, self.stop_lines['S']), (255, 255, 255), 2)
        
        # North approach (moving South): Left lane [320, 370]
        cv2.line(frame, (self.cx, self.stop_lines['N']), (self.cx + self.road_half, self.stop_lines['N']), (255, 255, 255), 2)
        
        # West approach (moving East): Indian Left lane is BOTTOM [180, 230], line at x=264
        cv2.line(frame, (self.stop_lines['W'], self.cy), (self.stop_lines['W'], self.cy + self.road_half), (255, 255, 255), 2)
        
        # East approach (moving West): Indian Left lane is TOP [130, 180], line at x=376
        cv2.line(frame, (self.stop_lines['E'], self.cy - self.road_half), (self.stop_lines['E'], self.cy), (255, 255, 255), 2)

        # Render Vehicles
        for v in self.vehicles:
            x1, y1 = int(v['x']), int(v['y'])
            x2, y2 = int(x1 + v['w']), int(y1 + v['h'])

            cv2.rectangle(frame, (x1, y1), (x2, y2), v['color'], -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (20, 20, 20), 1)

            if v['is_emergency']:
                c_left = (0, 0, 255) if self.emergency_strobe_state else (255, 0, 0)
                c_right = (255, 0, 0) if self.emergency_strobe_state else (0, 0, 255)
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                cv2.circle(frame, (mid_x - 4, mid_y), 3, c_left, -1)
                cv2.circle(frame, (mid_x + 4, mid_y), 3, c_right, -1)

        # Traffic Signal Dots
        s_color = (0, 255, 0) if self.signal_is_green else (0, 0, 255)
        ew_color = (0, 0, 255) if self.signal_is_green else (0, 255, 0)
        
        cv2.circle(frame, (self.cx - self.road_half - 8, self.stop_lines['S']), 5, s_color, -1)
        cv2.circle(frame, (self.stop_lines['W'] - 8, self.cy + self.road_half + 8), 5, ew_color, -1)

        return frame