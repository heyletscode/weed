import time
import os
import random
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from csv_logger import CsvLogger

PROJECT_ID = "gen-lang-client-0410905787" 
LOCATION = "us-central1"

class CameraSystem:
    def __init__(self):
        self.classes = ["weed", "healthy_tomato", "diseased_tomato"]
        self.logger = CsvLogger()
        
        # Initialize Vertex AI
        try:
            # Set credentials explicitly
            current_dir = os.path.dirname(os.path.abspath(__file__))
            credentials_path = os.path.join(current_dir, "credentials.json")
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            
            vertexai.init(project=PROJECT_ID, location=LOCATION)
            self.model = GenerativeModel("gemini-2.5-flash")
            self.use_vertex = True
            print(f"[VISION] Vertex AI initialized with project {PROJECT_ID}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Vertex AI: {e}")
            print("[VISION] Falling back to simulation mode")
            self.use_vertex = False

    def convert_to_linux_path(self, path):
        """Convert Windows path to Linux-style path (forward slashes)"""
        if path:
            return path.replace('\\', '/')
        return path
    
    def _convert_rgb565_to_jpeg(self, rgb565_path, output_path, width, height):
        """Convert RGB565 raw data to JPEG image"""
        try:
            import numpy as np
            from PIL import Image
            
            # Read raw RGB565 data
            with open(rgb565_path, 'rb') as f:
                raw_data = f.read()
            
            expected_size = width * height * 2  # 2 bytes per pixel
            if len(raw_data) != expected_size:
                print(f"[WARNING] RGB565 size mismatch: expected {expected_size}, got {len(raw_data)}")
                return False
            
            # Convert bytes to numpy array as little-endian uint16
            rgb565_array = np.frombuffer(raw_data, dtype='<u2').reshape((height, width))
            
            # Extract RGB channels from RGB565
            # RGB565 format (little-endian): GGGBBBBB RRRRRGGG
            # After reading as little-endian uint16: RRRRRGGGGGGBBBBB
            r = ((rgb565_array & 0xF800) >> 11)  # 5 bits red
            g = ((rgb565_array & 0x07E0) >> 5)   # 6 bits green
            b = (rgb565_array & 0x001F)          # 5 bits blue
            
            # Scale to 8-bit properly
            r = (r * 255 // 31).astype(np.uint8)  # 5-bit to 8-bit
            g = (g * 255 // 63).astype(np.uint8)  # 6-bit to 8-bit
            b = (b * 255 // 31).astype(np.uint8)  # 5-bit to 8-bit
            
            # Stack into RGB image
            rgb_image = np.stack([r, g, b], axis=-1)
            
            # Convert to PIL Image and save as JPEG
            img = Image.fromarray(rgb_image, mode='RGB')
            img.save(output_path, 'JPEG', quality=85)
            
            return True
        except Exception as e:
            print(f"[ERROR] RGB565 conversion failed: {e}")
            return False

    def fetch_image(self, source="dataset", camera_ip=None):
        """
        Fetch image based on source.
        source: "dataset" or "camera"
        camera_ip: IP address of the ESP32-CAM (required for "camera" source)
        """
        print(f"[VISION] Fetching image from {source}...")
        
        if source == "camera":
            if camera_ip:
                try:
                    import requests
                    url = f"http://{camera_ip}/capture"
                    print(f"[VISION] Requesting from {url}...")
                    
                    # Retry logic with exponential backoff
                    for attempt in range(5):
                        try:
                            # Use streaming to handle large responses better
                            # Add keep-alive and disable compression
                            headers = {
                                'Connection': 'keep-alive',
                                'Accept-Encoding': 'identity'
                            }
                            response = requests.get(url, timeout=30, stream=True, headers=headers)
                            
                            if response.status_code == 200:
                                # Read in chunks to handle incomplete reads better
                                current_dir = os.path.dirname(os.path.abspath(__file__))
                                raw_path = os.path.join(current_dir, "data", "capture_raw.rgb565")
                                
                                # Stream raw data to file in chunks
                                with open(raw_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=4096):
                                        if chunk:
                                            f.write(chunk)
                                
                                print(f"[VISION] Raw RGB565 data received ({os.path.getsize(raw_path)} bytes)")
                                
                                # Convert RGB565 to JPEG (QVGA: 320x240)
                                save_path = os.path.join(current_dir, "data", "capture_latest.jpg")
                                if self._convert_rgb565_to_jpeg(raw_path, save_path, 320, 240):
                                    print(f"[VISION] Image converted and saved to {save_path}")
                                    return save_path
                                else:
                                    print(f"[ERROR] Failed to convert RGB565 to JPEG")
                                    return None
                            else:
                                print(f"[WARNING] Attempt {attempt+1}: Status {response.status_code}")
                        except requests.exceptions.RequestException as e:
                            print(f"[WARNING] Attempt {attempt+1}: {e}")
                            if attempt == 4:
                                raise
                            # Exponential backoff: 1s, 2s, 4s, 8s
                            wait_time = 2 ** attempt
                            print(f"[VISION] Waiting {wait_time}s before retry...")
                            time.sleep(wait_time)
                    
                    print(f"[ERROR] Camera returned status {response.status_code}")
                except Exception as e:
                    print(f"[ERROR] Camera fetch failed after retries: {e}")
            else:
                print("[ERROR] Camera IP not known yet! (Wait for camera to connect)")
            
            print("[VISION] Falling back to dataset...")
        
        # Get directory of current file
        
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

    def predict_objects(self, image_path):
        """
        Analyze image using Vertex AI (Gemini) or fallback to simulation.
        """
        if not image_path:
            return []

        if self.use_vertex:
            try:
                print(f"[VISION] Analyzing {os.path.basename(image_path)} with Gemini...")
                
                # Load image data
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                image_part = Part.from_data(data=image_data, mime_type="image/jpeg")
                
                # Prompt optimized for strict classification
                prompt = """
                Analyze this image. Identify if any of the following are present:
                1. "weed"
                2. "healthy_tomato"
                3. "diseased_tomato"
                
                STEPS:
                1. Count the number of distinct plants in the image.
                2. IF there are multiple distinct plants, return a list of all their types: e.g. ['weed', 'healthy_tomato']
                3. IF there is only one plant, return ONLY the single most confident classification: e.g. ['weed']
                4. IF NO plant is clearly visible in the image, or you are unsure, return []. Do not guess.
                
                Return ONLY a python list of strings containing exactly the detected classes.
                If nothing is detected, return [].
                Do not include markdown formatting or explanations.
                """
                
                response = self.model.generate_content([image_part, prompt])
                response_text = response.text.strip()
                
                # Clean up response to get a list
                # This is a basic parser, assuming the model obeys instructions well
                detected_objects = []
                for cls in self.classes:
                    if cls in response_text:
                        detected_objects.append(cls)
                
                print(f"[VERTEX] Raw response: {response_text}")
                print(f"[VERTEX] parsed: {detected_objects}")
                return detected_objects

            except Exception as e:
                print(f"[ERROR] Vertex AI prediction failed: {e}")
                print("[VISION] Falling back to simulation for this request")
        
        # Fallback Simulation
        num_objects = random.randint(1, 3) 
        detected_objects = random.sample(self.classes, num_objects)
        print(f"[VISION] (Simulated) Predictor output: {detected_objects}")
        return detected_objects

    def process_image(self, image_path):
        """
        Simulate processing image pipeline.
        1. Predict objects in the image
        2. Decide spray logic based on prediction
        """
        # Get predictions
        detections = self.predict_objects(image_path)
        
        # Log to CSV
        self.logger.log(detections)
        
        # Spray Logic: Spray if "weed" is detected
        if "weed" in detections:
            print("[LOGIC] Weed detected -> SPRAY")
            return '1', detections
        else:
            print("[LOGIC] No weed detected -> NO SPRAY")
            return '0', detections
