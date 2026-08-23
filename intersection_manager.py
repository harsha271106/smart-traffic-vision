import cv2
import numpy as np
from ultralytics import YOLO

# Load YOLOv8 Model
model = YOLO('yolov8n.pt')

strobe_history = []

def detect_emergency_flashing(vehicle_crop):
    global strobe_history
    if vehicle_crop.size == 0:
        return False

    hsv = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)

    # Red & Blue HSV Masks
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

def check_emergency_yolo(frame_roi):
    results = model(frame_roi, verbose=False)
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            if class_id in [2, 5, 7] and confidence > 0.55:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                vehicle_crop = frame_roi[y1:y2, x1:x2]
                
                if detect_emergency_flashing(vehicle_crop):
                    return True
    return False

def process_lane_roi(frame, roi_points, bg_subtractor):
    h, w = frame.shape[:2]
    roi_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(roi_mask, [np.array(roi_points, dtype=np.int32)], 255)
    
    frame_roi = cv2.bitwise_and(frame, frame, mask=roi_mask)
    is_emergency = check_emergency_yolo(frame_roi)

    fg_mask = bg_subtractor.apply(frame_roi)
    fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_small)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_large)

    density_score = cv2.countNonZero(fg_mask)
    return density_score, is_emergency

def run_4way_intersection(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file '{video_path}'.")
        return

    # Heavily angled rightward perspective coordinates
    lane_rois = [
        [[400, 90], [445, 90], [380, 360], [250, 360]],  # Lane 1 (Left inner driving lane)
        [[445, 90], [485, 90], [475, 360], [380, 360]],  # Lane 2 (Middle left)
        [[485, 90], [530, 90], [565, 360], [475, 360]],  # Lane 3 (Middle right)
        [[530, 90], [585, 90], [640, 360], [565, 360]]   # Lane 4 (Far right corridor)
    ]
    
    subtractors = [cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False) for _ in range(4)]
    lane_names = ["LANE 1", "LANE 2", "LANE 3", "LANE 4"]

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
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
            status_text = f"EMERGENCY OVERRIDE: {lane_names[active_lane]} GREEN"
            status_color = (0, 0, 255)
        else:
            active_lane = int(np.argmax(densities))
            status_text = f"DYNAMIC PRIORITY: {lane_names[active_lane]} GREEN"
            status_color = (0, 255, 0)

        # 1. Draw Sharply Angled Lane Boundaries
        for i in range(4):
            pts = np.array(lane_rois[i], dtype=np.int32)
            is_active = (i == active_lane)
            box_color = (0, 255, 0) if is_active else (0, 0, 255)
            cv2.polylines(frame, [pts], isClosed=True, color=box_color, thickness=2)

        # 2. Draw Top Main Status Banner
        cv2.rectangle(frame, (10, 10), (370, 45), (0, 0, 0), -1)
        cv2.putText(frame, status_text, (15, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 2)

        # 3. Draw Side Overlay Box for Individual Lane Stats
        cv2.rectangle(frame, (500, 10), (630, 105), (0, 0, 0), -1)
        for i in range(4):
            is_active = (i == active_lane)
            text_color = (0, 255, 0) if is_active else (0, 0, 255)
            cv2.putText(frame, f"L{i+1}: {densities[i]} px", (510, 28 + (i * 18)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)

        cv2.imshow("Multi-Lane Smart Traffic Management System", frame)

        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_4way_intersection('Light_Traffic.mp4')