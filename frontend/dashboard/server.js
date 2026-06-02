const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

// 모듈 분리된 라우터 및 서비스 불러오기
const apiRoutes = require('./routes/api');
const mqttService = require('./mqtt/mqttService');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

// 미들웨어 설정
app.use(express.json());
app.use(cors());

// 대시보드 화면(index.html) 제공
app.get('/', (req, res) => {
    res.sendFile(__dirname + '/index.html');
});

// REST API 라우터 등록
app.use('/api', apiRoutes);

// Socket.io 클라이언트 연결 관리
io.on('connection', (socket) => {
    console.log(`[Socket] 대시보드 클라이언트 접속됨 (ID: ${socket.id})`);
    
    socket.on('disconnect', () => {
        console.log(`[Socket] 클라이언트 접속 해제됨 (ID: ${socket.id})`);
    });
});

// MQTT 서비스 및 백엔드 핵심 로직 실행
mqttService(io);

// 서버 실행
const PORT = 3000;
server.listen(PORT, () => {
    console.log(`=========================================`);
    console.log(` 관제 서버가 성공적으로 실행되었습니다. (포트: ${PORT}) `);
    console.log(`=========================================`);
});