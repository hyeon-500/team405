from flask import Flask, request, jsonify
import pandas as pd
import joblib
import os
import traceback

app = Flask(__name__)

# 경로 꼬임 방지를 위한 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'model', 'risk_model.pkl')

# 전역 변수로 모델 미리 로드
model = None
try:
    model = joblib.load(MODEL_PATH)
    print(f"모델 로드 성공: {MODEL_PATH}")
except Exception as e:
    print(f"모델 파일 로드 실패. 'train_model.py'를 먼저 실행했는지 확인 필요!\n에러: {e}")

# 기상별 기본 치사율 가중치 (도로교통공단 통계 기준)
BASE_FATALITY_RATES = {'Clear': 1.24, 'Rain': 1.64, 'Snow': 1.50, 'Fog': 9.90, 'Cloudy': 1.30}

@app.route('/', methods=['GET'])
def home():
    return "<h1>AI 관제 API 서버 동작 중 </h1><p>센서 데이터는 /predict_risk 엔드포인트로 POST 요청해 주세요.</p>"

@app.route('/predict_risk', methods=['POST'])
def predict_risk():
    if model is None:
        return jsonify({"success": False, "error": "AI 모델이 초기화되지 않았습니다. 서버 상태를 확인해 주세요."}), 503

    try:
        data = request.json
        
        temp = float(data.get('temp', 20.0))
        humidity = float(data.get('humidity', 50.0))
        lux = float(data.get('lux', 500.0))
        speed = int(data.get('speed', 60))

        # 조도(lux) 센서값 기준으로 주야간 판별
        if lux < 10: mapped_time = 'Night'
        elif lux < 400: mapped_time = 'Dawn'
        else: mapped_time = 'Daylight'

        # 온습도 조건에 따른 기상/노면 상태 매핑
        if humidity >= 85:
            if temp <= 0: 
                mapped_weather, mapped_surface = 'Snow', 'Icy'
            # 온도 0~10도 사이이면서 새벽/야간일 경우 안개 낀 젖은 도로로 간주 (사고 위험도 높임)
            elif 0 < temp <= 10 and mapped_time in ['Dawn', 'Night']: 
                mapped_weather, mapped_surface = 'Fog', 'Wet'
            else: 
                mapped_weather, mapped_surface = 'Rain', 'Wet'
        elif 65 <= humidity < 85:
            mapped_weather, mapped_surface = 'Cloudy', 'Dry'
        else:
            mapped_weather, mapped_surface = 'Clear', 'Dry'

        # 매핑된 환경을 바탕으로 한국형 치사율 가중치 계산
        base_weight = BASE_FATALITY_RATES.get(mapped_weather, 1.24)
        surface_mult = 1.5 if mapped_surface == 'Icy' else (1.2 if mapped_surface == 'Wet' else 1.0)
        time_mult = 1.3 if mapped_time in ['Night', 'Dawn'] else 1.0
        fatality_weight = round(base_weight * surface_mult * time_mult, 2)

        # 모델 입력용 데이터프레임 구성
        # (조도 센서의 민감도를 높이기 위해 Time_of_Day 특성은 예측에서 제외)
        input_df = pd.DataFrame([{
            'Weather': mapped_weather,
            'Road_Surface': mapped_surface,
            # 'Time_of_Day': mapped_time,  
            'Speed': speed,
            'lux': lux,  
            'korea_fatality_weight': fatality_weight
        }])

        # 예측 결과 추출
        predicted_risk_str = str(model.predict(input_df))

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
        error_msg = traceback.format_exc()
        print(f"[예측 API 내부 오류 발생]\n{error_msg}")
        return jsonify({
            "success": False, 
            "error": "예측 처리 중 서버 내부 오류가 발생했습니다.",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)