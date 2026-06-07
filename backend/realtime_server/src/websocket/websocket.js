
// websocket 서버 코드 작성하는곳


// Socket.io 클라이언트 연결 관리

function initWebsocket(io){
      
      io.on('connection', (socket) => {
            console.log(`[Socket] 대시보드 클라이언트 접속됨 (ID: ${socket.id})`);
            
            socket.on('disconnect', () => {
                  console.log(`[Socket] 클라이언트 접속 해제됨 (ID: ${socket.id})`);
            });
      });
}


// 브로드캐스팅

function broadcastSensorData(io, data) {
      io.emit('sensor_update',data);
}

module.exports = {
      initWebsocket,
      broadcastSensorData
}