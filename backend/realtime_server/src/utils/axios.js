// RestAPI 중의 POST, 비동기 통신 방식 중 하나인 axios.
const axios = require('axios');

// AI 예측 서버 (Flask) URL
const AI_SERVER_URL = 'http://127.0.0.1:5000/predict_risk';

// 센서 데이터를 바탕으로 AI 위험도 예측 결과를 요청하는 비동기 함수
const getAiPrediction = async (sensorData) => {
    try {
        const response = await axios.post(AI_SERVER_URL, sensorData);
        return response.data;
    } catch (error) {
        console.error("AI 예측 서버 통신 실패:", error.message);
        throw new Error("AI 서버와 연결할 수 없습니다. 서버 상태를 확인해주세요."); 
    }
};

module.exports = { getAiPrediction };