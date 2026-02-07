#include <WiFi.h>

// ========= WIFI & SERVER SETTINGS =========
const char* ssid     = "Airtel_mihi_1556_EXT";
const char* password = "air67760";
const char* server_ip = "192.168.1.102"; // <-- Put the IP from Python here!
const uint16_t port  = 5000;

WiFiClient client;

// ========= PIN MAPPING (Same as before) =========
#define LEFT_FWD   18  
#define RIGHT_FWD  19  
#define RIGHT_REV  22  
#define LEFT_REV   21  
#define PUMP_PIN    2
#define BUZZ_PIN   23

int TURN_TIME = 2000;      // Default, will be updated from server
int FORWARD_TIME = 5000;   // Default, will be updated from server
int SPRAY_TIME = 2000;     // Default, will be updated from server
bool isRunning = false;
bool configReceived = false;

void setup() {
  Serial.begin(115200);
  pinMode(LEFT_FWD, OUTPUT); pinMode(RIGHT_FWD, OUTPUT);
  pinMode(RIGHT_REV, OUTPUT); pinMode(LEFT_REV, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT); pinMode(BUZZ_PIN, OUTPUT);
  Stop();

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  Serial.print("ESP32 IP: "); Serial.println(WiFi.localIP());
}

void loop() {
  // If not connected to server, try to connect
  if (!client.connected()) {
    Serial.println("Connecting to Python Server...");
    configReceived = false;
    if (client.connect(server_ip, port)) {
      Serial.println("Connected to Server!");
      receiveConfig(); // Wait for initial config
    } else {
      delay(2000); // Wait before retrying
      return;
    }
  }

  // 1. Check for commands from the Python Server
  if (client.available()) {
    char cmd = client.read();
    handleCommand(cmd);
  }

  // 2. Run Square Logic if active
  if (isRunning) {
    performSquareRoutine();
  }
}

void handleCommand(char cmd) {
    Serial.print("Remote Command: "); Serial.println(cmd);
    
    // Check for UPDATE command (multi-character)
    if (cmd == 'U') {
      String fullMsg = "U" + client.readStringUntil('\n');
      parseConfig(fullMsg);
      return;
    }
    
    // Single character commands
    if (cmd == 'S') isRunning = true;
    else if (cmd == 'X') { isRunning = false; Stop(); }
    else if (cmd == 'P') spray();
    else if (cmd == 'W') { moveForward(); delay(FORWARD_TIME); Stop(); }
    else if (cmd == 'D') { turnRight(); delay(TURN_TIME); Stop(); }
}

// ========= SPRAY QUERY FUNCTION =========
bool queryShouldSpray() {
  // Send spray query to server
  client.print("Q");  // Q for Query spray
  Serial.println("Querying server: should spray?");
  
  // Wait indefinitely for response (BLOCKING)
  // The robot stops here until server replies after image processing
  while (!client.available()) {
    // Optional: check for safety timeout or manual stop button here if needed
    // For now, we wait forever as requested
    delay(10);
  }
  
  if (client.available()) {
    char response = client.read();
    Serial.print("Server response: ");
    Serial.println(response);
    return (response == '1');
  }
  
  return false;
}

// ========= SMART DELAY WITH SPRAY QUERY =========
// Moves forward for half the time, queries server, stops and sprays if needed,
// then continues for the remaining half
// Returns false if STOP command received
bool smartDelayWithSpray(int ms) {
  int halfTime = ms / 2;
  
  // First half of movement
  unsigned long start = millis();
  while (millis() - start < halfTime) {
    if (client.available()) {
      char c = client.read();
      if (c == 'X') {
        isRunning = false;
        Stop();
        return false;
      }
    }
  }
  
  // Stop and query at halfway point
  Stop();
  Serial.println("Halfway point - querying spray...");
  
  if (queryShouldSpray()) {
    Serial.println("Spraying!");
    
    // Spray
    spray();
    
    Serial.println("Spray complete, continuing movement...");
  } else {
    Serial.println("Not spraying, continuing movement...");
  }
  
  // Resume movement for second half
  moveForward();
  start = millis();
  while (millis() - start < halfTime) {
    if (client.available()) {
      char c = client.read();
      if (c == 'X') {
        isRunning = false;
        Stop();
        return false;
      }
    }
  }
  
  return true;
}

