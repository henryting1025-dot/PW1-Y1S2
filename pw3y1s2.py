import cv2
import numpy as np
import time
import threading
import sys
from picamera2 import Picamera2
from gpiozero import Motor

# --- 1. Hardware Setup ---
# Using inverted motor configuration
motor_right = Motor(forward=23, backward=24, enable=25)
motor_left  = Motor(forward=17, backward=27, enable=22)

# --- 2. PID & Speed Settings ---
Kp, Kd = 0.02, 0.008 
SPEED_BASE = 0.30
SEARCH_SPEED = 0.70  # Fast pivot for 90-degree corners
last_error = 0

# --- 3. AI Threading ---
CLASSES = ["Fingerprint", "QR", "Recycle", "arrow left", "arrow right", "arrow up", "stop"]
current_ai_label = None
ai_frame = None
running = True
data_lock = threading.Lock()

try:
    net = cv2.dnn.readNetFromONNX("best.onnx")
    print("--- AI MODEL LOADED SUCCESSFULLY ---")
except Exception as e:
    print(f"--- MODEL LOAD ERROR: {e} ---")
    net = None

def ai_thread_func():
    global current_ai_label, ai_frame, running
    while running:
        if ai_frame is not None and net is not None:
            try:
                img = ai_frame.copy()
                blob = cv2.dnn.blobFromImage(img, 1/255.0, (320, 320), swapRB=False, crop=False)
                net.setInput(blob)
                preds = net.forward()
                out = np.squeeze(preds)
                if out.shape[0] < out.shape[1]: out = out.T
                conf_scores = out[:, 4:]
                max_scores = np.max(conf_scores, axis=1)
                best_idx = np.argmax(max_scores)
                
                with data_lock:
                    if max_scores[best_idx] > 0.55:
                        current_ai_label = CLASSES[np.argmax(conf_scores[best_idx])]
                    else:
                        current_ai_label = None
            except: pass
        time.sleep(0.05)

thread = threading.Thread(target=ai_thread_func, daemon=True)
thread.start()

# --- 4. Camera Setup ---
def limit(val):
    return float(max(-0.95, min(0.95, val)))

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (320, 240)})
picam2.configure(config)
picam2.start()

search_direction = 1
ignore_until = 0
blind_navigation = False 

print("--- SYSTEM READY: MONITORING FOR SYMBOLS ---")

try:
    while True:
        frame = picam2.capture_array()
        ai_frame = frame 
        
        # --- STEP A: AI ACTION LOGIC (WITH PRINTS) ---
        if not blind_navigation:
            with data_lock:
                detected = current_ai_label
            
            if detected is not None and time.time() > ignore_until:
                # This prints to the terminal whenever a symbol is recognized
                print(f"\n>>> [AI DETECTED]: {detected} <<<")
                sys.stdout.flush() 
                
                if detected == "stop":
                    motor_left.stop(); motor_right.stop()
                    time.sleep(3.0)
                    ignore_until = time.time() + 2.0
                
                elif detected == "Recycle":
                    print("ACTION: Blinding eyes for 12s Recycle spin...")
                    blind_navigation = True
                    # Rotate 360 (Adjust signs if spin direction is wrong)
                    motor_left.value = 1.0; motor_right.value = -1.0
                    time.sleep(12.0) 
                    motor_left.stop(); motor_right.stop()
                    blind_navigation = False
                    ignore_until = time.time() + 2.0
                
                # Arrows are kept to help the navigation bias
                if "arrow" not in detected:
                    with data_lock: 
                        current_ai_label = None
                continue

        # --- STEP B: NAVIGATION LOGIC ---
        if not blind_navigation:
            roi = frame[170:240, 0:320]
            hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
            
            # Masks
            mask_r = cv2.bitwise_or(cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255])), 
                                   cv2.inRange(hsv, np.array([160, 50, 50]), np.array([179, 255, 255])))
            mask_y = cv2.inRange(hsv, np.array([77, 181, 172]), np.array([122, 220, 225]))
            _, mask_b = cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY), 80, 255, cv2.THRESH_BINARY_INV)

            active_mask = None
            is_red = False
            
            if cv2.countNonZero(mask_r) > 30: 
                active_mask = mask_r
                is_red = True 
            elif cv2.countNonZero(mask_y) > 30: 
                active_mask = mask_y
            elif cv2.countNonZero(mask_b) > 120: 
                active_mask = mask_b

            if active_mask is not None:
                M = cv2.moments(active_mask)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    error = 160 - cx
                    steering = (Kp * error) + (Kd * (error - last_error))
                    
                    if is_red:
                        # FORCED RIGHT EXIT (For inverted hardware)
                        motor_left.value = -0.5
                        motor_right.value = 0.85
                    else:
                        # NORMAL NAVIGATION
                        motor_left.value = limit(SPEED_BASE + steering)
                        motor_right.value = limit(SPEED_BASE - steering)
                    
                    search_direction = 1 if error > 0 else -1
                    last_error = error
            else:
                # 90-DEGREE RECOVERY (Fast pivot)
                motor_left.value = limit(SEARCH_SPEED * search_direction)
                motor_right.value = limit(-SEARCH_SPEED * search_direction)

except KeyboardInterrupt:
    running = False
finally:
    running = False
    motor_left.stop()
    motor_right.stop()
    picam2.stop()
    print("\n--- SYSTEM SHUTDOWN CLEANLY ---")
