// -------------------------------------------------------
// [파일 정보] nucleo_mqtt_bridge.ino
// [역할] NUCLEO(UART) 데이터를 수신하여 MQTT(Wi-Fi)로 중계
// -------------------------------------------------------

#include <WiFi.h>          // ESP32의 Wi-Fi 기능을 제어하는 라이브러리
#include <PubSubClient.h>  // MQTT 통신(발행/구독)을 위한 라이브러리


// 네트워크 및 서버 설정 (사용 환경에 맞게 수정 필요)

const char* WIFI_SSID    = "404호";      // 접속할 와이파이 이름
const char* WIFI_PASS    = "kgitbank@1004";  // 와이파이 비밀번호
const char* MQTT_SERVER  = "192.168.0.193";   // MQTT 브로커(PC)의 IP 주소
const int   MQTT_PORT    = 1883;              // MQTT 기본 포트 번호

const String VEHICLE_ID    = "1234";

const String TOPIC_JSON    = "iot/" + VEHICLE_ID + "/json";        // 서버로 보낼때                        (publish)
const String TOPIC_CONTROL = "iot/" + VEHICLE_ID + "/control";     // 서버로부터 위험 판단 명령을 수신     (Subscribe)
const String TOPIC_STATUS  = "iot/" + VEHICLE_ID + "/status";      // 접속 상태 알릴 때


// 하드웨어 핀 설정 (NUCLEO 보드와 연결)

#define NUCLEO_RX  16       // ESP32의 16번 핀 (NUCLEO의 TX와 연결됨)
#define NUCLEO_TX  17       // ESP32의 17번 핀 (NUCLEO의 RX와 연결됨)
#define NUCLEO_BAUD 9600  // NUCLEO와 맞춘 통신 속도


// 통신 객체 생성

WiFiClient    wifiClient;            
PubSubClient mqttClient(wifiClient); 


// Wi-Fi 연결 처리

void connectWiFi()
{
    WiFi.begin(WIFI_SSID, WIFI_PASS); 
    Serial.print("Wi-Fi 연결 중");
    while (WiFi.status() != WL_CONNECTED) 
    {
        delay(500);
        Serial.print("."); 
    }
    Serial.println("\nWi-Fi 연결 완료: " + WiFi.localIP().toString());
}


// 서버로부터 역송신(Downstream) 제어 명령 수신
void callback(char* topic, byte* payload, unsigned int length) {
    String message = "";
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    Serial.println("[서버 명령 수신] 토픽: " + String(topic) + " / 내용: " + message);
    
    // 수신받은 JSON 명령을 STM32로 그대로 전달
    Serial2.println(message); 
}


// MQTT 브로커 연결 처리
void connectMQTT() {
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT); 
    mqttClient.setCallback(callback);  

    String clientId = "ESP32_Vehicle_" + VEHICLE_ID;

    while (!mqttClient.connected()) {
        Serial.print("MQTT 연결 중...");
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("MQTT 연결 완료 (ID: " + clientId + ")");
            mqttClient.publish(TOPIC_STATUS.c_str(), "online", true);
            mqttClient.subscribe(TOPIC_CONTROL.c_str());
        } else {
            Serial.print("실패, rc="); 
            Serial.print(mqttClient.state());
            Serial.println(" 5초 후 재시도");
            delay(5000); 
        }
    }
}


// 초기 시스템 초기화

void setup()
{
    Serial.begin(115200); 
    
    Serial2.begin(NUCLEO_BAUD, SERIAL_8N1, NUCLEO_RX, NUCLEO_TX); 
    Serial2.setTimeout(100);

    connectWiFi(); 
    connectMQTT(); 

    Serial.println("시스템 준비 완료. NUCLEO 데이터 수신 대기 중...");
}


void loop() {
    // Wi-Fi가 끊기면 스스로 재연결 (먹통 방지)
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Wi-Fi 연결 끊어짐! 재연결 시도 중...");
        WiFi.disconnect();
        WiFi.reconnect();
        delay(2000);
        return; 
    }

    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop(); 

    if (Serial2.available()) {
        String line = Serial2.readStringUntil('\n');

        // 노이즈 필터링
        String cleanLine = "";
        for (int i = 0; i < line.length(); i++) {
            char c = line[i];
            if (c >= 32 && c <= 126) {
                cleanLine += c;
            }
        }

        // 괄호 { } 기준으로 완전한 JSON 찾기
        int startIdx = cleanLine.indexOf('{');
        int endIdx = cleanLine.lastIndexOf('}');

        if (startIdx != -1 && endIdx != -1 && startIdx < endIdx) {
            String finalJson = cleanLine.substring(startIdx, endIdx + 1);
            
            // 1초 속도 제한기(Throttle)
            static unsigned long lastPublishTime = 0;
            
            if (millis() - lastPublishTime >= 1000) {
                lastPublishTime = millis();
                Serial.println("데이터 복원 완료 및 서버로 전송: " + finalJson);
                mqttClient.publish(TOPIC_JSON.c_str(), finalJson.c_str());
            } 
            // 1초가 안 지났을 때 들어오는 초과 데이터는 서버 보호를 위해 무시됨
        } else {
            Serial.println("불안전한 노이즈 데이터 버림: " + cleanLine);
        }
    }
}