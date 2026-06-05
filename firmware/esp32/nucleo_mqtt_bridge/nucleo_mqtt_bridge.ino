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
const char* TOPIC_JSON   = "iot/nucleo/json";        // 전체 데이터 전송용
const char* TOPIC_TEMP   = "iot/nucleo/temperature"; // 온도값 개별 전송용
const char* TOPIC_HUMI   = "iot/nucleo/humidity";    // 습도값 개별 전송용
const char* TOPIC_LUX    = "iot/nucleo/lux";         // 조도값 개별 전송용
const char* TOPIC_STATUS = "iot/nucleo/status";      // 장치 연결 상태 전송용

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
// [함수] MQTT 브로커 연결 처리
// -------------------------------------------------------
void connectMQTT()
{
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT); // 서버 정보 설정
    mqttClient.setKeepAlive(60);
    mqttClient.setSocketTimeout(5);

    // MAC 주소 기반 Client ID 생성
    String clientId = "ESP32_NUCLEO_" + WiFi.macAddress();
    clientId.replace(":", "");

    while (!mqttClient.connected()) // 연결될 때까지 재시도
    {
        Serial.print("MQTT 연결 중...");
        
        /* 
         * connect(ID, User, Pass, WillTopic, WillQoS, WillRetain, WillMessage)
         * LWT(Last Will): 장치가 비정상 종료 시 서버가 대신 "offline" 메시지를 발행함
         */
        // if (mqttClient.connect(MQTT_CLIENT,
        //                        nullptr, nullptr,        // 인증 없음
        //                        TOPIC_STATUS, 1,         // LWT Topic, QoS
        //                        true, "offline"))        // Retain, LWT Payload
        if (mqttClient.connect(clientId.c_str()))
        {
            Serial.println("MQTT 연결 완료");
            // 온라인 상태임을 서버에 알림 (Retain 설정으로 나중에 접속한 사람도 확인 가능)
            mqttClient.publish(TOPIC_STATUS, "online", true);
        }
        else
        {
            Serial.print("실패, rc="); // 에러 코드 출력
            Serial.print(mqttClient.state());
            Serial.println(" 5초 후 재시도");
            delay(5000); // 5초 대기 후 재시도
        }
    }
}

// -------------------------------------------------------
// [함수] 데이터 파싱 및 MQTT 전송 (STM32 규격 맞춤 적용)
// 입력: {"temp":24.0,"humidity":41.0,"lux":1.0,"speed":14}
// -------------------------------------------------------
void parseAndPublish(String json)
{
    // 1. 수신한 JSON 원본 데이터를 전체 토픽으로 발행
    mqttClient.publish(TOPIC_JSON, json.c_str());

    // 2. 온도(temp) 값 추출 및 발행
    int tempIdx = json.indexOf("\"temp\":"); 
    if (tempIdx != -1) 
    {
        int start = tempIdx + 7; // "\"temp\":" 의 문자 길이는 7
        int end   = json.indexOf(',', start); 
        if (end == -1) end = json.indexOf('}', start); 
        String tempVal = json.substring(start, end); 
        tempVal.trim(); 
        mqttClient.publish(TOPIC_TEMP, tempVal.c_str()); 
    }

    // 3. 습도(humidity) 값 추출 및 발행 
    int humiIdx = json.indexOf("\"humidity\":");
    if (humiIdx != -1)
    {
        int start = humiIdx + 11; // "\"humidity\":" 의 문자 길이는 11
        int end   = json.indexOf(',', start);
        if (end == -1) end = json.indexOf('}', start);
        String humiVal = json.substring(start, end);
        humiVal.trim();
        mqttClient.publish(TOPIC_HUMI, humiVal.c_str());
    }

    // 4. 조도(lux) 값 추출 및 발행 
    int luxIdx = json.indexOf("\"lux\":");
    if (luxIdx != -1)
    {
        int start = luxIdx + 6; // "\"lux\":" 의 문자 길이는 6
        int end   = json.indexOf(',', start);
        if (end == -1) end = json.indexOf('}', start);
        String luxVal = json.substring(start, end);
        luxVal.trim();
        mqttClient.publish(TOPIC_LUX, luxVal.c_str());
    }

    // 5. 가상 속도(speed) 값 추출 및 발행 (추가됨)
    int speedIdx = json.indexOf("\"speed\":");
    if (speedIdx != -1)
    {
        int start = speedIdx + 8; // "\"speed\":" 의 문자 길이는 8
        int end   = json.indexOf(',', start);
        if (end == -1) end = json.indexOf('}', start);
        String speedVal = json.substring(start, end);
        speedVal.trim();
        // speed 전용 토픽으로 발행 (상단 변수 선언부에 추가하셔도 좋습니다)
        mqttClient.publish("iot/nucleo/speed", speedVal.c_str());
    }

    Serial.println("MQTT 파싱 및 발행 성공: " + json);
}
// -------------------------------------------------------
// [설정] 초기 시스템 초기화
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
void loop()
{
    // 1. MQTT 연결 상태 상시 체크 및 유지
    if (!mqttClient.connected())
    {
        Serial.print("MQTT 끊김, state=");
        Serial.println(mqttClient.state());
        connectMQTT();
    }
    mqttClient.loop(); // MQTT 내부 데이터 처리를 위해 주기적 호출 필요


    //lastTime = millis();

    // 2. NUCLEO로부터 데이터 수신 여부 확인
    if (Serial2.available())
    {
        // 줄바꿈('\n') 문자가 올 때까지 버퍼의 모든 데이터를 읽어옴
        String line = Serial2.readStringUntil('\n');

        // [핵심 1단계] 널 바이트(0x00)와 깨진 특수문자 완벽 제거
        String cleanLine = "";
        for (int i = 0; i < line.length(); i++) {
            char c = line[i];
            // 키보드로 칠 수 있는 정상적인 글자(ASCII 32 ~ 126)만 통과시킴
            if (c >= 32 && c <= 126) {
                cleanLine += c;
            }
        }

        // [핵심 2단계] 깨끗해진 문자열에서 위치 찾기
        int tempIdx = cleanLine.indexOf("temp");
        int endIdx = cleanLine.lastIndexOf('}');

        // temp와 } 가 모두 무사히 살아있다면?
        if (tempIdx != -1 && endIdx != -1)
        {
            // 노이즈 찌꺼기를 버리고 완벽한 JSON {" ... } 형태로 강제 조립
            String finalJson = "{\"" + cleanLine.substring(tempIdx, endIdx + 1);

            Serial.print("✅ 데이터 복원 성공: ");
            Serial.println(finalJson);

            // 복원된 데이터를 서버로 전송
            parseAndPublish(finalJson); 
            mqttClient.loop();
        }
        else
        {
            // temp 글자조차 완전히 박살난 순수 노이즈는 무시
            // (시리얼 모니터가 너무 지저분해지면 아래 두 줄은 주석 처리하셔도 됩니다)
            Serial.print("⚠️ 순수 노이즈 버림: ");
            Serial.println(cleanLine);
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