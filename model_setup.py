import mediapipe as mp
import urllib.request
import os

def initialize_recognizer():
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
    return GestureRecognizer, options