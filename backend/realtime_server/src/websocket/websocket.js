// websocket.js 


// websocket 서버 코드 작성하는곳

// Socket.io 클라이언트 연결 관리
function initWebsocket(io) {
    io.on('connection', (socket) => {
        console.log(`[Socket] 대시보드 클라이언트 접속됨 (ID: ${socket.id})`);
        
        // 초기 접속 시 기본적으로 '전체 차량(all_vehicles)' 관제 방에 입장시킴
        socket.join('all_vehicles');

        // 프론트엔드 대시보드에서 특정 차량을 검색(필터링)했을 때 실행되는 이벤트
        socket.on('subscribe_vehicle', (vehicle_id) => {
            // 접속 중인 기존 방에서 모두 퇴장 (본인 고유 ID 방은 제외)
            socket.rooms.forEach(room => {
                if (room !== socket.id) socket.leave(room);
            });

            // 프론트엔드에서 넘어온 검색어가 빈 문자열("")이면 전체 보기, 값이 있으면 해당 차량 방에 입장
            const targetRoom = vehicle_id ? vehicle_id : 'all_vehicles';
            socket.join(targetRoom);
            
            console.log(`[Socket] 클라이언트(ID: ${socket.id})가 관제 모드를 변경함 ➔ [${targetRoom}] 모니터링 중`);
        });

        socket.on('disconnect', () => {
            console.log(`[Socket] 클라이언트 접속 해제됨 (ID: ${socket.id})`);
        });
    });
}

// 브로드캐스팅 (mqtt_client.js에서 호출됨)
function broadcastSensorData(io, vehicle_id, payload) {
    // 특정 차량 번호 방에 접속한 관리자에게만 개별 전송
    io.to(vehicle_id).emit('sensor_update', payload);

    // '전체 차량'을 모니터링 중인 방('all_vehicles')의 관리자에게도 전송
    io.to('all_vehicles').emit('sensor_update', payload);
}

module.exports = {
    initWebsocket,
    broadcastSensorData
};