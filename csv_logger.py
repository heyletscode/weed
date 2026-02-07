import csv
import os
from datetime import datetime

class CsvLogger:
    def __init__(self, filename="detection_logs.csv"):
        self.filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        self.headers = ["Timestamp", "Weed", "Healthy Tomato", "Diseased Tomato"]
        self._initialize_file()

    def _initialize_file(self):
        """Check if file exists, if not create with headers"""
        if not os.path.exists(self.filename):
            try:
                with open(self.filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.headers)
                print(f"[LOGGER] Created log file: {self.filename}")
            except Exception as e:
                print(f"[LOGGER] Error creating file: {e}")

    def log(self, detections):
        """
        Log detection data to CSV.
        detections: list of strings (e.g. ['weed', 'healthy_tomato'])
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Initialize row with 0s
            row_data = {
                "Timestamp": timestamp,
                "Weed": 0,
                "Healthy Tomato": 0,
                "Diseased Tomato": 0
            }
            
            # Update counts/flags based on detections
            # Assuming we just want 1 if present, 0 if not (binary flag)
            # If you want counts, we can do row_data[...] += 1
            for det in detections:
                if det == "weed":
                    row_data["Weed"] = 1
                elif det == "healthy_tomato":
                    row_data["Healthy Tomato"] = 1
                elif det == "diseased_tomato":
                    row_data["Diseased Tomato"] = 1
            
            # Write row
            with open(self.filename, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    row_data["Timestamp"],
                    row_data["Weed"],
                    row_data["Healthy Tomato"],
                    row_data["Diseased Tomato"]
                ])
                
            print(f"[LOGGER] Logged to CSV: {detections}")
            
        except Exception as e:
            print(f"[LOGGER] Error logging data: {e}")
