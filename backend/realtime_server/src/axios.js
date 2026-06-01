// RestAPI 중의 POST, 비동기 통신 방식 중 하나인 axios.
const axios = require('axios');
const db = require('./db/db');

module.exports = (app, io, server) => {

    // ================================================================
    // 2. 센서 데이터 수신 API (ESP32/STM32 -> Node.js)
    // ================================================================
    app.post('/api/sensor', async (req, res) => {

        const { temp, humidity, lux, speed } = req.body;

        try {

            // 1) Flask AI API 서버로 데이터 전송 및 위험도 예측 요청
            const flaskResponse = await axios.post(
                'http://127.0.0.1:5000/predict_risk',   // ML 서버(5000) 연결
                {
                    temp,
                    humidity,
                    lux,
                    speed
                }
            );

            const aiData = flaskResponse.data;   
            const mapped = aiData.mapped_features;

            const riskLevel = aiData.predicted_risk.replace(/[\\[\]']/g, "");

            // 2) SQLite sensor_logs 테이블 저장
            const insertLogSql = `
                INSERT INTO sensor_logs
                (
                    raw_temp,
                    raw_humidity,
                    raw_lux,
                    current_speed,
                    mapped_weather,
                    mapped_surface,
                    mapped_time,
                    predicted_risk
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            `;

            db.run(
                insertLogSql,
                [
                    temp,
                    humidity,
                    lux,
                    speed,
                    mapped.mapped_weather,
                    mapped.mapped_surface,
                    mapped.mapped_time,
                    riskLevel
                ],
                function (err) {

                    if (err) {
                        console.error(err.message);
                        return;
                    }

                    const currentLogId = this.lastID;

                    // 3) 위험 알림 저장
                    if (
                        riskLevel === 'WARNING' ||
                        riskLevel === 'DANGER'
                    ) {

                        let cause =
                            `${mapped.mapped_time}시간대 ` +
                            `${mapped.mapped_weather}/` +
                            `${mapped.mapped_surface} 상태에서 ` +
                            `${speed}km/h 주행`;

                        let message =
                            riskLevel === 'DANGER'
                                ? '치명적 위험! 결빙/가시거리 불량 구간입니다. 즉시 50km/h 이하로 크게 감속하세요!'
                                : '주의 구간! 수막현상 위험이 있습니다. 서행하세요.';

                        db.run(
                            `
                            INSERT INTO alert_events
                            (
                                log_id,
                                risk_level,
                                event_cause,
                                alert_message
                            )
                            VALUES (?, ?, ?, ?)
                            `,
                            [
                                currentLogId,
                                riskLevel,
                                cause,
                                message
                            ]
                        );
                    }

                    // 4) 실시간 브로드캐스트
                    const broadcastData = {

                        log_id: currentLogId,

                        raw: {
                            temp,
                            humidity,
                            lux,
                            speed
                        },

                        mapped: mapped,

                        risk_level: riskLevel,

                        timestamp: new Date().toLocaleString()
                    };

                    io.emit('sensor_update', broadcastData);
                }
            );

            res.status(200).json({
                success: true,
                message: 'AI 분석 완료 및 DB 저장 성공',
                result: riskLevel
            });

        } catch (error) {

            console.error(
                'Flask 통신 또는 DB 에러:',
                error.message
            );

            res.status(500).json({
                success: false,
                message: '서버 에러 발생'
            });
        }
    });

    // ================================================================
    // 3. Socket.io 연결 관리
    // ================================================================
    io.on('connection', (socket) => {   // socket 연결

        console.log(
            `[Socket.io] 새로운 대시보드 클라이언트 접속: ${socket.id}`
        );

        socket.on('disconnect', () => {    // socket 끊기

            console.log(
                `[Socket.io] 클라이언트 접속 해제: ${socket.id}`
            );
        });
    });

    // 서버 실행
    const PORT = 3000;

    server.listen(PORT, () => { // localhost:3000

        console.log('=========================================');
        console.log(`🚀 Node.js 관제 서버가 포트 ${PORT}에서 실행 중입니다.`);
        console.log('=========================================');
    });
};
