from flask import Flask, request, jsonify
from predict import predict_risk

# =========================================================
# Flask 서버 생성
# =========================================================
app = Flask(__name__)


# =========================================================
# 위험도 예측 API
# =========================================================

@app.route('/predict_risk', methods=['POST'])    # localhost:5000/predict_risk, post(생성)
def predict():

    try:

        # Node.js 관제 서버에서 전달받은 센서 데이터
        sensor_data = request.json

        print("[수신 센서 데이터]")
        print(sensor_data)

        # AI 위험도 분석
        result = predict_risk(sensor_data)

        print("[AI 분석 결과]")
        print(result)

        # JSON 응답 반환
        return jsonify(result)

    except Exception as e:

        print("에러 발생:", str(e))

        return jsonify({
            "success": False,
            "message": "AI 서버 처리 실패"
        }), 500


# =========================================================
# Flask 서버 실행
# =========================================================

if __name__ == '__main__':    # localhost:5000에서 실행
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

# 실시간으로 ESP32로부터 STM32 데이터받고 AI 결과 반환하는 서버