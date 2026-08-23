import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO('yolov8n.pt')

strobe_history = []

def detect_emergency_flashing(vehicle_crop):
    global strobe_history
    if vehicle_crop.size == 0:
        return False

    hsv = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)

    # 1. Red Color Masks
    lower_red1 = np.array([0, 150, 150])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 150, 150])
    upper_red2 = np.array([180, 255, 255])
    mask_red = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1), 
                             cv2.inRange(hsv, lower_red2, upper_red2))

    # 2. Blue Color Mask
    lower_blue = np.array([100, 170, 150])
    upper_blue = np.array([140, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    # Combine Red and Blue masks (Excludes Yellow/White headlights)
    emergency_lights_mask = cv2.bitwise_or(mask_red, mask_blue)
    
    strobe_pixel_count = cv2.countNonZero(emergency_lights_mask)
    
    strobe_history.append(strobe_pixel_count)
    if len(strobe_history) > 10:
        strobe_history.pop(0)

    if len(strobe_history) < 6:
        return False

    strobe_variance = np.std(strobe_history)

    # Requires high oscillation of red/blue pixels + significant light area
    return strobe_variance > 200.0 and np.max(strobe_history) > 150

def check_emergency_yolo(frame_roi):
    """
    Scans ONLY inside the ROI mask area. Any vehicle outside the blue box is ignored.
    """
    results = model(frame_roi, verbose=False)
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            # Check Vehicles: Cars (2), Buses (5), Trucks (7)
            if class_id in [2, 5, 7] and confidence > 0.55:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                vehicle_crop = frame_roi[y1:y2, x1:x2]
                
                # Check specifically for RED/BLUE flashing strobes inside ROI
                if detect_emergency_flashing(vehicle_crop):
                    cv2.rectangle(frame_roi, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.putText(frame_roi, f"SIREN DETECTED ({int(confidence*100)}%)", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    return True
    return False

def run_traffic_analysis(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file '{video_path}'. Check the path!")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0: 
        fps = 25

    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False)

    current_state = None
    remaining_time = 0
    frame_counter = 0

    print(f"--- Processing Video Feed: {video_path} ---")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame = cv2.resize(frame, (640, 360))

        # --- ROI Setup ---
        roi_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        road_pts = np.array([[[410, 80], [580, 80], [640, 360], [320, 360]]], dtype=np.int32)
        cv2.fillPoly(roi_mask, road_pts, 255)
        frame_roi = cv2.bitwise_and(frame, frame, mask=roi_mask)

        # FIX: Pass 'frame_roi' instead of 'frame' so cars outside the blue line are completely ignored!
        is_emergency = check_emergency_yolo(frame_roi)

        # Background Subtraction & Filtering
        fg_mask = bg_subtractor.apply(frame_roi)
        fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)
        kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_small)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_large)

        density_score = cv2.countNonZero(fg_mask)

        # Traffic Level Decision Logic
        if is_emergency:
            target_state = "AUTOMATIC EMERGENCY OVERRIDE!"
            allocated_duration = 60
            signal_color = (0, 0, 255)
        elif density_score < 2500:
            target_state = "LOW"
            allocated_duration = 15
            signal_color = (0, 255, 0)
        elif 2500 <= density_score < 3800:
            target_state = "MODERATE"
            allocated_duration = 30
            signal_color = (0, 255, 255)
        else:
            target_state = "HEAVY"
            allocated_duration = 50
            signal_color = (0, 0, 255)

        # Timer Reset
        if target_state != current_state:
            current_state = target_state
            remaining_time = allocated_duration
            frame_counter = 0

        # Countdown Logic
        frame_counter += 1
        if frame_counter >= fps:
            frame_counter = 0
            if remaining_time > 0:
                remaining_time -= 1

        # UI Overlay Box
        cv2.rectangle(frame, (10, 10), (460, 120), (0, 0, 0), -1)
        cv2.putText(frame, f"Density Score: {density_score}", (20, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Traffic Level: {current_state}", (20, 65), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, signal_color, 2)
        cv2.putText(frame, f"Green Timer Remaining: {remaining_time}s", (20, 95), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Overlay ROI cropped processing back onto visualization
        frame_display = cv2.bitwise_or(frame_roi, cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(roi_mask)))
        cv2.polylines(frame, [road_pts], isClosed=True, color=(255, 0, 0), thickness=2)

        cv2.imshow("Smart Traffic Management Feed", frame)
        cv2.imshow("Vehicle Detection Mask (Filtered ROI)", fg_mask)

        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_traffic_analysis('Light_Traffic.mp4')