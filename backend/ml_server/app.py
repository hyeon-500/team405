# app.py

from flask import Flask, request, jsonify
import pandas as pd
import joblib
import os
import traceback

app = Flask(__name__)

# =================================================================
# 절대 경로 설정
# =================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'model', 'risk_model.pkl')

# 모델 로드 (전역 변수 설정)
model = None
try:
    model = joblib.load(MODEL_PATH)
    print(f"AI 모델 로드 완료: {MODEL_PATH}")
except Exception as e:
    print(f"모델 로드 실패! 'train_model.py'를 먼저 실행해 주세요.\n에러: {e}")

BASE_FATALITY_RATES = {'Clear': 1.24, 'Rain': 1.64, 'Snow': 1.50, 'Fog': 9.90, 'Cloudy': 1.30}

@app.route('/', methods=['GET'])
def home():
    return "<h1>AI 관제 API 서버가 정상 가동 중입니다!</h1><p>STM32 센서 데이터는 POST 방식으로 '/predict_risk' 경로에 전송해주세요.</p>"

@app.route('/predict_risk', methods=['POST'])
def predict_risk():
    # 모델이 로드되지 않았을 경우 에러
    if model is None:
        return jsonify({"success": False, "error": "AI 모델이 초기화되지 않았습니다. 관리자에게 문의하세요."}), 503

    try:
        data = request.json
        
        temp = float(data.get('temp', 20.0))
        humidity = float(data.get('humidity', 50.0))
        lux = float(data.get('lux', 500.0))
        speed = int(data.get('speed', 60))

        # 센서 데이터 기반 매핑 로직
        if lux < 10: mapped_time = 'Night'
        elif lux < 400: mapped_time = 'Dawn'
        else: mapped_time = 'Daylight'

        if humidity >= 80:
            if temp <= 0: mapped_weather, mapped_surface = 'Snow', 'Icy'
            else: mapped_weather, mapped_surface = 'Rain', 'Wet'
        else: mapped_weather, mapped_surface = 'Clear', 'Dry'

        base_weight = BASE_FATALITY_RATES.get(mapped_weather, 1.24)
        surface_mult = 1.5 if mapped_surface == 'Icy' else (1.2 if mapped_surface == 'Wet' else 1.0)
        time_mult = 1.3 if mapped_time in ['Night', 'Dawn'] else 1.0
        fatality_weight = round(base_weight * surface_mult * time_mult, 2)

        # =================================================================
        # 조도 민감도 조정을 위해 Time_of_Day를 빼고 5개 특성을 넘김
        # =================================================================
        input_df = pd.DataFrame([{
            'Weather': mapped_weather,
            'Road_Surface': mapped_surface,
            # 'Time_of_Day': mapped_time,  
            'Speed': speed,
            'lux': lux,  
            'korea_fatality_weight': fatality_weight
        }])

        # 4. 예측 결과 추출
        predicted_risk_str = str(model.predict(input_df)[0])

        response = {
            "success": True,
            "raw_sensor_data": {"temp": temp, "humidity": humidity, "lux": lux, "current_speed": speed},
            "mapped_features": {
                "mapped_weather": mapped_weather,
                "mapped_surface": mapped_surface,
                "mapped_time": mapped_time,
                "korea_fatality_weight": fatality_weight
            },
            "predicted_risk": predicted_risk_str
        }
        return jsonify(response), 200

    except Exception as e:
        # 서버 에러 발생 시 JSON 반환
        error_msg = traceback.format_exc()
        print(f"[예측 API 에러 발생]\n{error_msg}")
        return jsonify({
            "success": False, 
            "error": "예측 처리 중 서버 내부 오류가 발생했습니다.",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)