# RIPO Project - Code Documentation

## Project Overview
RIPO is a gesture recognition system that uses hand landmarks and MediaPipe to control system functions (mouse clicks, scrolling, page navigation) through hand gestures captured via webcam at 60 FPS.

---

## File: main.py

### Function: main()
**Location:** Lines 5-70

**Purpose:** Entry point of the application that sets up video capture, initializes gesture recognition, and processes video frames in real-time.

**What it does:**
- Line 6: Initializes the gesture recognizer model and configuration options
- Line 7: Creates a GestureController instance to handle gesture-based actions
- Lines 9-18: Defines hand skeleton connections (21 landmark points connected to form a hand outline)
- Lines 20-22: Opens webcam (device 0) and sets resolution to 640x480 pixels
- Lines 24-25: Initializes timing variables for FPS calculation (targeting 60 FPS)
- Lines 27: Prints startup message (in Polish)
- Lines 29-70: Main loop that:
  - Line 31: Captures video frames from webcam
  - Line 32: Breaks loop if frame capture fails
  - Lines 34-37: Calculates FPS by measuring time between frames and skips frame if too fast
  - Line 39: Flips frame horizontally (mirror effect)
  - Line 40: Converts frame from BGR to RGB color space
  - Line 42: Converts frame to MediaPipe Image format
  - Line 43: Gets current timestamp in milliseconds
  - Line 45: Runs gesture recognizer on the frame
  - Lines 47-66: If hand landmarks detected, draws hand skeleton on frame (lines and circles for joints) and processes landmarks for gestures
  - Line 68: Clears gesture history if no hand detected
  - Line 70: Displays FPS counter on frame
  - Line 71: Displays video stream with window title
  - Lines 73-74: Exits loop if 'q' key is pressed
- Lines 76-77: Releases webcam and closes all OpenCV windows

**Key Details:**
- Uses MediaPipe hand landmark detection (21 points per hand)
- Runs at 60 FPS for smooth gesture recognition
- Displays real-time hand skeleton overlay on video feed
- Calls GestureController to process hand movements and perform actions

---

## File: model_setup.py

### Function: initialize_recognizer()
**Location:** Lines 5-25

**Purpose:** Sets up and configures the MediaPipe gesture recognizer model, downloading if necessary.

**What it does:**
- Line 6: Defines URL to the pre-trained gesture recognizer model
- Line 7: Sets local model file path
- Lines 8-10: Checks if model exists locally; if not, downloads from URL
- Lines 12-14: Imports MediaPipe task components for gesture recognition
- Line 15: Imports the vision running mode enumeration
- Lines 17-23: Creates GestureRecognizerOptions with:
  - Model asset path (line 18)
  - Running mode set to VIDEO for real-time processing (line 19)
  - Maximum 1 hand detection (line 20)
  - Confidence thresholds set to 0.7 (70%) for hand detection, presence, and tracking (lines 21-23)
- Line 25: Returns GestureRecognizer class and configured options

**Key Details:**
- Automatically downloads model on first run (about 50-100 MB)
- Configures model for single hand tracking
- High confidence thresholds reduce false detections
- Returns objects needed for video frame processing in main()

---

## File: actions.py

### Class: GestureController

#### Method: __init__()
**Location:** Lines 4-18

**Purpose:** Initialize gesture controller with timing parameters for debouncing actions and history tracking.

**What it does:**
- Line 6: Disables PyAutoGUI fail-safe (prevents cursor escape)
- Lines 9-10: Sets up click debounce timer (prevent multiple clicks with minimum 1 second between them)
- Lines 12-13: Sets up scroll debounce timer (allow scrolls every 0.05 seconds)
- Lines 15-16: Sets up swipe debounce timer (prevent multiple swipes with minimum 1 second between them)
- Lines 18-19: Sets up logging cooldown (print status only every 1 second)
- Line 21: Initializes empty wrist history list to track hand position over time

**Key Details:**
- Debounce timings prevent accidental multiple actions from jittery gesture recognition
- Cooldowns fine-tuned for 60 FPS operation
- Wrist history used for swipe gesture detection

#### Method: process_landmarks()
**Location:** Lines 23-99

**Purpose:** Analyzes hand landmarks and detected gestures to perform corresponding system actions (clicks, scrolling, page navigation).

**What it does:**

**Dynamic Gestures (Swipes) - Lines 26-56:**
- Line 27: Extracts wrist X-coordinate (first landmark)
- Line 28: Adds current wrist position and timestamp to history
- Line 31: Removes history entries older than 0.4 seconds (keeps recent motion)
- Lines 34-56: If enough history data exists (3+ frames):
  - Calculates horizontal displacement (dx) and time delta (dt)
  - Lines 39-40: Calculates wrist velocity
  - Lines 43-50: LEFT SWIPE detection (dx < -0.15, velocity < -0.6):
    - Triggers browser back button if 1+ second since last swipe
    - Clears history to avoid repeating
  - Lines 52-56: RIGHT SWIPE detection (dx > 0.15, velocity > 0.6):
    - Triggers browser forward button if 1+ second since last swipe
    - Clears history to avoid repeating

**Static Gestures (Thumb/Click) - Lines 59-83:**
- Lines 61-65: PINCH TO CLICK detection:
  - Measures distance between thumb tip (landmark 4) and index finger tip (landmark 8)
  - If distance < 0.05 (fingers pinched):
    - Performs mouse click if 1+ second since last click
- Lines 67-83: THUMB gestures (requires MediaPipe gesture classification):
  - Line 68: Gets top classified gesture for current hand
  - Lines 70-74: THUMB_UP or THUMB_DOWN detected:
    - Logs scroll direction if 1+ second since last log
  - Lines 76-78: THUMB_UP:
    - Scrolls up by 120 pixels if 0.05+ seconds since last scroll
  - Lines 80-82: THUMB_DOWN:
    - Scrolls down by 120 pixels if 0.05+ seconds since last scroll

**Key Details:**
- Supports 5 distinct gesture actions (left swipe, right swipe, click, scroll up, scroll down)
- Uses velocity calculation for motion-based gestures (more reliable than position alone)
- Debounce system prevents accidental repeated actions
- Processes one hand only (idx parameter allows multi-hand support in future)

#### Method: clear_history()
**Location:** Lines 85-91

**Purpose:** Placeholder for clearing gesture history (not actively used due to auto-expiration logic).

**What it does:**
- Line 85-91: Empty implementation with comment explaining that wrist history auto-clears after 0.4 seconds instead of clearing on every missed frame

**Key Details:**
- History automatically expires old data, so explicit clearing not needed
- Prevents false swipe detections from motion blur at 60 FPS

---

## Summary of Gesture Actions
| Gesture | Action | Cooldown |
|---------|--------|----------|
| Left Swipe | Browser Back | 1.0 second |
| Right Swipe | Browser Forward | 1.0 second |
| Thumb + Index Pinch | Mouse Click | 1.0 second |
| Thumb Up | Scroll Up | 0.05 seconds |
| Thumb Down | Scroll Down | 0.05 seconds |

---

## Dependencies
- **opencv-python**: Video capture and frame display/rendering
- **mediapipe**: Hand landmark detection and gesture classification
- **PyAutoGUI**: System control (mouse clicks, scrolling, keyboard shortcuts)
