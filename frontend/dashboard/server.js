const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const sqlite3 = require('sqlite3').verbose();
const axios = require('axios');
const cors = require('cors');
const mqtt = require('mqtt'); // MQTT 패키지 추가

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

app.use(express.json());
app.use(cors());
app.get('/', (req, res) => {
    res.sendFile(__dirname + '/index.html');
});

// =================================================================
// 1. SQLite 데이터베이스 초기화 및 테이블 생성
// =================================================================
const db = new sqlite3.Database('./log/sensor_monitoring.db', (err) => {
    if (err) console.error("DB 연결 실패:", err.message);
    else console.log("✓ SQLite 데이터베이스(sensor_monitoring.db) 연결 완료");
});

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS sensor_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
        raw_temp REAL NOT NULL,
        raw_humidity REAL NOT NULL,
        raw_lux REAL NOT NULL,
        current_speed INTEGER NOT NULL,
        mapped_weather TEXT,
        mapped_surface TEXT,
        mapped_time TEXT,
        predicted_risk TEXT
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS alert_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
        log_id INTEGER,
        risk_level TEXT NOT NULL,
        event_cause TEXT NOT NULL,
        alert_message TEXT NOT NULL,
        FOREIGN KEY(log_id) REFERENCES sensor_logs(log_id)
    )`);
});

// =================================================================
// 2. MQTT 브로커 연결 및 센서 데이터 수신 (HTTP API를 완벽히 대체)
// =================================================================
// (로컬 PC에 설치된 Mosquitto 브로커를 가리킵니다)
const MQTT_BROKER = 'mqtt://127.0.0.1:1883'; 
const mqttClient = mqtt.connect(MQTT_BROKER);

mqttClient.on('connect', () => {
    console.log("✓ MQTT 브로커 연결 완료");
    // ESP32에서 JSON 전체 데이터를 쏘는 핵심 토픽만 구독합니다.
    mqttClient.subscribe('iot/nucleo/json', (err) => {
        if (!err) console.log("📡 [iot/nucleo/json] 토픽 구독 완료. 실시간 수신 대기 중...");
        else console.error("❌ MQTT 구독 에러:", err);
    });
});

// MQTT 토픽으로 데이터가 들어올 때마다 실행되는 이벤트
mqttClient.on('message', async (topic, message) => {
    if (topic === 'iot/nucleo/json') {
        try {
            // 0) 들어온 MQTT 메시지(문자열)를 JSON 객체로 파싱
            const sensorData = JSON.parse(message.toString());
            const { temp, humidity, lux, speed } = sensorData;

            // 1) Flask AI API 서버로 데이터 전송 및 위험도 예측 요청
            const flaskResponse = await axios.post('http://127.0.0.1:5000/predict_risk', {
                temp, humidity, lux, speed
            });
            
            const aiData = flaskResponse.data;
            const mapped = aiData.mapped_features;
            const riskLevel = aiData.predicted_risk; 

            // 2) SQLite 'sensor_logs' 테이블에 저장
            const insertLogSql = `INSERT INTO sensor_logs 
                (raw_temp, raw_humidity, raw_lux, current_speed, mapped_weather, mapped_surface, mapped_time, predicted_risk) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
            
            db.run(insertLogSql, [temp, humidity, lux, speed, mapped.mapped_weather, mapped.mapped_surface, mapped.mapped_time, riskLevel], function(err) {
                if (err) return console.error("DB 저장 에러:", err.message);
                
                const currentLogId = this.lastID;

                // 3) WARNING 또는 DANGER일 경우 'alert_events' 테이블에 추가 저장
                if (riskLevel === 'WARNING' || riskLevel === 'DANGER') {
                    let cause = `${mapped.mapped_time}시간대 ${mapped.mapped_weather}/${mapped.mapped_surface} 상태에서 ${speed}km/h 주행`;
                    let alertMessage = riskLevel === 'DANGER' 
                        ? "치명적 위험! 결빙/가시거리 불량 구간입니다. 즉시 50km/h 이하로 크게 감속하세요!" 
                        : "주의 구간! 수막현상 위험이 있습니다. 서행하세요.";

                    db.run(`INSERT INTO alert_events (log_id, risk_level, event_cause, alert_message) VALUES (?, ?, ?, ?)`,
                        [currentLogId, riskLevel, cause, alertMessage]);
                }

                // 4) Socket.io를 통해 프론트엔드 대시보드로 실시간 데이터 방송
                const broadcastData = {
                    log_id: currentLogId,
                    raw: sensorData,
                    mapped: mapped,
                    risk_level: riskLevel,
                    timestamp: new Date().toLocaleString()
                };
                io.emit('sensor_update', broadcastData); // 1초 주기로 연결된 모든 웹에 쏨
            });

        } catch (error) {
            console.error("❌ 데이터 처리/Flask 연동 에러:", error.message);
        }
    }
});

// =================================================================
// 3. Socket.io 실시간 연결 관리
// =================================================================
io.on('connection', (socket) => {
    console.log(`[Socket.io] 새로운 대시보드 클라이언트 접속: ${socket.id}`);
    socket.on('disconnect', () => {
        console.log(`[Socket.io] 클라이언트 접속 해제: ${socket.id}`);
    });
});

// 서버 포트 설정 및 구동
const PORT = 3000;
server.listen(PORT, () => {
    console.log(`=========================================`);
    console.log(`🚀 Node.js 관제 서버가 포트 ${PORT}에서 실행 중입니다.`);
    console.log(`=========================================`);
});