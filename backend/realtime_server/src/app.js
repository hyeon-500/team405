
// 역할 STM32/ESP32 센서데이터 수신,웹에 실시간 전송,DB저장,ML서버 호출,경고처리

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');
const {initWebsocket} = require('./websocket/websocket'); 

// 모듈 분리된 라우터 및 서비스 불러오기
const apiRoutes = require('./routes/api');
const mqttService = require('./mqtt/mqtt_client');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

// 미들웨어 설정
app.use(express.json());
app.use(cors());

// =================================================================
// [경로 수정 및 추가] 프론트엔드 자바스크립트/CSS 파일을 찾을 수 있도록 정적 경로 개통
// =================================================================
// __dirname(src) 기준 3칸 위(../../..)로 올라가서 frontend/dashboard 폴더를 통째로 서빙합니다.
app.use(express.static(path.join(__dirname, '../../../frontend/dashboard')));

// 대시보드 화면(index.html) 제공
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../../../frontend/dashboard/index.html'));
});


// REST API 라우터 등록
app.use('/api', apiRoutes);

// Socket.io 클라이언트 연결 관리  
initWebsocket(io);                                                     
// io.on('connection', (socket) => {                                                    websocket.js 로 옮김
//     console.log(`[Socket] 대시보드 클라이언트 접속됨 (ID: ${socket.id})`);
    
//     socket.on('disconnect', () => {
//         console.log(`[Socket] 클라이언트 접속 해제됨 (ID: ${socket.id})`);
//     });
// });

// MQTT 서비스 및 백엔드 핵심 로직 실행
mqttService(io);

// 서버 실행
const PORT = 3000;
server.listen(PORT, () => {
    console.log(`=========================================`);
    console.log(` 관제 서버가 성공적으로 실행되었습니다. (포트: ${PORT}) `);
    console.log(`=========================================`);
});