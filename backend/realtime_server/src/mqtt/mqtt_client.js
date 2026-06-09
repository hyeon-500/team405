const mqtt = require('mqtt');
// 분리된 서비스 모듈 불러오기
const apiService = require('../services/ai_service');
const logService = require('../services/log_service');
const alertService = require('../services/alert_service');
const websocket = require('../websocket/websocket');
const { getRealtimeWeather } = require('../utils/weather'); 

module.exports = function(io) {
    const MQTT_BROKER = 'mqtt://127.0.0.1:1883';
    const mqttClient = mqtt.connect(MQTT_BROKER);

    mqttClient.on('connect', () => {
        console.log("MQTT 브로커 접속 성공");
        mqttClient.subscribe('iot/+/json');            
    });

    mqttClient.on('message', async (topic, message) => {    
        if (topic.endsWith('json')) {
            try {
                const rawData = message.toString().trim();
                const sensorData = JSON.parse(rawData);
                
                // 1. 🚀 거짓말을 하지 않는 토픽 주소에서 진짜 차량 ID를 가장 먼저 추출합니다.
                // (예: "iot/4321/json" ➔ "4321")
                const currentVehicle = topic.split('/')[1]; 

                // 2. 💡 [핵심] 기존 구조를 깨지 않기 위해, 추출한 진짜 ID로 객체 내부의 vid를 덮어씌웁니다!
                // 이렇게 하면 STM32가 내부 데이터에 "1234"라고 잘못 보냈어도 "4321"로 정정됩니다.
                sensorData.vid = currentVehicle; 

                // 3. 기존 구조 그대로 데이터를 안전하게 구조 분해 할당합니다.
                const { vid, lat, lon, temp, humidity, lux, speed } = sensorData;
                
                console.log(`\n[수신] 차량ID: ${currentVehicle} | 토픽: ${topic}`);

                // 기상청 API 연동
                let realWeather = null;
                if (lat && lon) {
                    realWeather = await getRealtimeWeather(lat, lon);
                }
                const finalTemp = realWeather ? realWeather.temp : temp;
                const finalHumidity = realWeather ? realWeather.humidity : humidity;
                const finalRainType = realWeather ? realWeather.rainType : 0; 

                // AI 모델 예측
                const aiData = await apiService.getAiPrediction({ 
                    temp: finalTemp, 
                    humidity: finalHumidity, 
                    lux: lux, 
                    speed: speed,
                    rainType: finalRainType
                });
                
                const mapped = aiData.mapped_features;
                const riskLevel = String(aiData.predicted_risk).replace(/['\[\]\s]+/g, '');

                // 하드웨어 개별 제어
                const controlTopic = `iot/${currentVehicle}/control`;
                
                if (riskLevel === 'DANGER' || riskLevel === 'WARNING') {
                    mqttClient.publish(controlTopic, JSON.stringify({ command: riskLevel }));
                    console.log(` [제어] ${currentVehicle} 차량으로 ${riskLevel} 제어 명령 역송신 완료`);
                } else {
                    mqttClient.publish(controlTopic, JSON.stringify({ command: 'SAFE' }));
                }

                // 4. 수정된 올바른 vid(또는 currentVehicle)가 포함된 상태로 DB에 정상 저장됩니다!
                const currentLogId = await logService.saveSensorLog(
                    currentVehicle, finalTemp, finalHumidity, lux, speed, mapped, riskLevel
                );

                if (riskLevel === 'WARNING' || riskLevel === 'DANGER') {
                    await alertService.saveAlert(
                        currentLogId, currentVehicle, riskLevel, mapped, speed
                    );
                }
        
                // 프론트엔드 개별 관제 브로드캐스팅
                const payload = {
                    log_id: currentLogId,
                    vehicle_id: currentVehicle,
                    raw_sensor_data: aiData.raw_sensor_data, 
                    mapped_features: aiData.mapped_features,
                    predicted_risk: aiData.predicted_risk,
                    timestamp: new Date().toLocaleString()
                };
                
                websocket.broadcastSensorData(io, currentVehicle, payload);

            } catch (error) {
                console.error("데이터 처리 중 오류 발생:", error.message);
            }
        }
    });
};