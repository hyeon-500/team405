# ============================================================
# 공통 설정 셀
# ============================================================
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
import matplotlib.pyplot as plt
import matplotlib
import platform, warnings
warnings.filterwarnings('ignore')

# 한글 폰트 OS 자동 감지
try:
    if platform.system() == 'Windows':
        matplotlib.rc('font', family='Malgun Gothic')
    elif platform.system() == 'Darwin':
        matplotlib.rc('font', family='AppleGothic')
    else:
        from matplotlib import font_manager
        fp = font_manager.findfont(font_manager.FontProperties(family='NanumGothic'))
        if 'Nanum' in fp:
            matplotlib.rc('font', family='NanumGothic')
except Exception as e:
    print(f'폰트 설정 실패: {e}')
matplotlib.rc('axes', unicode_minus=False)
print('✅ 공통 설정 완료')

import pandas as pd
import glob
import os

# =========================
# 파일 읽기
# =========================

try:
    df = pd.read_csv("./dataset/ai_master_dataset.csv",encoding='cp949') # encoding='utf-8'

except Exception as e:
    print(f"오류 발생: {e}")

X = df[
    [
        'Weather',
        'Road_Surface',
        'Time_of_Day',
        'injuries_total',
        'korea_fatality_weight'  
    ]
]

y = df['Risk_Level']  # x, y 나누고

encoder = LabelEncoder()

X['Weather'] = encoder.fit_transform(X['Weather'])

X['Road_Surface'] = encoder.fit_transform(
    X['Road_Surface']
)

X['Time_of_Day'] = encoder.fit_transform(
    X['Time_of_Day']
)

y = encoder.fit_transform(y)   # DecisionTree를 쓰려면 문자는 encode로 변환


X_train, X_test, y_train, y_test = train_test_split(  # train/test 분리
    X, y, test_size=0.2, random_state=42
)

model = DecisionTreeClassifier()   # 학습 모델이 DecisionTree

model.fit(X_train, y_train)   # 머신러닝 학습

accuracy = model.score(X_test, y_test)   

print("정확도 :", accuracy)   # 정확도 확인


joblib.dump(model, "./risk_model.pkl")   # 파일 변환
