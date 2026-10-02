import os
import time
import csv
import cv2
import numpy as np
from ultralytics import YOLO

# Default fallback model
model = YOLO('yolov8n.pt')

# COCO vehicle classes: 2: Car, 3: Motorcycle, 5: Bus, 7: Truck
INDIAN_VEHICLE_CLASSES = [2, 3, 5, 7]

strobe_history = []

def detect_emergency_flashing(vehicle_crop):
    global strobe_history
    if vehicle_crop.size == 0:
        return False

    hsv = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)

    lower_red1, upper_red1 = np.array([0, 150, 150]), np.array([10, 255, 255])
    lower_red2, upper_red2 = np.array([170, 150, 150]), np.array([180, 255, 255])
    mask_red = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1), 
                              cv2.inRange(hsv, lower_red2, upper_red2))

    lower_blue, upper_blue = np.array([100, 170, 150]), np.array([140, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    emergency_lights_mask = cv2.bitwise_or(mask_red, mask_blue)
    strobe_pixel_count = cv2.countNonZero(emergency_lights_mask)
    
    strobe_history.append(strobe_pixel_count)
    if len(strobe_history) > 10:
        strobe_history.pop(0)

    if len(strobe_history) < 6:
        return False

    strobe_variance = np.std(strobe_history)
    return strobe_variance > 200.0 and np.max(strobe_history) > 150

def check_emergency_yolo(frame, approach_roi_pts, yolo_results=None):
    if yolo_results is None:
        yolo_results = model(frame, verbose=False)

    contour = approach_roi_pts.astype(np.float32)

    for result in yolo_results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            if class_id in [2, 5, 7] and confidence > 0.50:
                xyxy = box.xyxy[0].cpu().numpy()
                cx = float((xyxy[0] + xyxy[2]) / 2.0)
                cy = float(xyxy[3])
                
                # Type-safe pointPolygonTest using float coordinates
                if cv2.pointPolygonTest(contour, (cx, cy), False) >= 0:
                    h, w = frame.shape[:2]
                    x1, y1 = max(0, int(xyxy[0])), max(0, int(xyxy[1]))
                    x2, y2 = min(w, int(xyxy[2])), min(h, int(xyxy[3]))
                    
                    vehicle_crop = frame[y1:y2, x1:x2]
                    if detect_emergency_flashing(vehicle_crop):
                        return True
    return False

def calculate_hybrid_density(frame, fg_clean, yolo_results, approach_roi_pts):
    # 1. Base MOG2 Motion Pixel Density
    h, w = frame.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [approach_roi_pts.astype(np.int32)], 255)
    corridor_fg = cv2.bitwise_and(fg_clean, fg_clean, mask=mask)
    pixel_density = cv2.countNonZero(corridor_fg)

    # 2. Static Queue Density Floor via YOLOv8
    yolo_density_boost = 0
    vehicle_count = 0
    contour = approach_roi_pts.astype(np.float32)
    
    if yolo_results and len(yolo_results[0].boxes) > 0:
        for box in yolo_results[0].boxes:
            cls = int(box.cls[0].cpu().numpy())
            conf = float(box.conf[0].cpu().numpy())
            
            if cls in INDIAN_VEHICLE_CLASSES and conf > 0.35:
                xyxy = box.xyxy[0].cpu().numpy()
                cx = float((xyxy[0] + xyxy[2]) / 2.0)
                cy = float(xyxy[3])
                
                if cv2.pointPolygonTest(contour, (cx, cy), False) >= 0:
                    vehicle_count += 1
                    if cls == 3:        # Two-Wheeler
                        yolo_density_boost += 350
                    elif cls in [5, 7]: # Bus / Heavy Truck
                        yolo_density_boost += 2500
                    else:               # Car / Auto-Rickshaw
                        yolo_density_boost += 850

    effective_density = max(pixel_density, yolo_density_boost)
    return effective_density, vehicle_count

def process_lane_roi(frame, roi_points, bg_subtractor, yolo_model=None):
    roi_pts = np.array(roi_points, dtype=np.int32)
    
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    fg_mask = bg_subtractor.apply(blurred)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_small)
    fg_clean = cv2.morphologyEx(fg_clean, cv2.MORPH_CLOSE, kernel_large)

    active_yolo = yolo_model if yolo_model is not None else model
    yolo_results = active_yolo(frame, verbose=False)

    density_score, _ = calculate_hybrid_density(frame, fg_clean, yolo_results, roi_pts)
    is_emergency = check_emergency_yolo(frame, roi_pts, yolo_results)

    return density_score, is_emergency

def run_corridor_manager(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file '{video_path}'.")
        return

    csv_file = 'traffic_performance_log.csv'
    file_exists = os.path.isfile(csv_file)
    log_file = open(csv_file, mode='a', newline='')
    writer = csv.writer(log_file)

    if not file_exists:
        writer.writerow(['Timestamp', 'Frame_Index', 'Latency_ms', 'Corridor_Density', 'Signal_State', 'Emergency_Active'])

    approach_roi = [[410, 95], [560, 95], [550, 360], [150, 360]]
    subtractor = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False)
    frame_index = 0

    print("--- Running Corridor Traffic Manager with CSV Logging ---")

    while cap.isOpened():
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame_index += 1
        frame = cv2.resize(frame, (640, 360))

        density, emergency = process_lane_roi(frame, approach_roi, subtractor, model)

        if emergency:
            signal_state = "GREEN"
            status_text = "EMERGENCY OVERRIDE: GREEN"
            status_color = (0, 0, 255)
            is_emergency_flag = 1
        elif density > 1200:
            signal_state = "GREEN"
            status_text = f"DYNAMIC FLOW: GREEN (Density: {density})"
            status_color = (0, 255, 0)
            is_emergency_flag = 0
        else:
            signal_state = "RED"
            status_text = f"LOW DEMAND: RED (Density: {density})"
            status_color = (0, 0, 255)
            is_emergency_flag = 0

        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)

        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([current_time, frame_index, latency_ms, density, signal_state, is_emergency_flag])
        log_file.flush()

        pts = np.array(approach_roi, dtype=np.int32)
        box_color = (0, 255, 0) if signal_state == "GREEN" else (0, 0, 255)
        cv2.polylines(frame, [pts], isClosed=True, color=box_color, thickness=2)

        cv2.rectangle(frame, (10, 10), (390, 45), (0, 0, 0), -1)
        cv2.putText(frame, status_text, (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 2)

        cv2.imshow("Smart Traffic Corridor Controller", frame)

        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    log_file.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_corridor_manager('Light_Traffic.mp4')