const mqtt = require('mqtt');

// 분리된 서비스 모듈 불러오기
const apiService = require('../services/ai_service');
const logService = require('../services/log_service');
const alertService = require('../services/alert_service');
const websocket = require('../websocket/websocket');
const { getRealtimeWeather } = require('../utils/weather'); // 모듈 부르기

// 차량별 대기열(Queue) 보관소
const vehicleQueues = {};

// 큐 처리 엔진 (한 차량의 데이터는 무조건 1개씩 순차 처리)
async function processQueue(vid, io, mqttClient) {              // 다중차량에서 데이터가 동시에 와도 큐에서 순차 처리
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
        realWeather = await getRealtimeWeather(lat, lon); // getRealtimeWeather => weather.js
    }
    // API호출에 실패하거나 값이 없으면 STM32 센서가 측정한 물리값(temp,humidity)을 백업데이터로 유지,강수형태는 0(맑음)을 기본값으로 지정
    const finalTemp = realWeather ? realWeather.temp : temp;
    const finalHumidity = realWeather ? realWeather.humidity : humidity;
    const finalRainType = realWeather ? realWeather.rainType : 0; 

    // AI 모델 예측
    // JSON으로 패킹하여 api_service.js를 통해  Flask AI 서버로 보냄.
    const aiData = await apiService.getAiPrediction({ 
        temp: finalTemp, 
        humidity: finalHumidity, 
        lux: lux, 
        speed: speed,
        rainType: finalRainType
    });
    
    // Flask 서버가 배열 문자열 형태로 반환하는 치명적인 포맷 오류 가능성을 차단하기 위해
    // 자바스크립트 단에서 replace(/['\[\]\s]+/g, '') 정규식 필터링을 걸어 대괄호, 따옴표, 공백을 완전히     
    // 깎아내고 완벽한 순수 알파벳 문자열(SAFE, WARNING, DANGER)만 추출해 냅니다.
    const mapped = aiData.mapped_features;
    const riskLevel = String(aiData.predicted_risk).replace(/['\[\]\s]+/g, '');

    // 하드웨어 개별 제어
    const controlTopic = `iot/${currentVehicle}/control`;
    
    if (riskLevel === 'DANGER' || riskLevel === 'WARNING') {
        mqttClient.publish(controlTopic, JSON.stringify({ command: riskLevel }));
        console.log(`[제어] ${currentVehicle} 차량으로 ${riskLevel} 제어 명령 역송신 완료`);
    } else {
        mqttClient.publish(controlTopic, JSON.stringify({ command: 'SAFE' }));
    }

    // DB 저장

    // log_service.js 를 통해 모든 차량의 센서 원본과 매핑특성,AI 예측 등급을 sensor_logs 테이블에 기록하고
    // 고유 키인 currentLogId를 반환 받는다
    const currentLogId = await logService.saveSensorLog(
        currentVehicle, finalTemp, finalHumidity, lux, speed, mapped, riskLevel
    );

    // 만약 등급이 WR or DN 이면 외래키를 물고 alert_service.js 를 실행후 위험발생 원인 문구,경고메시지 alert_events 테이블에 저장 
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