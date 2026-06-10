const mqtt = require('mqtt');

// 분리된 서비스 모듈 불러오기
const apiService = require('../services/ai_service');
const logService = require('../services/log_service');
const alertService = require('../services/alert_service');
const websocket = require('../websocket/websocket');
const { getRealtimeWeather } = require('../utils/weather'); 

// 차량별 대기열(Queue) 보관소
const vehicleQueues = {};

// 큐 처리 엔진 (한 차량의 데이터는 무조건 1개씩 순차 처리)
async function processQueue(vid, io, mqttClient) {
    if (vehicleQueues[vid].isProcessing) return; 
    
    vehicleQueues[vid].isProcessing = true; 

    while (vehicleQueues[vid].messages.length > 0) {
        const task = vehicleQueues[vid].messages.shift(); 
        
        try {
            await handleSensorData(task.topic, task.sensorData, vid, io, mqttClient);
        } catch (error) {
            console.error(`[Queue 에러] ${vid}번 차량 데이터 처리 중 오류:`, error.message);
        }
    }

    vehicleQueues[vid].isProcessing = false; 
}

module.exports = function(io) {
    const MQTT_BROKER = 'mqtt://127.0.0.1:1883';
    const mqttClient = mqtt.connect(MQTT_BROKER);

    mqttClient.on('connect', () => {
        console.log("MQTT 브로커 접속 성공 (Queue 시스템 가동)");
        mqttClient.subscribe('iot/+/json');            
    });

    mqttClient.on('message', (topic, message) => {    
        if (topic.endsWith('json')) {
            try {
                const rawData = message.toString().trim();
                const sensorData = JSON.parse(rawData);
                
                // 토픽 주소에서 차량 ID 추출
                const currentVehicle = topic.split('/')[1]; 

                // 객체 내부의 vid 덮어쓰기
                sensorData.vid = currentVehicle; 

                // 데이터가 들어오면 즉시 처리하지 않고 큐에 쌓기
                if (!vehicleQueues[currentVehicle]) {
                    vehicleQueues[currentVehicle] = { messages: [], isProcessing: false };
                }
                
                vehicleQueues[currentVehicle].messages.push({ topic, sensorData });
                
                // 큐 처리 시작
                processQueue(currentVehicle, io, mqttClient);

            } catch (error) {
                console.error("MQTT 메시지 파싱 오류:", error.message);
            }
        }
    });
};

// 실제 데이터 처리 로직 (분리됨)
async function handleSensorData(topic, sensorData, currentVehicle, io, mqttClient) {
    const { lat, lon, temp, humidity, lux, speed } = sensorData;
    
    console.log(`\n[Queue 처리 중] 차량ID: ${currentVehicle} | 대기열 남은 수: ${vehicleQueues[currentVehicle].messages.length}`);

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
        console.log(` 🚨 [제어] ${currentVehicle} 차량으로 ${riskLevel} 제어 명령 역송신 완료`);
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
}