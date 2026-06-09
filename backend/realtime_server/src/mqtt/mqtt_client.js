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
        
        // 다중 차량 통신 지원: 특정 토픽이 아닌 와일드카드(+) 사용
        mqttClient.subscribe('iot/+/json');            
        //mqttClient.subscribe('iot/nucleo/json'); // 기존 단일 토픽도 하위 호환성 
    });

    mqttClient.on('message', async (topic, message) => {    
        // 수신 토픽이 json으로 끝나는 데이터만 처리
        if (topic.endsWith('json')) {
            try {
                const rawData = message.toString().trim();
                
                // 센서 데이터 파싱 및 STM32의 차량 고유번호(vid) 추출
                const sensorData = JSON.parse(rawData);
                const { vid, temp, humidity, lux, speed, lat, lon } = sensorData;
                
                const currentVehicle = vid || 'UNKNOWN_CAR';
                console.log(`\n[수신] 차량ID: ${currentVehicle} | 토픽: ${topic}`);

                // 기상청 API 연동
                let realWeather = null;
                if (lat && lon) {
                    realWeather = await getRealtimeWeather(lat, lon);
                }
                const finalTemp = realWeather ? realWeather.temp : temp;
                const finalHumidity = realWeather ? realWeather.humidity : humidity;

                // AI 모델 예측 (차량 환경 데이터 분석)
                const aiData = await apiService.getAiPrediction({ 
                    temp: finalTemp, 
                    humidity: finalHumidity, 
                    lux: lux, 
                    speed: speed 
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

                // DB 저장
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