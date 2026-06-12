// 웹 화면에 데이터 제공 담당하고 REST API를 구현하는 파일

const express = require('express');
const router = express.Router();
const db = require('../../../database/sqlite/sqlite'); // 비동기 DB 모듈

// 최근 센서 로그 50개 조회 API
router.get('/logs', async (req, res) => {
    try {
        const logs = await db.all("SELECT * FROM sensor_logs ORDER BY timestamp DESC LIMIT 50");
        res.json({ success: true, data: logs });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// 위험 이벤트 발생 이력 전체 조회 API
router.get('/alerts', async (req, res) => {
    try {
        const alerts = await db.all("SELECT * FROM alert_events ORDER BY timestamp DESC");
        res.json({ success: true, data: alerts });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

module.exports = router;