// const { SerialPort } = require('serialport');
// const { ReadlineParser } = require('@serialport/parser-readline');
// const db = require('./db'); 

// let latestData = null;
// let dataCallback = null;

// function onData(callback) { dataCallback = callback; }

// function saveToDB(data) {
//   const stmt = db.prepare(
//     'INSERT INTO sensor_data (sensor, temp, humi, lux, received_at) VALUES (?, ?, ?, ?, ?)'  // 향후 변경
//   );
//   stmt.run(
//     'NUCLEO',
//     data.temp, 
//     data.humi, 
//     data.lux,  
//     data.receivedAt
//   );
//   console.log(`[DB] 저장 완료: temp=${data.t ?? data.temp}`);
// }

// function startSerialReader() {
//   // 포트 번호가 COM3가 맞는지 꼭 확인하세요!
//   const port = new SerialPort({ path: process.env.SERIAL_PORT || 'COM3', baudRate: 115200 });
//   const parser = port.pipe(new ReadlineParser({ delimiter: '\n' }));

//   port.on('open', () => console.log('[Serial] 포트 연결 완료'));

//   parser.on('data', (line) => {
//     const text = line.trim();
//     if (!text.startsWith('{')) return;

//     try {
//       const data = JSON.parse(text);
//       data.receivedAt = new Date().toISOString();
//       latestData = data;

//       console.log(`[Serial] 수신: temp=${data.temp} humi=${data.humi} lux=${data.lux}`);  // 향후 변경

//       saveToDB(data); // DB 저장 실행
//       if (dataCallback) dataCallback(data); // 실시간 콜백 실행
//     } catch (e) {
//       console.error('JSON 파싱 오류:', e.message);
//     }
//   });
// }

// module.exports = { startSerialReader, onData, getLatest: () => latestData };

// STM32/ESP32 에서 오는 시리얼(UART) 데이터 읽기 -> JSON으로 변환 -> app.js에 전달
