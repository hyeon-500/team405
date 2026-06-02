const mqtt = require('mqtt');
const db = require('../db/db');
const aiApi = require('../utils/axios');

module.exports = function(io) {
    const MQTT_BROKER = 'mqtt://127.0.0.1:1883';
    const mqttClient = mqtt.connect(MQTT_BROKER);

    mqttClient.on('connect', () => {
        console.log("MQTT 브로커 접속 성공");
        mqttClient.subscribe('iot/nucleo/json');
    });

    mqttClient.on('message', async (topic, message) => {
        if (topic === 'iot/nucleo/json') {
            try {
                // 1. MQTT 수신 데이터 파싱
                const sensorData = JSON.parse(message.toString());
                const { temp, humidity, lux, speed } = sensorData;

                // 2. AI 서버를 통한 위험도 예측
                const aiData = await aiApi.getAiPrediction({ temp, humidity, lux, speed });
                const mapped = aiData.mapped_features;
                const riskLevel = aiData.predicted_risk;

                // 3. 위험도에 따른 하드웨어 제어 명령 역송신 (Downstream)
                if (riskLevel === 'DANGER' || riskLevel === 'WARNING') {
                    mqttClient.publish('iot/nucleo/control', JSON.stringify({ command: riskLevel }));
                    console.log(`[제어 명령] 차량으로 ${riskLevel} 상태 전송 완료`);
                } else {
                    mqttClient.publish('iot/nucleo/control', JSON.stringify({ command: 'SAFE' }));
                }

                // 4. 전체 센서 로그 DB 저장
                const insertLogSql = `INSERT INTO sensor_logs 
                    (raw_temp, raw_humidity, raw_lux, current_speed, mapped_weather, mapped_surface, mapped_time, predicted_risk) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
                
                const result = await db.run(insertLogSql, [
                    temp, humidity, lux, speed, mapped.mapped_weather, mapped.mapped_surface, mapped.mapped_time, riskLevel
                ]);
                const currentLogId = result.lastID;

                // 5. 위험 상태일 경우 이벤트 알림 테이블에 분리 저장
                if (riskLevel === 'WARNING' || riskLevel === 'DANGER') {
                    const cause = `${mapped.mapped_time}시간대 ${mapped.mapped_weather}/${mapped.mapped_surface} 상태에서 ${speed}km/h 주행`;
                    const alertMessage = riskLevel === 'DANGER'
                        ? "치명적 위험! 즉시 50km/h 이하로 크게 감속하세요!"
                        : "주의 구간! 서행하세요.";
                    
                    await db.run(
                        `INSERT INTO alert_events (log_id, risk_level, event_cause, alert_message) VALUES (?, ?, ?, ?)`,
                        [currentLogId, riskLevel, cause, alertMessage]
                    );
                }

                // 6. 프론트엔드 실시간 렌더링을 위한 데이터 브로드캐스팅
                io.emit('sensor_update', {
                    log_id: currentLogId,
                    raw: sensorData,
                    mapped: mapped,
                    risk_level: riskLevel,
                    timestamp: new Date().toLocaleString()
                });

            } catch (error) {
                console.error("데이터 처리 중 오류 발생:", error.message);
            }
        }
    });
};