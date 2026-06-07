const mqtt = require('mqtt');
// const db = require('../../../database/sqlite/sqlite');
const apiService = require('../services/ai_service');
const logService = require('../services/log_service');
const alertService = require('../services/alert_service');
const websocket = require('../websocket/websocket');

module.exports = function(io) {
    const MQTT_BROKER = 'mqtt://127.0.0.1:1883';
    const mqttClient = mqtt.connect(MQTT_BROKER);

    mqttClient.on('connect', () => {
        console.log("MQTT 브로커 접속 성공");
        mqttClient.subscribe('iot/nucleo/json');            //   MQTT 수신 -> ESP32가 보내는 토픽 구독
    });

    mqttClient.on('message', async (topic, message) => {    //  데이터 받음 (시작)
        if (topic === 'iot/nucleo/json') {
            try {
                // 디버깅
                const rawData = message.toString();
                console.log(`\n[수신한 원본 데이터] : ${rawData}`);

                // MQTT 수신 데이터 파싱
                const sensorData = JSON.parse(message.toString());
                const { temp, humidity, lux, speed } = sensorData;

                // AI 서버를 통한 위험도 예측                       -> AI 서버(app.py) 호출
                const aiData = await apiService.getAiPrediction({ temp, humidity, lux, speed });  // 여기서 다음으로 봐야할 파일은 services/api_service.js
                const mapped = aiData.mapped_features;                                       // app.py에서 반환한 값 여기 저장
                const riskLevel = aiData.predicted_risk;                                     // app.py에서 반환한 값 여기 저장

                // 위험도에 따른 하드웨어 제어 명령 역송신 (Downstream)
                if (riskLevel === 'DANGER' || riskLevel === 'WARNING') {
                    mqttClient.publish('iot/nucleo/control', JSON.stringify({ command: riskLevel }));       // 여기 되게 중요 
                                                                                                            // esp32 -> 서버  | 서버 -> esp32  양방향 통신
                    console.log(`[제어 명령] 차량으로 ${riskLevel} 상태 전송 완료`);
                } else {
                    mqttClient.publish('iot/nucleo/control', JSON.stringify({ command: 'SAFE' }));
                }

                // 전체 센서 로그 DB 저장                                (함수 log_service.js로 옮김)
                const currentLogId = 
                    await logService.saveSensorLog(
                        temp,humidity,lux,speed,mapped,riskLevel
                    );

                // 위험 상태일 경우 이벤트 알림 테이블에 분리 저장       (함수 alert_service.js로 옮김)
                await alertService.saveAlert(
                    currentLogId,riskLevel,mapped,speed
                );
        
                // 프론트엔드 실시간 렌더링을 위한 데이터 브로드캐스팅   (함수 websocket.js로 옮김)

                websocket.broadcastSensorData(
                    io,
                    {
                        log_id: currentLogId,
                        raw: sensorData,
                        mapped,
                        risk_level: riskLevel,
                        timestamp: new Date().toLocaleString()
                    }
                )

            } catch (error) {
                console.error("🚨 데이터 처리 중 오류 발생:\n", error);
            }
        }
    });
};