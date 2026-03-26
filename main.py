import cv2
import mediapipe as mp
import time
from model_setup import initialize_recognizer
from actions import GestureController

def main():
    GestureRecognizer, options = initialize_recognizer()
    controller = GestureController()

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
    # ZWIĘKSZONO DO 60 FPS
    target_fps = 60 
    
    print("Uruchamianie sterowania systemem z 60 FPS... Program może teraz działać w tle. Wciśnij 'q' z aktywnym oknem podglądu, aby wyjść.")

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
                    
                    # Rysowanie nakładki na kamerze
                    for connection in HAND_CONNECTIONS:
                        start_idx, end_idx = connection
                        start_point = hand_landmarks[start_idx]
                        end_point = hand_landmarks[end_idx]
                        
                        cx_start, cy_start = int(start_point.x * w), int(start_point.y * h)
                        cx_end, cy_end = int(end_point.x * w), int(end_point.y * h)
                        cv2.line(frame, (cx_start, cy_start), (cx_end, cy_end), (0, 0, 255), 1)
                        
                    for landmark in hand_landmarks:
                        cx, cy = int(landmark.x * w), int(landmark.y * h)
                        cv2.circle(frame, (cx, cy), 3, (0, 255, 0), cv2.FILLED)
                        
                    # Wywołanie dedykowanej analizy i wciskania przycisków odzewu
                    controller.process_landmarks(hand_landmarks, results.gestures, idx, current_time)
            else:
                controller.clear_history()

            cv2.putText(frame, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            cv2.imshow('RIPO Project - Sterowanie dlonmi', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
