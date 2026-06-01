// =================================================================
// 1. SQLite 데이터베이스 초기화 및 테이블 생성
// =================================================================
const sqlite3 = require('sqlite3').verbose();
const db = new sqlite3.Database('./log/sensor_monitoring.db', (err) => {
    if (err) console.error("DB 연결 실패:", err.message);
    else console.log("✓ SQLite 데이터베이스(sensor_monitoring.db) 연결 완료");
});

db.serialize(() => {
    // 센서 로그 테이블 생성 (모든 통신 기록)
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

    // 위험 이벤트 알림 테이블 생성 (WARNING / DANGER 발생 시)
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

module.exports = db;