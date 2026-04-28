# -*- coding: utf-8 -*-
import cv2
import numpy as np
from picamera2 import Picamera2
from gpiozero import Motor

# --- 1. Hardware & PID Setup ---
motor_right = Motor(forward=23, backward=24, enable=25)
motor_left  = Motor(forward=17, backward=27, enable=22)
SPEED_BASE = 0.70
setpoint = 160 

# --- 2. Camera Initialization ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (320, 240)})
picam2.configure(config)
picam2.start()

def get_shape(frame_rgb, frame_gray):
    """
    The Ultimate Identifier: Handles Solid, Fragmented, and Hollow Boss Shapes.
    """
    blurred = cv2.GaussianBlur(frame_gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 150, 255, cv2.THRESH_BINARY_INV)
    
    # Morphological Net for Grouping
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
    grouped_thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    grouped_contours, _ = cv2.findContours(grouped_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for g_cnt in grouped_contours:
        x, y, w, h = cv2.boundingRect(g_cnt)
        bbox_area = w * h
        
        # Noise Filter
        if bbox_area < 800: continue 
        if x < 5 or y < 5 or (x + w) > 315 or (y + h) > 235: continue

        roi_original = thresh[y:y+h, x:x+w]
        sub_contours, _ = cv2.findContours(roi_original, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        fragment_count = len(sub_contours)
        
        shape_name = "Unknown"
        debug_val = 0.0 # Used to show the Fill Ratio on screen

        # --- A. FRAGMENTED PATTERNS ---
        # --- A. FRAGMENTED PATTERNS ---
        if fragment_count >= 3:
            g_area = cv2.contourArea(g_cnt)
            g_hull = cv2.convexHull(g_cnt)
            g_solidity = g_area / cv2.contourArea(g_hull) if cv2.contourArea(g_hull) > 0 else 0
            g_extent = g_area / bbox_area if bbox_area > 0 else 0
            
            # ??????? (FR)
            actual_pixels = cv2.countNonZero(roi_original)
            roi_fill = actual_pixels / bbox_area if bbox_area > 0 else 0
            debug_val = roi_fill
            
            # --- ?????? Push Button ---
            # ??????,??????(>0.55),???????????(<15),????!
            if roi_fill > 0.55 and fragment_count < 15:
                shape_name = "Push Button"
            elif g_extent > 0.82: 
                shape_name = "QR Code"
            elif fragment_count == 3 and g_solidity < 0.72: 
                shape_name = "Recycle"
            elif roi_fill < 0.25: 
                shape_name = "Warning"
            else: 
                shape_name = "Fingerprint"
            
        # --- B. SOLID & HOLLOW SHAPES ---
        elif fragment_count > 0:
            main_cnt = max(sub_contours, key=cv2.contourArea)
            m_area = cv2.contourArea(main_cnt)
            if m_area < 400: continue 
            
            mx, my, mw, mh = cv2.boundingRect(main_cnt)
            exact_roi = roi_original[my:my+mh, mx:mx+mw]
            
            # --- ULTIMATE BOSS FILTER: HOLLOWNESS (FILL RATIO) ---
            # How much of the mathematical area is actually painted white?
            actual_pixels = cv2.countNonZero(exact_roi)
            fill_ratio = actual_pixels / m_area if m_area > 0 else 0
            debug_val = fill_ratio
            
            if fill_ratio < 0.40:
                # Mostly empty space -> Warning Sign
                shape_name = "Warning"
            elif 0.40 <= fill_ratio < 0.82:
                # Solid block with massive holes -> Push Button
                shape_name = "Push Button"
            else:
                # --- C. STANDARD SOLID SHAPES (fill_ratio > 0.82) ---
                M = cv2.moments(main_cnt)
                dx, dy = 0, 0
                if M["m00"] != 0:
                    dx = (M["m10"] / M["m00"]) - (mx + mw / 2)
                    dy = (M["m01"] / M["m00"]) - (my + mh / 2)
                
                # Check Solidity first to avoid confusing 3/4 circle with arrows
                hull = cv2.convexHull(main_cnt)
                solidity = m_area / cv2.contourArea(hull) if cv2.contourArea(hull) > 0 else 0
                
                if solidity > 0.75:
                    v = len(cv2.approxPolyDP(main_cnt, 0.015 * cv2.arcLength(main_cnt, True), True))
                    if 0.75 <= solidity <= 0.92: shape_name = "3/4 Circle"
                    elif v == 4: shape_name = "Trapezium" if (m_area/(mw*mh)) > 0.65 else "Diamond"
                    elif v == 8: shape_name = "Octagon"
                    else: shape_name = "Circle/Curve"
                else:
                    if abs(dx) > 1.5 or abs(dy) > 1.5:
                        if abs(dx) > abs(dy): shape_name = "Arrow Right" if dx > 0 else "Arrow Left"
                        else: shape_name = "Arrow Down" if dy > 0 else "Arrow Up"
                    else:
                        v = len(cv2.approxPolyDP(main_cnt, 0.015 * cv2.arcLength(main_cnt, True), True))
                        if v == 10: shape_name = "Star"
                        elif v == 12: shape_name = "Cross"

        # --- Visual Feedback ---
        cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # Showing FR (Fill Ratio) on screen so you can see the magic happen!
        cv2.putText(frame_rgb, f"{shape_name} (FR:{debug_val:.2f})", (x, y - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    
    return grouped_thresh

try:
    print("[SYSTEM] Ultimate Boss-Beater Mode Started...")
    while True:
        frame = picam2.capture_array()
        display_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        bw_mask = get_shape(display_frame, gray)
        
        cv2.imshow("Human View", display_frame)
        enlarged_bw = cv2.resize(bw_mask, (640, 480), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Computer View", enlarged_bw)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    motor_left.stop(); motor_right.stop(); picam2.stop(); cv2.destroyAllWindows()
