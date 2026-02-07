import socket
import threading
import tkinter as tk
from tkinter import ttk
import time
from PIL import Image, ImageTk
from camera_module import CameraSystem

# --- SETTINGS ---
PORT = 5000
DEFAULT_FORWARD_TIME = 5000
DEFAULT_TURN_TIME = 2000
DEFAULT_SPRAY_TIME = 2000

class RobotControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Control Panel")
        self.root.geometry("1000x850")
        self.root.resizable(False, False)
        
        # Network variables
        self.client_conn = None
        self.server_socket = None
        self.local_ip = socket.gethostbyname(socket.gethostname())
        
        # Timing parameters
        self.forward_time = DEFAULT_FORWARD_TIME
        self.turn_time = DEFAULT_TURN_TIME
        self.spray_time = DEFAULT_SPRAY_TIME
        
        # Initialize Camera System
        self.camera = CameraSystem()
        
        self.setup_gui()
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
    
    def setup_gui(self):
        # Title
        title_label = tk.Label(self.root, text="🤖 Robot Control Panel", 
                               font=("Arial", 18, "bold"), fg="#2c3e50")
        title_label.pack(pady=15)
        
        # Camera/Processing Status Frame
        vision_frame = tk.LabelFrame(self.root, text="📷 Vision System", 
                                   font=("Arial", 12, "bold"), padx=15, pady=10)
        vision_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Image Display Area
        self.image_label = tk.Label(vision_frame, text="No Image", bg="#bdc3c7", width=40, height=10)
        self.image_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Processing Status Label
        self.vision_status_label = tk.Label(vision_frame, text="Status: Idle", 
                                          font=("Arial", 14, "bold"), bg=vision_frame.cget('bg'), fg="#7f8c8d")
        self.vision_status_label.pack(side=tk.LEFT, padx=10)

        # Connection Status Frame
        status_frame = tk.Frame(self.root, bg="#ecf0f1", relief=tk.RIDGE, borderwidth=2)
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(status_frame, text="📡 PC IP Address:", font=("Arial", 10, "bold"), 
                bg="#ecf0f1").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.ip_label = tk.Label(status_frame, text=self.local_ip, 
                                 font=("Arial", 10), fg="#16a085", bg="#ecf0f1")
        self.ip_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        tk.Label(status_frame, text="🔌 Port:", font=("Arial", 10, "bold"), 
                bg="#ecf0f1").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.port_label = tk.Label(status_frame, text=str(PORT), 
                                   font=("Arial", 10), fg="#16a085", bg="#ecf0f1")
        self.port_label.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        tk.Label(status_frame, text="📶 Status:", font=("Arial", 10, "bold"), 
                bg="#ecf0f1").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.status_label = tk.Label(status_frame, text="Waiting for ESP32...", 
                                     font=("Arial", 10), fg="#e67e22", bg="#ecf0f1")
        self.status_label.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Settings Frame
        settings_frame = tk.LabelFrame(self.root, text="⚙️ Movement Settings", 
                                       font=("Arial", 12, "bold"), padx=15, pady=10)
        settings_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(settings_frame, text="Forward Time (ms):", 
                font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.forward_entry = tk.Entry(settings_frame, width=10, font=("Arial", 10))
        self.forward_entry.insert(0, str(DEFAULT_FORWARD_TIME))
        self.forward_entry.grid(row=0, column=1, padx=10, pady=5)
        
        tk.Label(settings_frame, text="Turn Time (ms):", 
                font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.turn_entry = tk.Entry(settings_frame, width=10, font=("Arial", 10))
        self.turn_entry.insert(0, str(DEFAULT_TURN_TIME))
        self.turn_entry.grid(row=1, column=1, padx=10, pady=5)
        
        tk.Label(settings_frame, text="Spray Time (ms):", 
                font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.spray_entry = tk.Entry(settings_frame, width=10, font=("Arial", 10))
        self.spray_entry.insert(0, str(DEFAULT_SPRAY_TIME))
        self.spray_entry.grid(row=2, column=1, padx=10, pady=5)
        
        self.update_btn = tk.Button(settings_frame, text="📤 Update Settings", 
                                    command=self.on_update_settings, 
                                    bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                                    state=tk.DISABLED, cursor="hand2")
        self.update_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Control Buttons Frame
        control_frame = tk.LabelFrame(self.root, text="🎮 Robot Controls", 
                                      font=("Arial", 12, "bold"), padx=15, pady=10)
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.start_btn = tk.Button(control_frame, text="▶️ START", 
                                   command=self.on_start_click, 
                                   bg="#27ae60", fg="white", font=("Arial", 12, "bold"),
                                   width=12, height=1, state=tk.DISABLED, cursor="hand2")
        self.start_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.stop_btn = tk.Button(control_frame, text="⏹️ STOP", 
                                  command=self.on_stop_click, 
                                  bg="#e74c3c", fg="white", font=("Arial", 12, "bold"),
                                  width=12, height=1, state=tk.DISABLED, cursor="hand2")
        self.stop_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.spray_btn = tk.Button(control_frame, text="💧 SPRAY", 
                                   command=self.on_spray_click, 
                                   bg="#3498db", fg="white", font=("Arial", 12, "bold"),
                                   width=12, height=1, state=tk.DISABLED, cursor="hand2")
        self.spray_btn.grid(row=0, column=2, padx=5, pady=5)
    
    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(("0.0.0.0", PORT))
            self.server_socket.listen(1)
            
            print(f"[SERVER] Started on {self.local_ip}:{PORT}")
            print(f"[SERVER] Waiting for ESP32 connection...")
            
            conn, addr = self.server_socket.accept()
            self.client_conn = conn
            
            print(f"[CONNECTED] Robot connected from {addr}")
            
            # Send initial config
            self.send_config()
            
            # Update GUI
            self.root.after(0, self.update_connection_status, True)
            
            # Start listener thread for spray queries
            listener_thread = threading.Thread(target=self.listen_for_queries, daemon=True)
            listener_thread.start()
            
        except Exception as e:
            print(f"[ERROR] Server error: {e}")
            self.root.after(0, self.update_connection_status, False)
    
    def listen_for_queries(self):
        """Background thread to listen for spray queries from ESP32"""
        print("[LISTENER] Started listening for spray queries")
        while self.client_conn:
            try:
                if self.client_conn:
                    data = self.client_conn.recv(1)
                    if data:
                        cmd = data.decode()
                        if cmd == 'Q':
                            # Spray query received - Start Vision Pipeline
                            print(f"[QUERY] Spray query received. Starting vision pipeline...")
                            self.run_vision_pipeline()
            except Exception as e:
                print(f"[LISTENER] Error: {e}")
                break
    
    def run_vision_pipeline(self):
        """Executes the simulated vision pipeline: Fetch -> Process -> Respond"""
        # Step 1: Countdown and Fetch Image
        for i in range(4, 0, -1):
            self.update_vision_status(f"Capturing in {i}...", "#e67e22") # Orange
            time.sleep(1)
            
        self.update_vision_status("Capturing Image...", "#e67e22") # Orange
        
        # Use camera module to fetch image
        image_path = self.camera.fetch_image()
        
        # Update GUI with fetched image
        if image_path:
             self.root.after(0, lambda: self.display_image(image_path))
        
        # Step 2: Process Image
        self.update_vision_status("Processing Image...", "#3498db") # Blue
        
        # Use camera module to process image (pass the fetched image path)
        decision, detections = self.camera.process_image(image_path)
        
        # Step 3: Send Response
        if self.client_conn:
            self.client_conn.sendall(decision.encode())
            print(f"[decision] Sent to robot: {decision}")
        
        # Update Status with Result
        result_text = "Result: SPRAY (WEED)" if decision == '1' else "Result: NO SPRAY"
        result_color = "#c0392b" if decision == '1' else "#27ae60" # Red for spray, Green for clear
        
        # Show detections in status
        det_str = ", ".join(detections) if detections else "None"
        full_status = f"{result_text}\nDetected: {det_str}"
        
        self.update_vision_status(full_status, result_color)
        
        # Reset status after a delay
        self.root.after(5000, lambda: self.update_vision_status("Status: Idle", "#7f8c8d"))

    def update_vision_status(self, text, color):
        """Update the vision status label safely from background thread"""
        self.root.after(0, lambda: self.vision_status_label.config(text=text, fg=color))

    def display_image(self, image_path):
        """Display the fetched image on the GUI"""
        try:
            img = Image.open(image_path)
            # Resize to fit the label (keep aspect ratio)
            img.thumbnail((300, 200)) 
            photo = ImageTk.PhotoImage(img)
            
            self.image_label.config(image=photo, text="", width=300, height=200)
            self.image_label.image = photo # Keep reference!
        except Exception as e:
            print(f"[ERROR] Failed to display image: {e}")
    
    def send_config(self):
        """Send current configuration to ESP32"""
        if self.client_conn:
            try:
                config_msg = f"CONFIG:{self.forward_time}:{self.turn_time}:{self.spray_time}\n"
                self.client_conn.sendall(config_msg.encode())
                print(f"[SENT] {config_msg.strip()}")
            except Exception as e:
                print(f"[ERROR] Failed to send config: {e}")
    
    def send_command(self, cmd):
        """Send single character command to ESP32"""
        if self.client_conn:
            try:
                self.client_conn.sendall(cmd.encode())
                print(f"[SENT] Command: {cmd}")
            except Exception as e:
                print(f"[ERROR] Failed to send command: {e}")
    
    def update_connection_status(self, connected):
        """Update GUI based on connection status"""
        if connected:
            self.status_label.config(text="Connected ✓", fg="#27ae60")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.spray_btn.config(state=tk.NORMAL)
            self.update_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Disconnected ✗", fg="#e74c3c")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.spray_btn.config(state=tk.DISABLED)
            self.update_btn.config(state=tk.DISABLED)
    
    def on_start_click(self):
        """Handle START button click"""
        self.send_command('S')
    
    def on_stop_click(self):
        """Handle STOP button click"""
        self.send_command('X')
    
    def on_spray_click(self):
        """Handle SPRAY button click"""
        self.send_command('P')
    
    def on_update_settings(self):
        """Handle Update Settings button click"""
        try:
            forward = int(self.forward_entry.get())
            turn = int(self.turn_entry.get())
            spray = int(self.spray_entry.get())
            
            if forward <= 0 or turn <= 0 or spray <= 0:
                self.status_label.config(text="Invalid values! Must be > 0", fg="#e74c3c")
                return
            
            self.forward_time = forward
            self.turn_time = turn
            self.spray_time = spray
            
            # Send UPDATE command to ESP32
            if self.client_conn:
                update_msg = f"UPDATE:{self.forward_time}:{self.turn_time}:{self.spray_time}\n"
                self.client_conn.sendall(update_msg.encode())
                print(f"[SENT] {update_msg.strip()}")
                self.status_label.config(text="Settings Updated ✓", fg="#27ae60")
        except ValueError:
            self.status_label.config(text="Invalid input! Enter numbers only", fg="#e74c3c")
        except Exception as e:
            print(f"[ERROR] Update failed: {e}")
            self.status_label.config(text="Update failed!", fg="#e74c3c")

if __name__ == "__main__":
    root = tk.Tk()
    app = RobotControlGUI(root)
    root.mainloop()