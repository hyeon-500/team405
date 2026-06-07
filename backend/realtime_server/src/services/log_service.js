


// 센서 로그 DB 저장



const db = require('../../../database/sqlite/sqlite');

// 센서 데이터 + AI 분석 결과 저장
async function saveSensorLog(
      temp,
      humidity,
      lux,
      speed,
      mapped,
      riskLevel
) {

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

      const result = await db.run(
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
            ]
      );

      return result.lastID;
}

module.exports = {
saveSensorLog
};