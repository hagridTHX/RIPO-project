import cv2
import mediapipe as mp
import time
import argparse
import keyboard
import os
import ctypes
from model_setup import initialize_recognizer
from actions import GestureController

def main():
    # 1. Obsługa argumentów
    parser = argparse.ArgumentParser(description="Sterowanie gestami RIPO")
    parser.add_argument('--debug', action='store_true', help='Uruchamia aplikację z widocznym oknem kamery')
    args = parser.parse_args()

    # 2. Ukrywanie konsoli, jeśli nie jesteśmy w trybie debug (Tylko dla Windows)
    if not args.debug:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0 = SW_HIDE

    # 3. Globalny skrót klawiszowy (Ctrl + Shift + Q), aby "zabić" proces
    keyboard.add_hotkey('ctrl+shift+q', lambda: os._exit(0))

    if args.debug:
        print("Uruchomiono w trybie DEBUG (z oknem).")
    print("Aplikacja działa. Naciśnij 'Ctrl+Shift+Q' w dowolnym momencie, aby ją zamknąć.")

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

    with GestureRecognizer.create_from_options(options) as recognizer:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Nie można odebrać klatki z kamery.")
                break
            
            frame = cv2.flip(frame, 1)  
            current_time = time.time()
            fps = 1 / (current_time - prev_time) if prev_time > 0 else 0
            prev_time = current_time

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            results = recognizer.recognize_for_video(mp_image, int(current_time * 1000))

            h, w, _ = frame.shape

            if results.hand_landmarks:
                for idx, hand_landmarks in enumerate(results.hand_landmarks):
                    
                    # Rysowanie na klatce TYLKO w trybie debug
                    if args.debug:
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
                            
                    # Główna logika jest wykonywana niezależnie od trybu
                    controller.process_landmarks(hand_landmarks, results.gestures, idx, current_time, frame_height=h, frame_width=w)
            else:
                controller.last_gesture = "No gesture"
                controller.last_gesture_confidence = 0.0

            # Wyświetlanie okna TYLKO w trybie debug
            if args.debug:
                cv2.putText(frame, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                gesture_text = f'{controller.last_gesture} ({controller.last_gesture_confidence:.1%})'
                cv2.putText(frame, gesture_text, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                cv2.imshow('Gesture Controller', frame)
                
                if cv2.waitKey(1) & 0xFF == 27:  # ESC zamyka podgląd
                    break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()