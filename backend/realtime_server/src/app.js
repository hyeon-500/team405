const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const app = express();
const server = http.createServer(app);    // app.js 가 돌아가기 위한 최소한의 모듈들
const io = new Server(server, {
    cors: {
        origin: '*'
    }
});

app.use(express.json());
app.use(cors());

app.get('/', (req, res) => {                             // restapi 중의 get으로 자기가 실행되면 다른 파일들을 열어줌
    res.sendFile(__dirname + '/../../../frontend/dashboard/index.html');  // index.html 연결
});

// sensor API 및 socket 로직 연결
require('./axios')(app, io, server);    // axios(axios.js)연결

// 역할 STM32/ESP32 센서데이터 수신,웹에 실시간 전송,DB저장,ML서버 호출,경고처리