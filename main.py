import cv2
import mediapipe as mp
import time
import urllib.request
import os
import math

def main():
    model_url = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
    model_path = "gesture_recognizer.task"
    if not os.path.exists(model_path):
        print("Pobieranie modelu Gesture Recognizer...")
        urllib.request.urlretrieve(model_url, model_path)
        print("Model zostal pobrany.")

    BaseOptions = mp.tasks.BaseOptions
    GestureRecognizer = mp.tasks.vision.GestureRecognizer
    GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = GestureRecognizerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.VIDEO, 
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7
    )

    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),  
        (0, 5), (5, 6), (6, 7), (7, 8),  
        (5, 9), (9, 10), (10, 11), (11, 12),  
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)  
    ]

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    prev_time = 0
    target_fps = 30
    
    last_gesture_time = 0
    gesture_cooldown = 0.5 

    # --- Zmienna do analizy dynamiki ruchu ---
    wrist_history = [] 

    print("Uruchamianie przechwytywania... Wciśnij 'q' aby wyjść.")

    with GestureRecognizer.create_from_options(options) as recognizer:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Nie można pobrać klatki z kamery.")
                break

            current_time = time.time()
            if (current_time - prev_time) < 1.0 / target_fps:
                continue
            fps = 1 / (current_time - prev_time)
            prev_time = current_time

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp_ms = int(current_time * 1000)
            
            results = recognizer.recognize_for_video(mp_image, timestamp_ms)

            if results.hand_landmarks:
                for idx, hand_landmarks in enumerate(results.hand_landmarks):
                    h, w, _ = frame.shape
                    
                    for connection in HAND_CONNECTIONS:
                        start_idx, end_idx = connection
                        start_point = hand_landmarks[start_idx]
                        end_point = hand_landmarks[end_idx]
                        
                        cx_start, cy_start = int(start_point.x * w), int(start_point.y * h)
                        cx_end, cy_end = int(end_point.x * w), int(end_point.y * h)
                        cv2.line(frame, (cx_start, cy_start), (cx_end, cy_end), (0, 0, 255), 2)
                        
                    for landmark in hand_landmarks:
                        cx, cy = int(landmark.x * w), int(landmark.y * h)
                        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), cv2.FILLED)
                        
                    gesture_recognized = ""

                    # ================= LOGIKA RUCHU =================
                    # 1. Analiza pozycji nadgarstka (landmark 0) w czasie
                    wrist_x = hand_landmarks[0].x
                    wrist_history.append((current_time, wrist_x))
                    
                    # Czas okna analizy: 0.4 sekundy
                    wrist_history = [history for history in wrist_history if current_time - history[0] < 0.4]

                    # Szukamy odchyleń tylko jeśli mamy dane z przynajmniej 3 klatek w historii
                    if len(wrist_history) > 3:
                        oldest_time, oldest_x = wrist_history[0]
                        dx = wrist_x - oldest_x
                        dt = current_time - oldest_time
                        
                        velocity = dx / dt if dt > 0 else 0
                        
                        # Obraz jest odwrócony z pomocą cv2.flip (lustrzane odbicie),
                        # Wiadome 'w lewo' dla użytkownika (przed kamerką w jego lewo)
                        # oznacza zjazd współrzędnych X od dużych (+1.0 z prawej monitora)
                        # po małe (np. 0.0), czyli dx jest mocno ujemne.
                        # Ustawiamy pułap przyspieszenia (-0.8 znormalizowanego obrazu/sek) i wymaganą zmianę odległości (-20% ekranu)
                        if dx < -0.2 and velocity < -0.8:
                            gesture_recognized = "Machnięcie w lewo"
                            wrist_history = [] # Zresetuj historię by uniknąć zapętlania gestu
                        elif dx > 0.2 and velocity > 0.8:
                            gesture_recognized = "Machnięcie w prawo"
                            wrist_history = [] # Zresetuj historię by uniknąć zapętlania gestu
                            
                    # ================= LOGIKA STATYCZNA =================
                    if gesture_recognized == "":
                        if results.gestures and len(results.gestures) > idx:
                            top_gesture = results.gestures[idx][0].category_name
                            if top_gesture == "Thumb_Up":
                                gesture_recognized = "Kciuk w górę"
                            elif top_gesture == "Thumb_Down":
                                gesture_recognized = "Kciuk w dół"
                                
                        thumb_tip = hand_landmarks[4]
                        index_tip = hand_landmarks[8]
                        distance = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                        if distance < 0.05 and gesture_recognized == "":
                            gesture_recognized = "Złączenie palca wskazującego i kciuka"

                    if gesture_recognized and (current_time - last_gesture_time) > gesture_cooldown:
                        print(f"Rozpoznano gest: {gesture_recognized}")
                        last_gesture_time = current_time
            else:
                # Brak dłoni = czyszczenie historii, by nie porównywać np. wyjścia z kadru -> ponownego wejścia po 10 sek. a cooldown pozostał
                wrist_history = [] 

            cv2.putText(frame, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.imshow('RIPO Project - Sterowanie dlonmi (Tasks API)', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
