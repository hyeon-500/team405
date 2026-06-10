// -------------------------------------------------------
// [파일 정보] nucleo_mqtt_bridge.ino
// [역할] NUCLEO(UART) 데이터를 수신하여 MQTT(Wi-Fi)로 중계
// -------------------------------------------------------

#include <WiFi.h>          // ESP32의 Wi-Fi 기능을 제어하는 라이브러리
#include <PubSubClient.h>  // MQTT 통신(발행/구독)을 위한 라이브러리

// -------------------------------------------------------
// 1. 네트워크 및 서버 설정 (사용 환경에 맞게 수정 필요)
// -------------------------------------------------------
const char* WIFI_SSID    = "404호";      // 접속할 와이파이 이름
const char* WIFI_PASS    = "kgitbank@1004";  // 와이파이 비밀번호
const char* MQTT_SERVER  = "192.168.0.193";   // MQTT 브로커(PC)의 IP 주소
const int   MQTT_PORT    = 1883;              // MQTT 기본 포트 번호
//const char* MQTT_CLIENT  = "ESP32_NUCLEO_1"; // 서버가 이 장치를 식별할 이름


// MQTT 주제(Topic) 정의: 데이터의 "주소"와 같은 역할
const String VEHICLE_ID    = "5632";
const String TOPIC_JSON    = "iot/" + VEHICLE_ID + "/json";        // 서버로 보낼 때
const String TOPIC_CONTROL = "iot/" + VEHICLE_ID + "/control";     // 서버에서 제어 명령 받을 때
const String TOPIC_STATUS  = "iot/" + VEHICLE_ID + "/status";      // 접속 상태 알릴 때 (String으로 통일)

// -------------------------------------------------------
// 2. 하드웨어 핀 설정 (NUCLEO 보드와 연결)
// -------------------------------------------------------
#define NUCLEO_RX  16       // ESP32의 16번 핀 (NUCLEO의 TX와 연결됨)
#define NUCLEO_TX  17       // ESP32의 17번 핀 (NUCLEO의 RX와 연결됨)
#define NUCLEO_BAUD 9600  // NUCLEO와 맞춘 통신 속도

// -------------------------------------------------------
// 3. 통신 객체 생성
// -------------------------------------------------------
WiFiClient    wifiClient;            // Wi-Fi 연결을 관리하는 클라이언트
PubSubClient mqttClient(wifiClient); // Wi-Fi를 기반으로 MQTT 동작을 수행하는 클라이언트

// -------------------------------------------------------
// [함수] Wi-Fi 연결 처리
// -------------------------------------------------------
void connectWiFi()
{
    WiFi.begin(WIFI_SSID, WIFI_PASS); // 와이파이 연결 시도
    Serial.print("Wi-Fi 연결 중");
    while (WiFi.status() != WL_CONNECTED) // 연결될 때까지 무한 반복
    {
        delay(500);
        Serial.print("."); // 연결 대기 중임을 표시
    }
    // 연결 성공 시 ESP32가 할당받은 IP를 시리얼 모니터에 출력
    Serial.println("\nWi-Fi 연결 완료: " + WiFi.localIP().toString());
}

// -------------------------------------------------------
// 서버로부터 역송신(Downstream) 제어 명령 수신
// -------------------------------------------------------
void callback(char* topic, byte* payload, unsigned int length) {
    String message = "";
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    Serial.println("[서버 명령 수신] 토픽: " + String(topic) + " / 내용: " + message);
    
    // 수신받은 JSON 명령을 STM32로 그대로 전달
    Serial2.println(message); 
}
// -------------------------------------------------------
// [함수] MQTT 브로커 연결 처리
// -------------------------------------------------------
void connectMQTT() {
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT); 
    mqttClient.setCallback(callback);  // 콜백 함수 등록

    // 서버에서 알아보기 쉽게 차량 번호를 포함한 Client ID 생성
    String clientId = "ESP32_Vehicle_" + VEHICLE_ID;

    while (!mqttClient.connected()) {
        Serial.print("MQTT 연결 중...");
        // 생성한 고유 ID로 접속 시도
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("MQTT 연결 완료 (ID: " + clientId + ")");
            
            // 접속 완료 상태를 각 차량의 전용 토픽으로 발행 (.c_str() 추가)
            mqttClient.publish(TOPIC_STATUS.c_str(), "online", true);
            
            // 내 차량 번호에 맞는 제어 명령만 골라서 구독
            mqttClient.subscribe(TOPIC_CONTROL.c_str());
        } else {
            Serial.print("실패, rc="); 
            Serial.print(mqttClient.state());
            Serial.println(" 5초 후 재시도");
            delay(5000); 
        }
    }
}

// -------------------------------------------------------
// 초기 시스템 초기화
// -------------------------------------------------------
void setup()
{
    Serial.begin(115200); // PC 디버깅용 시리얼 시작
    
    // NUCLEO와 통신할 UART2 채널 설정 (RX=16, TX=17)
    Serial2.begin(NUCLEO_BAUD, SERIAL_8N1, NUCLEO_RX, NUCLEO_TX); 
    Serial2.setTimeout(100);

    connectWiFi(); // 와이파이 연결
    connectMQTT(); // MQTT 연결

    Serial.println("시스템 준비 완료. NUCLEO 데이터 수신 대기 중...");
}

// -------------------------------------------------------
// [루프] 반복 실행 로직 
// -------------------------------------------------------
void loop() {
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop(); 

    if (Serial2.available()) {
        String line = Serial2.readStringUntil('\n');

        // 사용자님이 작성하신 노이즈 필터링 완벽 유지
        String cleanLine = "";
        for (int i = 0; i < line.length(); i++) {
            char c = line[i];
            if (c >= 32 && c <= 126) {
                cleanLine += c;
            }
        }

        // 괄호 { } 기준으로 완전한 JSON만 찾기
        int startIdx = cleanLine.indexOf('{');
        int endIdx = cleanLine.lastIndexOf('}');

        if (startIdx != -1 && endIdx != -1 && startIdx < endIdx) {
            String finalJson = cleanLine.substring(startIdx, endIdx + 1);
            Serial.println("데이터 복원 완료 및 서버로 전송: " + finalJson);

            // 통짜 데이터 바로 전송!
            mqttClient.publish(TOPIC_JSON.c_str(), finalJson.c_str());
        } else {
            Serial.println("불안전한 노이즈 데이터 버림: " + cleanLine);
        }
    }

    

    //---------------------------------------

    // // 데이터 전송만 1초 간격
    // static unsigned long lastTime = 0;
    // if (millis() - lastTime >= 1000)
    // {
    //     lastTime = millis();

    //     // 2. NUCLEO로부터 데이터 수신 여부 확인
    //     if (Serial2.available())
    //     {
    //         // 줄바꿈('\n') 문자가 올 때까지 한 줄을 읽어들임
    //         String line = Serial2.readStringUntil('\n');
    //         line.trim();

    //         // 수신된 문자열이 비어있지 않고, JSON 시작 기호 '{'를 포함하는지 검사
    //         if (line.length() > 0 && line.startsWith("{"))
    //         {
    //             parseAndPublish(line); // 파싱 및 전송 함수 실행
    //         }
    //     }                   
    // }

}