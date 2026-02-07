import time
import os
import random

class CameraSystem:
    def __init__(self):
        pass

    def fetch_image(self):
        """Simulate fetching image from camera module"""
        print("[VISION] Fetching image (Simulated 4s delay)...")
        time.sleep(4)
        
        # Get directory of current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "data")
        
        if not os.path.exists(data_dir):
            print(f"[ERROR] Data directory not found: {data_dir}")
            return None
            
        images = [f for f in os.listdir(data_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if images:
            selected_image = random.choice(images)
            return os.path.join(data_dir, selected_image)
        else:
            print("[ERROR] No images found in data directory")
            return None

    def process_image(self):
        """Simulate processing image"""
        print("[VISION] Processing image (Simulated 5s delay)...")
        time.sleep(5)
        return random.choice(['0', '1'])
