import pyautogui
import time
import math

class GestureController:
    def __init__(self):
        # Zabezpieczenie przed błędem ucieczki kursora
        pyautogui.FAILSAFE = False
        
        # Debounce setup
        self.last_click_time = 0
        self.click_cooldown = 1.0

        self.last_scroll_time = 0
        self.scroll_cooldown = 0.05 

        self.last_swipe_time = 0
        self.swipe_cooldown = 1.0   
        
        self.last_log_time = 0      
        self.log_cooldown = 1.0 

        self.wrist_history = [] 
    
    def process_landmarks(self, hand_landmarks, gestures, idx, current_time):
        gesture_recognized = ""

        # ================= LOGIKA GESTÓW DYNAMICZNYCH (MACHNIĘCIA) =================
        wrist_x = hand_landmarks[0].x
        self.wrist_history.append((current_time, wrist_x))
        
        # Ograniczenie pamięci do ostatnich 0.4s
        self.wrist_history = [history for history in self.wrist_history if current_time - history[0] < 0.4]

        # Wyższa czułość na utratę i zbieranie klatek w 60 FPS
        if len(self.wrist_history) > 3:
            oldest_time, oldest_x = self.wrist_history[0]
            dx = wrist_x - oldest_x
            dt = current_time - oldest_time
            
            # Zapobiegamy dzieleniu przez ekstremalnie małe dt przy 60 fps
            if dt > 0.05:
                velocity = dx / dt
                
                # Złagodzony próg ucięcia ruchu przy 60FPS
                if dx < -0.15 and velocity < -0.6:
                    gesture_recognized = "Machnięcie w lewo"
                    if current_time - self.last_swipe_time > self.swipe_cooldown:
                        print(f"[{current_time:.1f}] Akcja: Cofnięcie strony (Browser Back)")
                        pyautogui.hotkey('browserback')
                        self.last_swipe_time = current_time
                    self.wrist_history = [] 
                    
                elif dx > 0.15 and velocity > 0.6:
                    gesture_recognized = "Machnięcie w prawo"
                    if current_time - self.last_swipe_time > self.swipe_cooldown:
                        print(f"[{current_time:.1f}] Akcja: Powrót do strony (Browser Forward)")
                        pyautogui.hotkey('browserforward')
                        self.last_swipe_time = current_time
                    self.wrist_history = [] 

        # ================= LOGIKA GESTÓW STATYCZNYCH (PYAUTOGUI) =================
        if gesture_recognized == "":
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]
            distance = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
            
            if distance < 0.05:
                # Wymagane dodatkowe zabezpieczenie by skrypt nie klikał ciągle minimalnym ruchem
                if current_time - self.last_click_time > self.click_cooldown:
                    print(f"[{current_time:.1f}] Akcja: KLIKNIĘCIE")
                    pyautogui.click()
                    self.last_click_time = current_time
            
            elif gestures and len(gestures) > idx:
                top_gesture = gestures[idx][0].category_name
                
                if top_gesture in ["Thumb_Up", "Thumb_Down"]:
                    if current_time - self.last_log_time > self.log_cooldown:
                        kierunek = "w górę" if top_gesture == "Thumb_Up" else "w dół"
                        print(f"[{current_time:.1f}] Akcja: Scroll {kierunek}...")
                        self.last_log_time = current_time
                
                if top_gesture == "Thumb_Up":
                    if current_time - self.last_scroll_time > self.scroll_cooldown:
                        pyautogui.scroll(120) 
                        self.last_scroll_time = current_time
                        
                elif top_gesture == "Thumb_Down":
                    if current_time - self.last_scroll_time > self.scroll_cooldown:
                        pyautogui.scroll(-120) 
                        self.last_scroll_time = current_time

    def clear_history(self):
        # Przy 60 FPS szybki ruch dłoni łatwo gubi pojedyncze klatki (motion blur).
        # Zamiast czyścić historię z każdej straconej ramki (co blokowało Swipe), pozwalamy wektorowi oczyścić się samemu po czasie >0.4s
        pass
