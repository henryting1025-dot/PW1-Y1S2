from gpiozero import Motor
from time import sleep

# --- 1. Pin Configuration ---
# Right Motor
motor_right = Motor(forward=23, backward=24, enable=25)
# Left Motor
motor_left  = Motor(forward=17, backward=27, enable=22)

# ==========================================
#      CALIBRATION AREA (UPDATED)
# ==========================================

# A. Linear Calibration
MEASURED_PWM = 140
MEASURED_SPEED_CM_S = 29.7
SPEED_RATIO = MEASURED_PWM / MEASURED_SPEED_CM_S 

# B. Turning Calibration
# UPDATED: Based on "360 input = 180 actual"
# The robot is turning slower than we thought (approx 90 deg/s)
TURN_POWER = 0.6            
TURN_SPEED_DEG_S = 90.0     # <--- UPDATED FROM 180.0 TO 90.0

# ==========================================

def get_duty_cycle_from_speed(target_speed):
    required_pwm = target_speed * SPEED_RATIO
    if required_pwm > 255: 
        required_pwm = 255
    return required_pwm / 255

# --- Main Program ---

try:
    print("=== Robot Control Menu ===")
    print("1. Move Straight (Distance)")
    print("2. Turn (Angle)")
    
    mode = input("Choose Mode (1 or 2): ").strip()

    if mode == '1':
        # --- MODE 1: STRAIGHT ---
        dist = float(input("Enter Distance (cm): "))
        speed = float(input("Enter Speed (cm/s): "))
        direction = input("Direction (f=Forward, b=Backward): ").lower().strip()

        duration = dist / speed
        power = get_duty_cycle_from_speed(speed)

        print(f"\n[Plan] Moving {direction.upper()} for {duration:.2f}s...")
        sleep(1)

        if direction == 'f':
            motor_right.forward(power)
            motor_left.forward(power)
        elif direction == 'b':
            motor_right.backward(power)
            motor_left.backward(power)
        else:
            print("Error: Invalid direction.")
            exit()
        
        sleep(duration)

    elif mode == '2':
        # --- MODE 2: TURN ---
        angle = float(input("Enter Angle (e.g., 90, 180, 360): "))
        direction = input("Direction (l=Left, r=Right): ").lower().strip()

        # New Calculation based on 90.0 deg/s
        duration = angle / TURN_SPEED_DEG_S
        
        print(f"\n[Plan] Turning {direction.upper()} {angle} degrees ({duration:.2f}s)...")
        sleep(1)

        if direction == 'l':
            motor_left.backward(TURN_POWER)
            motor_right.forward(TURN_POWER)
        elif direction == 'r':
            motor_left.forward(TURN_POWER)
            motor_right.backward(TURN_POWER)
        else:
            print("Error: Invalid direction.")
            exit()
            
        sleep(duration)

    else:
        print("Invalid Mode.")

    motor_right.stop()
    motor_left.stop()
    print("Done.")

except ValueError:
    print("Error: Invalid number.")
except KeyboardInterrupt:
    print("\nStopped.")
    motor_right.stop()
    motor_left.stop()
