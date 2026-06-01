from flask import jsonify
import pandas as pd
import pickle


# =========================================================
# 머신러닝 모델 로드
# =========================================================
with open("../model/risk_model.pkl", "rb") as f:   # 파일 읽기
    model = pickle.load(f)


# =========================================================
# 위험 점수 알고리즘
# =========================================================
def calculate_risk_score(speed, weather, surface):
    score = 0
    # 속도 기준
    if speed >= 80:   # 기준값은 임의로 생성되었으며 나중에 STM32 를 바탕으로 수정될 수 있음
        score += 4
    elif speed >= 60:
        score += 3
    elif speed >= 40:
        score += 2
    else:
        score += 1

    # 날씨 기준
    if weather == "RAIN":
        score += 3
    elif weather == "FOG":
        score += 4
    elif weather == "SNOW":
        score += 5

    # 노면 상태 기준
    if surface == "WET":
        score += 3
    elif surface == "ICE":
        score += 5

    return score


# =========================================================
# 위험 단계 분류
# =========================================================
def classify_risk(score):

    if score >= 10:
        return "DANGER"

    elif score >= 6:
        return "WARNING"

    else:
        return "SAFE"


# =========================================================
# AI 위험도 예측 함수
# =========================================================
def predict_risk(sensor_data):
    temp = sensor_data.get("temp")      # STM32에서 넘어온 센서 데이터
    humidity = sensor_data.get("humidty")
    lux = sensor_data.get("lux")
    speed = sensor_data.get("speed")


    # =====================================================
    # 센서 데이터 기반 환경 매핑
    # =====================================================

    # 날씨 판단
    if humidity >= 80:
        weather = "RAIN"

    elif lux <= 100:
        weather = "FOG"

    else:
        weather = "CLEAR"


    # 노면 상태 판단
    if temp <= 0:
        surface = "ICE"

    elif humidity >= 70:
        surface = "WET"

    else:
        surface = "DRY"


    # 시간대 판단
    if lux <= 50:
        time_zone = "NIGHT"

    else:
        time_zone = "DAY"


    # =====================================================
    # 머신러닝 입력 데이터 생성
    # =====================================================
    input_df = pd.DataFrame([{
        "temp": temp,
        "humidity": humidity,
        "lux": lux,
        "speed": speed
    }])


    # =====================================================
    # RandomForest 위험 예측
    # =====================================================
    prediction = model.predict(input_df)[0]


    # =====================================================
    # 위험 점수 계산
    # =====================================================
    risk_score = calculate_risk_score(
        speed,
        weather,
        surface
    )


    # =====================================================
    # 위험 단계 분류
    # =====================================================
    risk_level = classify_risk(risk_score)


    # =====================================================
    # 결과 반환
    # =====================================================
    return {

        "predicted_risk": str(prediction),

        "risk_score": risk_score,

        "risk_level": risk_level,

        "mapped_features": {

            "mapped_weather": weather,
            "mapped_surface": surface,
            "mapped_time": time_zone
        }
    }

