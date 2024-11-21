import cv2
import time
import serial
from camera_functions import *
from control_functions import *
from window_menager import *

def Main_Loop(URL):
    
    continue_streaming_global = True #Controls the following cycle while. if someone press r it enables to restart the whole code, take a new image and run again the code

    # Set up the serial connection to the ESP32
    esp32 = serial.Serial(port='COM9', baudrate=115200, timeout=1)
    time.sleep(2)  # Give the ESP32 time to reset and initialize

    while continue_streaming_global:    
        
        [i_1,i_2] = move_motors(no_ref_motor1,no_ref_motor2,esp32)
        
        cap = cv2.VideoCapture(URL) # Starting the video stream capture.
        success, initial_frame = cap.read() # Reading the video stream. Taking a new initial frame as a reference picture for difference calculations
        
        [i_1,i_2] = move_motors(yes_ref_motor1,yes_ref_motor2,esp32)
        
        if not cap.isOpened():
            print("Failed to connect to the video stream.")
            return
        
        # Show xy directions in the image
        cv2.arrowedLine(frame, (0, 0), (40, 0), (255, 0, 0), 2)  # x direction
        cv2.arrowedLine(frame, (0, 0), (0, 40), (255, 0, 0), 2)  # y direction
        cv2.putText(frame, 'x', (45, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA) # x label
        cv2.putText(frame, 'y', (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA) # y label

        # Initialize the tracker
        tracker = cv2.TrackerKCF_create()  # Use KCF tracker | Initialize the tracking of the camera. The user draws a square on the initial frame where the plant is.
        bbox_initialized = False

        continue_streaming = True
        
        while continue_streaming_global and continue_streaming:
            success, frame = cap.read() # Read a new frame
            if not success:
                break

            # Create a copy of the frame before any drawing operations
            frame_copy = frame.copy()

            # Initialize the bounding box for tracking on the first frame
            if not bbox_initialized:
                bbox = cv2.selectROI("Video Stream", frame, False)
                tracker.init(frame, bbox)
                bbox_initialized = True

            # Update tracker - Update position of the plant
            success, bbox = tracker.update(frame)
            if success:
                (x_p, y_p, w, h) = [int(v) for v in bbox]
                cv2.rectangle(frame, (x_p, y_p), (x_p + w, y_p + h), (0, 255, 0), 2, 1)
                print(f"Object detected at coord = X:{(x_p + w) / 2} | Y:{(y_p + h) / 2}")
            else:
                cv2.putText(frame, "Tracking failure", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

            # Reflection detection using thresholded differences on unaltered frame_copy
            reflection_xy = find_reflection(initial_frame, frame_copy, threshold_value_min, threshold_value_max, area_value_min, area_value_max)
            if reflection_xy[1]:
                cv2.circle(frame, reflection_xy[0], 10, (0, 0, 255), 2)
                x_r = reflection_xy[0][0]
                y_r = reflection_xy[0][1]
                dx = x_r - x_p
                dy = y_r - y_p
                [i_1,i_2] = control_motors(dx,dy,i_1,i_2)
                # Draw an arrow from (x_r, y_r) to (x_r + i_1, y_r + i_2)
                cv2.arrowedLine(frame, (x_r, y_r), (x_r + int(i_1), y_r + int(i_2)), (255, 0, 0), 2)

            # Display images with updated threshold in real-time
            resized_gray_diff = cv2.resize(reflection_xy[2], (400, 400))  # Resize as needed
            resized_threshold = cv2.resize(reflection_xy[3], (400, 400))
            resized_frame = cv2.resize(frame, (400, 400))

            # Show the resized images in separate windows
            cv2.imshow("Gray scale difference", resized_gray_diff)
            cv2.imshow("Threshold", resized_threshold)
            cv2.imshow("Video Stream", resized_frame)

            # Move each window to a specific position on the screen
            cv2.moveWindow("Gray scale difference", 0, 0)
            cv2.moveWindow("Threshold", 420, 0)
            cv2.moveWindow("Video Stream", 840, 0)

            key = cv2.waitKey(3)
            if key == ord('q'):
                continue_streaming_global = False
                break
            if key == ord('r'):
                continue_streaming = False
                break
            
            time.sleep(2)

        cap.release()
        cv2.destroyAllWindows()