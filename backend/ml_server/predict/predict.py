import pandas as pd
import pickle


# =========================================================
# 머신러닝 모델 로드
# =========================================================
with open("../model/risk_model.pkl", "rb") as f:   # csv 읽기
    model = pickle.load(f)


# =========================================================
# 센서 데이터 기반 환경 분석
# =========================================================
def analyze_environment(temp, humidity, lux):    # csv를 기반으로 분석

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

    return {
        "weather": weather,
        "surface": surface,
        "time_zone": time_zone
    }


# =========================================================
# 위험 점수 계산
# =========================================================
def calculate_risk_score(speed, weather, surface):  # csv를 기반으로 분석

    score = 0

    # 속도 위험도
    if speed >= 80:
        score += 4

    elif speed >= 60:
        score += 3

    elif speed >= 40:
        score += 2

    else:
        score += 1

    # 날씨 위험도
    if weather == "RAIN":
        score += 3

    elif weather == "FOG":
        score += 4

    elif weather == "SNOW":
        score += 5

    # 노면 위험도
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
# AI 위험 예측
# =========================================================
def predict_risk(sensor_data):

    # =====================================================
    # STM32 센서 데이터 수신
    # =====================================================
    temp = sensor_data.get("temp", 0)

    humidity = sensor_data.get("humidity", 0)

    lux = sensor_data.get("lux", 0)

    speed = sensor_data.get("speed", 0)


    # =====================================================
    # 환경 분석
    # =====================================================
    env = analyze_environment(
        temp,
        humidity,
        lux
    )


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
    # RandomForest 기반 위험 예측
    # =====================================================
    ai_prediction = model.predict(input_df)[0]


    # =====================================================
    # 규칙 기반 위험 점수 계산
    # =====================================================
    risk_score = calculate_risk_score(
        speed,
        env["weather"],
        env["surface"]
    )


    # =====================================================
    # 위험 단계 분류
    # =====================================================
    risk_level = classify_risk(risk_score)


    # =====================================================
    # 최종 결과 반환
    # =====================================================
    return {

        # AI 예측 결과
        "ai_prediction": str(ai_prediction),

        # 규칙 기반 위험 분석
        "risk_score": risk_score,
        "risk_level": risk_level,

        # 센서 기반 환경 분석 결과
        "environment": {

            "weather": env["weather"],

            "surface": env["surface"],

            "time_zone": env["time_zone"]
        },

        # 원본 센서 데이터
        "sensor_data": {

            "temp": temp,

            "humidity": humidity,

            "lux": lux,

            "speed": speed
        }
    }

