const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: '*'
    }
});

app.use(express.json());
app.use(cors());

app.get('/', (req, res) => {
    res.sendFile(__dirname + '/public/index.html');
});

// sensor API 및 socket 로직 연결
require('./axios')(app, io, server);

// 역할 STM32/ESP32 센서데이터 수신,웹에 실시간 전송,DB저장,ML서버 호출,경고처리