#include "esp_camera.h"
#include <WiFi.h>

// ==========================================
// CAMERA MODEL: AI THINKER
// ==========================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ==========================================
// WIFI & SERVER SETTINGS
// ==========================================
const char* ssid = "admin";
const char* password = "1234567890";
const char* server_ip = "10.16.152.30";
const uint16_t server_port = 5000;

WiFiServer webServer(80);
unsigned long lastAnnounceTime = 0;
const unsigned long announceInterval = 15000;

void startCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_RGB565;
  
  // Frame parameters - Reduced resolution for RGB565
  config.frame_size = FRAMESIZE_QVGA; // 320x240 = ~150KB (vs 640x480 = ~600KB)
  config.fb_count = 2; // Double buffering for better reliability

  if(psramFound()){
    config.grab_mode = CAMERA_GRAB_LATEST;
  }
  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    return;
  }
}

void connectWiFi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void announcePresence() {
  WiFiClient client;
  if (client.connect(server_ip, server_port)) {
    client.print("CAM_IP:" + WiFi.localIP().toString() + "\n");
    delay(100);
    client.stop();
  }
}

void serveImage(WiFiClient& client) {
  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get();
  if(!fb) {
    client.println("HTTP/1.1 500 Internal Server Error");
    client.println();
    return;
  }

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: application/octet-stream");
  client.println("Content-Disposition: inline; filename=capture.rgb565");
  client.print("Content-Length: ");
  client.println(fb->len);
  client.println();
  
  // Send in chunks for large RGB565 data
  size_t remaining = fb->len;
  size_t sent = 0;
  const size_t chunk_size = 4096;
  
  while(remaining > 0) {
    size_t to_send = (remaining > chunk_size) ? chunk_size : remaining;
    client.write(fb->buf + sent, to_send);
    sent += to_send;
    remaining -= to_send;
    delay(1); // Small delay to prevent buffer overflow
  }
  
  esp_camera_fb_return(fb);
}

void setup() {
  Serial.begin(115200);
  startCamera();
  connectWiFi();
  webServer.begin();
  
  // Announce IP to server
  announcePresence();
}

void loop() {
  // Periodic presence announcement
  unsigned long currentTime = millis();
  if (currentTime - lastAnnounceTime >= announceInterval) {
    announcePresence();
    lastAnnounceTime = currentTime;
  }
  
  // Check for HTTP requests
  WiFiClient client = webServer.available();
  if (client) {
    String req = client.readStringUntil('\r');
    if (req.indexOf("GET /capture") != -1) {
      serveImage(client);
    }
    client.stop();
  }
}