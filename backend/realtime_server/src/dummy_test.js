const mqtt = require('mqtt');

// 관제 서버와 동일한 로컬 MQTT 브로커에 접속
const MQTT_BROKER = 'mqtt://127.0.0.1:1883';
const client = mqtt.connect(MQTT_BROKER);

client.on('connect', () => {
    console.log("테스트 데이터 생성기 가동! (MQTT 브로커 접속 성공)");
    console.log("==================================================");

    // 2초마다 무한 반복해서 데이터 쏘기
    setInterval(() => {
        // ----------------------------------------------------
        // 정상 차량 (9876번) - 맑고 밝은 낮, 안전 속도
        // ----------------------------------------------------
        const dummy9876 = {
            vid: "9876",
            temp: parseFloat((22 + Math.random() * 2).toFixed(1)),     // 22~24도
            humidity: parseFloat((40 + Math.random() * 5).toFixed(1)), // 40~45%
            lux: Math.floor(800 + Math.random() * 200),                // 800~1000 (밝음)
            speed: Math.floor(50 + Math.random() * 10)                 // 50~60km/h (정상)
        };
        client.publish('iot/9876/json', JSON.stringify(dummy9876));
        console.log(`[발송] 9876번 정상 데이터 ➔ 속도: ${dummy9876.speed}km/h | 조도: ${dummy9876.lux}`);

        // ----------------------------------------------------
        // 위험 차량 (6789번) - 터널 진입(어두움) + 과속
        // ----------------------------------------------------
        const dummy6789 = {
            vid: "6789",
            temp: parseFloat((-5 + Math.random() * 1).toFixed(1)),     
            humidity: parseFloat((90 + Math.random() * 5).toFixed(1)),
            lux: Math.floor(50 + Math.random() * 50),                
            speed: Math.floor(130 + Math.random() * 15)              
        };
        client.publish('iot/6789/json', JSON.stringify(dummy6789));
        console.log(`[발송] 6789번 위험 데이터 ➔ 속도: ${dummy6789.speed}km/h | 조도: ${dummy6789.lux}`);
        
    }, 2000); // 2000ms = 2초 간격
});

client.on('error', (err) => {
    console.error("MQTT 접속 에러:", err);
});