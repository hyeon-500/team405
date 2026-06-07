

const db = require('../../../database/sqlite/sqlite');

// WARNING, DANGER 이벤트 저장
async function saveAlert(
      currentLogId,
      riskLevel,
      mapped,
      speed
) {

    // SAFE는 저장 안 함
      if (
            riskLevel !== 'WARNING' &&
            riskLevel !== 'DANGER'
      ) {
            return;
      }

      const cause =
            `${mapped.mapped_time}시간대 ` +
            `${mapped.mapped_weather}/` +
            `${mapped.mapped_surface} 상태에서 ` +
            `${speed}km/h 주행`;

      const alertMessage =
            riskLevel === 'DANGER'
                  ? "치명적 위험! 즉시 50km/h 이하로 크게 감속하세요!"
                  : "주의 구간! 서행하세요.";

      await db.run(
            `INSERT INTO alert_events
            (
                  log_id,
                  risk_level,
                  event_cause,
                  alert_message
            )
            VALUES (?, ?, ?, ?)`,
            [
                  currentLogId,
                  riskLevel,
                  cause,
                  alertMessage
            ]
      );

      }

module.exports = {
      saveAlert
};