// ========= MODIFIED SMART DELAY =========
// Now checks the WIFI CLIENT instead of Serial for 'X'
bool smartDelay(int ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    if (client.available()) {
      char c = client.read();
      if (c == 'X') {
        isRunning = false;
        Stop();
        return false;
      }
    }
  }
  return true;
}

// ========= CONFIG PARSING FUNCTIONS =========
void parseConfig(String msg) {
  // Parse "CONFIG:5000:2000:2000" or "UPDATE:5000:2000:2000"
  // Format: forward_time:turn_time:spray_time
  int firstColon = msg.indexOf(':');
  int secondColon = msg.indexOf(':', firstColon + 1);
  int thirdColon = msg.indexOf(':', secondColon + 1);
  
  if (firstColon > 0 && secondColon > firstColon) {
    String forwardStr = msg.substring(firstColon + 1, secondColon);
    String turnStr = msg.substring(secondColon + 1, thirdColon > 0 ? thirdColon : msg.length());
    
    FORWARD_TIME = forwardStr.toInt();
    TURN_TIME = turnStr.toInt();
    
    // Parse spray time if available (for backward compatibility)
    if (thirdColon > 0) {
      String sprayStr = msg.substring(thirdColon + 1);
      SPRAY_TIME = sprayStr.toInt();
    }
    
    Serial.print("Config Updated - Forward: ");
    Serial.print(FORWARD_TIME);
    Serial.print("ms, Turn: ");
    Serial.print(TURN_TIME);
    Serial.print("ms, Spray: ");
    Serial.print(SPRAY_TIME);
    Serial.println("ms");
  }
}

void receiveConfig() {
  // Wait for CONFIG message from server
  Serial.println("Waiting for CONFIG...");
  unsigned long startTime = millis();
  
  while (!client.available() && millis() - startTime < 5000) {
    delay(10); // Wait up to 5 seconds
  }
  
  if (client.available()) {
    String configMsg = client.readStringUntil('\n');
    Serial.print("Received: "); Serial.println(configMsg);
    parseConfig(configMsg);
    configReceived = true;
  } else {
    Serial.println("No CONFIG received, using defaults");
  }
}

// ========= MOVEMENT FUNCTIONS =========
void moveForward() { digitalWrite(LEFT_FWD, HIGH); digitalWrite(RIGHT_REV, HIGH); }
void turnRight() { digitalWrite(LEFT_FWD, HIGH); digitalWrite(RIGHT_FWD, HIGH); }
void turnLeft() { digitalWrite(RIGHT_REV, HIGH); }  // Only right wheel forward (left wheels can't reverse)
void Stop() { digitalWrite(LEFT_FWD, 0); digitalWrite(RIGHT_FWD, 0); digitalWrite(RIGHT_REV, 0); digitalWrite(LEFT_REV, 0); digitalWrite(PUMP_PIN, 0); }
void spray() { digitalWrite(PUMP_PIN, HIGH); delay(SPRAY_TIME); digitalWrite(PUMP_PIN, LOW); }

void performSquareRoutine() {
  // Continuous zigzag pattern: straight → right turn → straight → left turn → repeat
  // Runs until STOP button is pressed
  // Queries server at halfway through each forward movement to decide if spraying is needed
  
  while (isRunning) {
    // Move forward (with spray query at halfway point)
    moveForward();
    if (!smartDelayWithSpray(FORWARD_TIME)) return;
    Stop();
    if (!smartDelay(500)) return;  // Brief pause
    
    if (!isRunning) return;
    
    // Turn right
    turnRight();
    if (!smartDelay(TURN_TIME)) return;
    Stop();
    if (!smartDelay(500)) return;  // Brief pause
    
    if (!isRunning) return;
    
    // Move forward again (with spray query at halfway point)
    moveForward();
    if (!smartDelayWithSpray(FORWARD_TIME)) return;
    Stop();
    if (!smartDelay(500)) return;  // Brief pause
    
    if (!isRunning) return;
    
    // Turn left
    turnLeft();
    if (!smartDelay(TURN_TIME)) return;
    Stop();
    if (!smartDelay(500)) return;  // Brief pause
  }
}