from flask import Flask, request, jsonify
import pandas as pd
import joblib
import os
import traceback
from datetime import datetime
import pytz

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
        
        # Node.js에서 넘겨준 기상청 강수 형태(rainType) 받기
        rain_type = int(data.get('rainType', 0))

        # '한국 현재 시각(KST)' 기준으로 주야간 완벽 분리
        kst = pytz.timezone('Asia/Seoul')
        current_hour = datetime.now(kst).hour

        if 6 <= current_hour < 18:
            mapped_time = 'Daylight'  # 아침 6시 ~ 오후 5시 59분
        elif 18 <= current_hour < 24:
            mapped_time = 'Night'     # 저녁 6시 ~ 밤 11시 59분
        else:
            mapped_time = 'Dawn'      # 자정 ~ 새벽 5시 59분

      
        # 하이픈(-) 대신 쉼표(,)를 사용해 기상청 PTY 코드 나열
        if rain_type in [3, 4, 9]:
            # 기상청 PTY 1(비), 4(소나기), 5(빗방울)
            mapped_weather, mapped_surface = 'Rain', 'Wet'
            
        elif rain_type in [1, 2, 5, 6]:
            # 기상청 PTY 2(비/눈), 3(눈), 6(빗방울눈날림), 7(눈날림)
            mapped_weather = 'Snow'
            # 눈이 오더라도 기온이 영상이면 젖음(Wet), 영하면 빙판(Icy)으로 처리
            mapped_surface = 'Icy' if temp <= 0 else 'Wet'
            
        else:
            # 기상청 PTY 0(강수 없음)
            if 0 < temp <= 10 and humidity >= 85 and mapped_time in ['Dawn', 'Night']:
                mapped_weather, mapped_surface = 'Fog', 'Wet'
            elif temp <= 0 and humidity >= 85:
                mapped_weather, mapped_surface = 'Cloudy', 'Icy'
            elif humidity >= 65:
                mapped_weather, mapped_surface = 'Cloudy', 'Dry'
            else:
                mapped_weather, mapped_surface = 'Clear', 'Dry'

        # 매핑된 환경을 바탕으로 한국형 치사율 가중치 계산
        base_weight = BASE_FATALITY_RATES.get(mapped_weather, 1.24)
        surface_mult = 1.5 if mapped_surface == 'Icy' else (1.2 if mapped_surface == 'Wet' else 1.0)
        time_mult = 1.3 if mapped_time in ['Night', 'Dawn'] else 1.0
        fatality_weight = round(base_weight * surface_mult * time_mult, 2)

       
        input_df = pd.DataFrame([{
            'Weather': mapped_weather,
            'Road_Surface': mapped_surface,
            'Time_of_Day': mapped_time,   
            'Speed': speed,
            'lux': lux,  
            'korea_fatality_weight': fatality_weight
        }])

        
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