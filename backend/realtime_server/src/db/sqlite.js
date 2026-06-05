const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// DB 파일 경로 설정 및 연결
const dbPath = path.join(__dirname, '../log/sensor_monitoring.db');
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error("DB 연결 오류:", err.message);
    } else {
        console.log("SQLite 데이터베이스 연결 완료");
    }
});

// 테이블 초기화
db.serialize(() => {
    // 센서 원본 및 AI 분석 결과 저장용 테이블
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

    // 위험 상태(WARNING/DANGER) 발생 시 알림 이력 저장용 테이블
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

// 비동기(Promise) 처리를 위한 래퍼(Wrapper) 객체 생성
const dbAsync = {
    run: (sql, params = []) => new Promise((resolve, reject) => {
        db.run(sql, params, function(err) {
            if (err) reject(err); 
            else resolve(this);
        });
    }),
    all: (sql, params = []) => new Promise((resolve, reject) => {
        db.all(sql, params, (err, rows) => {
            if (err) reject(err); 
            else resolve(rows);
        });
    })
};

module.exports = dbAsync;

// DB 연결 코드 작성하는곳