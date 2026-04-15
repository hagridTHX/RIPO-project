import pyautogui
import time
import math

class GestureController:
    def __init__(self):
        # Disable fail-safe for uninterrupted gesture control
        pyautogui.FAILSAFE = False
        self.last_gesture = "No gesture"
        self.last_gesture_confidence = 0.0
        self.last_gesture_time = 0
        self.gesture_display_duration = 0.3  # Show gesture for 0.3 seconds
        
        # Debounce setup
        self.last_click_time = 0
        self.click_cooldown = 0.15  # Very short cooldown to allow double-clicks
        self.second_click_time = 0  # Track double-click timing
        self.double_click_threshold = 0.4  # Time window for double-click

        self.last_scroll_time = 0
        self.scroll_cooldown = 0.05 

        self.last_swipe_time = 0
        self.swipe_cooldown = 1.0   
        
        self.last_log_time = 0      
        self.log_cooldown = 1.0 

        self.wrist_history = []
        
        # Get screen dimensions for cursor control
        self.screen_width, self.screen_height = pyautogui.size()
        self.cursor_smoothing = 0.3  # Smoothing factor (0-1): lower = more responsive, higher = smoother
        self.last_cursor_x = self.screen_width / 2
        self.last_cursor_y = self.screen_height / 2
        
        # Frame dimensions - will be set when processing first frame
        self.frame_width = 640   # Default, will be updated
        self.frame_height = 480  # Default, will be updated
        
        # Momentum system for edge reach
        self.position_history = []  # Track hand position for velocity calculation
        self.momentum_x = 0.0  # Accumulated momentum in X direction
        self.momentum_y = 0.0  # Accumulated momentum in Y direction
        self.momentum_friction = 0.85  # Decay factor (0.85 = 15% loss per frame)
        self.velocity_threshold = 0.3  # Hand velocity threshold for momentum
        self.momentum_scale = 2.0  # How much to amplify momentum
    
    def detect_open_hand(self, hand_landmarks):
        """
        Detect if hand is FULLY OPEN (all fingers extended)
        Optimized for fast performance
        """
        palm_center = (hand_landmarks[0].x, hand_landmarks[0].y)
        
        # Pre-cached finger tip indices for performance
        finger_tips = [4, 8, 12, 16, 20]
        min_distance = 0.09
        
        # Quick check: all fingertips must be extended from palm
        for tip_idx in finger_tips:
            tip = hand_landmarks[tip_idx]
            dx = tip.x - palm_center[0]
            dy = tip.y - palm_center[1]
            # Use squared distance to avoid sqrt (faster)
            dist_sq = dx * dx + dy * dy
            if dist_sq < (min_distance * min_distance):
                return False
        
        # Check thumb-index separation (not pinching)
        thumb = hand_landmarks[4]
        index = hand_landmarks[8]
        thumb_dx = thumb.x - index.x
        thumb_dy = thumb.y - index.y
        thumb_index_dist_sq = thumb_dx * thumb_dx + thumb_dy * thumb_dy
        if thumb_index_dist_sq < (0.07 * 0.07):  # (~0.07 separation)
            return False
        
        return True
    
    def calculate_hand_velocity(self, hand_landmarks, current_time):
        """
        Calculate current hand velocity from position history
        Returns velocity magnitude (units per second)
        """
        # Add current position to history
        hand_x = hand_landmarks[0].x
        hand_y = hand_landmarks[0].y
        self.position_history.append((current_time, hand_x, hand_y))
        
        # Keep only last 0.1 seconds of history (for accurate velocity)
        self.position_history = [
            pos for pos in self.position_history 
            if current_time - pos[0] < 0.1
        ]
        
        # Calculate velocity if we have enough history
        if len(self.position_history) >= 2:
            oldest_time, oldest_x, oldest_y = self.position_history[0]
            dt = current_time - oldest_time
            
            if dt > 0.01:  # Need some time elapsed
                dx = hand_x - oldest_x
                dy = hand_y - oldest_y
                velocity = math.sqrt(dx*dx + dy*dy) / dt
                return velocity, (dx/dt, dy/dt)  # Return velocity and direction
        
        return 0.0, (0.0, 0.0)
    def move_cursor_to_hand_position(self, hand_landmarks, current_time):
        """
        Direct cursor mapping with velocity-based momentum:
        - Fast movement: momentum helps reach edges
        - Slow movement: direct control only (precise clicking)
        """
        # Get wrist position (normalized 0.0-1.0 from camera)
        hand_x = hand_landmarks[0].x
        hand_y = hand_landmarks[0].y
        
        # Calculate hand velocity
        velocity, (vel_x, vel_y) = self.calculate_hand_velocity(hand_landmarks, current_time)
        
        # Determine if we should apply momentum
        if velocity > self.velocity_threshold:
            # Fast movement: activate momentum in direction of movement
            # Amplify the velocity for momentum effect
            self.momentum_x = vel_x * self.momentum_scale
            self.momentum_y = vel_y * self.momentum_scale
        else:
            # Slow movement: apply friction decay (lose momentum gradually)
            self.momentum_x *= self.momentum_friction
            self.momentum_y *= self.momentum_friction
            
            # Stop momentum completely if very small
            if abs(self.momentum_x) < 0.001:
                self.momentum_x = 0
            if abs(self.momentum_y) < 0.001:
                self.momentum_y = 0
        
        # Scale mapping - adjusted for 16:10 aspect ratio
        # Map hand's natural movement range to full screen
        scale_x_min = 0.03
        scale_x_max = 0.97
        scale_y_min = 0.15    # Hand naturally starts ~15% from top
        scale_y_max = 0.85    # Hand naturally reaches ~85% down
        
        # Map from camera range to screen range
        target_x = (hand_x - scale_x_min) / (scale_x_max - scale_x_min) * self.screen_width
        target_y = (hand_y - scale_y_min) / (scale_y_max - scale_y_min) * self.screen_height
        
        # Apply momentum (adds to cursor position independently)
        target_x += self.momentum_x
        target_y += self.momentum_y
        
        # Clamp to screen bounds
        target_x = max(0, min(self.screen_width - 1, target_x))
        target_y = max(0, min(self.screen_height - 1, target_y))
        
        # Apply smoothing (lower = more responsive)
        smooth_x = (self.last_cursor_x * self.cursor_smoothing + 
                   target_x * (1 - self.cursor_smoothing))
        smooth_y = (self.last_cursor_y * self.cursor_smoothing + 
                   target_y * (1 - self.cursor_smoothing))
        
        # Move cursor only if changed significantly (reduce pyautogui calls)
        if abs(smooth_x - self.last_cursor_x) > 0.5 or abs(smooth_y - self.last_cursor_y) > 0.5:
            pyautogui.moveTo(int(smooth_x), int(smooth_y), duration=0)
        
        # Update position for next frame
        self.last_cursor_x = smooth_x
        self.last_cursor_y = smooth_y
    
    def process_landmarks(self, hand_landmarks, gestures, idx, current_time, frame_height=480, frame_width=640):
        # Update frame dimensions if provided
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        gesture_recognized = ""
        gesture_confidence = 0.0

        # PRIORITY 1: Check for pinch-to-click (thumb + index VERY close AND all other fingers extended)
        thumb_tip = hand_landmarks[4]
        index_tip = hand_landmarks[8]
        middle_tip = hand_landmarks[12]
        ring_tip = hand_landmarks[16]
        pinky_tip = hand_landmarks[20]
        
        palm_center = (hand_landmarks[0].x, hand_landmarks[0].y)
        
        pinch_distance = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
        middle_distance = math.hypot(middle_tip.x - palm_center[0], middle_tip.y - palm_center[1])
        ring_distance = math.hypot(ring_tip.x - palm_center[0], ring_tip.y - palm_center[1])
        pinky_distance = math.hypot(pinky_tip.x - palm_center[0], pinky_tip.y - palm_center[1])
        
        # For a real pinch click:
        # - Thumb and index must be EXTREMELY close (< 0.035)
        # - AND ALL other fingers must be clearly extended (> 0.12 each)
        # This ensures it's a deliberate pinch, not a transition between gestures
        all_fingers_extended = (middle_distance > 0.12 and ring_distance > 0.12 and pinky_distance > 0.12)
        
        if pinch_distance < 0.035 and all_fingers_extended:
            gesture_recognized = "Click"
            gesture_confidence = 1.0
            if current_time - self.last_click_time > self.click_cooldown:
                # Stop momentum when clicking (for precise clicks)
                self.momentum_x = 0
                self.momentum_y = 0
                
                # Check for double-click (two clicks within threshold)
                time_since_last = current_time - self.second_click_time
                if time_since_last < self.double_click_threshold:
                    # This is a double-click!
                    print(f"[{current_time:.1f}] Action: Double-Click")
                    pyautogui.doubleClick()
                    self.second_click_time = 0  # Reset for next sequence
                else:
                    # Single click
                    print(f"[{current_time:.1f}] Action: Click (pinch: {pinch_distance:.3f})")
                    pyautogui.click()
                    self.second_click_time = current_time  # Set for potential next click
                
                self.last_click_time = current_time
        
        # PRIORITY 2: Check for swipes (wrist movement)
        elif gesture_recognized == "":
            wrist_x = hand_landmarks[0].x
            self.wrist_history.append((current_time, wrist_x))
            
            # Keep only recent 0.4 seconds of movement data
            self.wrist_history = [history for history in self.wrist_history if current_time - history[0] < 0.4]

            # Calculate swipe velocity - need at least 2 points (reduced from 3)
            if len(self.wrist_history) > 1:
                oldest_time, oldest_x = self.wrist_history[0]
                dx = wrist_x - oldest_x
                dt = current_time - oldest_time
                
                if dt > 0.03:  # Reduced from 0.04 to catch earlier
                    velocity = dx / dt
                    
                    # Much more lenient thresholds for fast swipes
                    if dx < -0.08 and velocity < -0.30:
                        gesture_recognized = "Left swipe"
                        gesture_confidence = 1.0
                        if current_time - self.last_swipe_time > self.swipe_cooldown:
                            print(f"[{current_time:.1f}] Action: Browser back (velocity: {velocity:.2f})")
                            pyautogui.hotkey('browserback')
                            self.last_swipe_time = current_time
                        self.wrist_history = [] 
                        
                    elif dx > 0.08 and velocity > 0.30:
                        gesture_recognized = "Right swipe"
                        gesture_confidence = 1.0
                        if current_time - self.last_swipe_time > self.swipe_cooldown:
                            print(f"[{current_time:.1f}] Action: Browser forward (velocity: {velocity:.2f})")
                            pyautogui.hotkey('browserforward')
                            self.last_swipe_time = current_time
                        self.wrist_history = []
        
        # PRIORITY 3: Check for thumb gestures (from MediaPipe classifier)
        if gesture_recognized == "":
            if gestures and len(gestures) > idx:
                top_gesture = gestures[idx][0].category_name
                gesture_confidence = gestures[idx][0].score
                
                if top_gesture == "Thumb_Up":
                    gesture_recognized = "Thumb Up"
                    if current_time - self.last_log_time > self.log_cooldown:
                        print(f"[{current_time:.1f}] Action: Scroll up")
                        self.last_log_time = current_time
                    
                    if current_time - self.last_scroll_time > self.scroll_cooldown:
                        pyautogui.scroll(120) 
                        self.last_scroll_time = current_time
                        
                elif top_gesture == "Thumb_Down":
                    gesture_recognized = "Thumb Down"
                    if current_time - self.last_log_time > self.log_cooldown:
                        print(f"[{current_time:.1f}] Action: Scroll down")
                        self.last_log_time = current_time
                    
                    if current_time - self.last_scroll_time > self.scroll_cooldown:
                        pyautogui.scroll(-120) 
                        self.last_scroll_time = current_time
        
        # PRIORITY 4: If no other gesture detected, check for FULL OPEN HAND (cursor movement)
        if gesture_recognized == "":
            if self.detect_open_hand(hand_landmarks):
                self.move_cursor_to_hand_position(hand_landmarks, current_time)
                gesture_recognized = "Cursor Mode"
                gesture_confidence = 1.0
        
        # Store last recognized gesture for display (keeps showing for duration)
        if gesture_recognized:
            self.last_gesture = gesture_recognized
            self.last_gesture_confidence = gesture_confidence
            self.last_gesture_time = current_time
        elif current_time - self.last_gesture_time > self.gesture_display_duration:
            # Clear gesture display after display duration expires
            self.last_gesture = "No gesture"
            self.last_gesture_confidence = 0.0
