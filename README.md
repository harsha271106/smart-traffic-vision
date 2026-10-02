# Smart Traffic Management Framework Using Computer Vision

An Intelligent Transportation System (ITS) developed for **Conceptual Project-I** at Woxsen University. This framework uses OpenCV background subtraction for dynamic density-based multi-lane signal timing, YOLOv8 for automated emergency vehicle priority detection, and an interactive Tkinter control dashboard.

## Team Members
* **M. Harshavardhan Reddy** (25WU0102152)
* **K. Pranay** (25WU0102328)
* **M. Sai Manoj** (25WU0102139)
* **M. Manoj Sri Sathya Charan** (25WU0102169)
* **Y. Abhinav Sri Ram** (25WU0101158)

**Faculty Mentor:** Prof. Geeta Tripathi

---

## Key Features
* **Multi-Lane Priority Scheduling:** Monitors 4 distinct approach lanes concurrently using perspective-calibrated Region of Interest (ROI) masks to adjust green signal cycles dynamically based on pixel density.
* **Automated Emergency Preemption:** Uses YOLOv8 object detection combined with red/blue HSV strobe light variance checks to grant immediate green light priority to approaching emergency vehicles.
* **Interactive Control Dashboard:** Features a Tkinter desktop GUI complete with video streaming controls, live signal indicator lights (Red/Green), and a real-time event log console.
* **Performance Analytics & CSV Logging:** Automatically logs frame-by-frame density, latency (ms), and active signal states to `traffic_performance_log.csv`, generating visual performance charts via `plot_metrics.py`.

---

## Tech Stack
* **Language:** Python 3
* **Libraries & AI:** OpenCV, NumPy, Ultralytics YOLOv8, Tkinter, Matplotlib, Pandas
* **Development:** VS Code, Git/GitHub

---

## Installation & Usage

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/harsha271106/smart-traffic-vision.git](https://github.com/harsha271106/smart-traffic-vision.git)
   cd smart-traffic-vision