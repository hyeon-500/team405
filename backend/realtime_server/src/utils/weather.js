// utils/weather.js
const axios = require('axios');
const { convertToKmaGrid } = require('./weatherxy'); // 격자 변환 모듈

async function getRealtimeWeather(lat, lon) {
    const { nx, ny } = convertToKmaGrid(lat, lon);
    const now = new Date();
    
    let year = now.getFullYear();
    let month = ('0' + (now.getMonth() + 1)).slice(-2);
    let day = ('0' + now.getDate()).slice(-2);
    let hours = now.getHours();
    let minutes = now.getMinutes();

    // 초단기실황은 매 정시에 관측 후 10분 이후에 제공되므로 방어 로직 적용
    if (minutes < 10) {
        hours = hours - 1;
        if (hours < 0) {
            now.setDate(now.getDate() - 1);
            year = now.getFullYear();
            month = ('0' + (now.getMonth() + 1)).slice(-2);
            day = ('0' + now.getDate()).slice(-2);
            hours = 23;
        }
    }
    
    const base_date = `${year}${month}${day}`;
    const base_time = ('0' + hours).slice(-2) + '00';
    
    // 공공데이터포털에서 발급받은 '일반 인증키(Decoding)' 입력
    const API_KEY = 'px9wOTSbToCfcDk0m06AlA'; 
    const url = 'https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtNcst';

    try {
        const response = await axios.get(url, {
            params: {
                authKey: API_KEY, 
                numOfRows: 10,
                pageNo: 1,
                dataType: 'JSON',
                base_date: base_date,
                base_time: base_time,
                nx: nx,
                ny: ny
            },
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        });

        // 기상청 JSON 응답 데이터 파싱
        const items = response.data.response.body.items.item;
        let weatherData = { temp: null, humidity: null, rainType: null, rainAmount: null };

        items.forEach(item => {
            if (item.category === 'T1H') weatherData.temp = parseFloat(item.obsrValue);       // 기온
            if (item.category === 'REH') weatherData.humidity = parseFloat(item.obsrValue);   // 습도
            if (item.category === 'PTY') weatherData.rainType = parseInt(item.obsrValue);     // 강수형태
            if (item.category === 'RN1') weatherData.rainAmount = parseFloat(item.obsrValue); // 강수량
        });

        console.log(`[기상청 API 연동 성공] 격자(${nx},${ny}) -> 기온: ${weatherData.temp}℃, 습도: ${weatherData.humidity}%`);
        return weatherData;

    } catch (error) {
        console.error("[기상청 API 호출 에러]:", error.message);
        return null;
    }
}

module.exports = { getRealtimeWeather };