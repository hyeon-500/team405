import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# 프로젝트 폴더 구조가 바뀌어도 경로가 꼬이지 않도록 절대 경로로 고정
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
ML_SERVER_DIR = os.path.dirname(BASE_DIR)             
DEFAULT_DATA_PATH = os.path.join(ML_SERVER_DIR, 'dataset', 'ai_master_dataset.csv')
DEFAULT_MODEL_PATH = os.path.join(ML_SERVER_DIR, 'model', 'risk_model.pkl')

def train_and_save_model(data_path=DEFAULT_DATA_PATH, model_path=DEFAULT_MODEL_PATH):
    print(f"데이터셋 불러오는 중... [{data_path}]")
    
    if not os.path.exists(data_path):
        raise FileNotFoundError("데이터셋 파일이 없습니다. 'preprocess.py'를 먼저 실행해서 데이터를 생성해 주세요.")
        
    df = pd.read_csv(data_path)

    # 학습 피처(X)와 타겟(y) 분리
    # (조도 센서값의 민감도를 위해 'Time_of_Day' 특성은 의도적으로 학습에서 배제)
    X = df[['Weather', 'Road_Surface', 'Speed', 'lux', 'korea_fatality_weight']]
    y = df['Risk_Level']

    # 전처리 파이프라인 설정
    categorical_features = ['Weather', 'Road_Surface']
    numeric_features = ['Speed', 'lux', 'korea_fatality_weight']

    # 수치형 데이터(속도, 조도 등)에 섞여 있을 수 있는 이상치(Outlier)의 영향을 최소화하기 위해 
    # 일반적인 StandardScaler 대신 RobustScaler를 적용
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', RobustScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])
    
    # 모델 파이프라인 (RandomForest)
    # 데이터 불균형 해결을 위해 class_weight='balanced'를 적용하고, 오버피팅을 막기 위해 파라미터 제어
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100,         
                                              max_depth=6,              
                                              min_samples_split=20,     
                                              min_samples_leaf=5,       
                                              random_state=42, 
                                              class_weight='balanced',
                                              n_jobs=-1))
    ])

    # Train / Test 데이터 분할 (라벨 비율이 깨지지 않도록 stratify 적용)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("RandomForest 모델 학습 시작...")
    model_pipeline.fit(X_train, y_train)

    # 모델 평가 수행
    y_pred = model_pipeline.predict(X_test)
    print("\n[모델 평가 결과]")
    print(f"정확도(Accuracy): {accuracy_score(y_test, y_pred):.4f}\n")
    print(classification_report(y_test, y_pred))

    # 변수 중요도 확인 (의도한 대로 lux와 Speed가 모델 예측에 주요하게 작용했는지 검증용)
    try:
        cat_features = preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_features)
        all_features = numeric_features + list(cat_features)
        
        importances = model_pipeline.named_steps['classifier'].feature_importances_
        
        feature_importance_df = pd.DataFrame({'Feature': all_features, 'Importance': importances})
        print("\n💡 [변수 중요도 Top 5]")
        print(feature_importance_df.sort_values(by='Importance', ascending=False).head(5).to_string(index=False))
        print("\n")
    except Exception as e:
        print(f"\n⚠️ 변수 중요도 추출 중 오류 발생: {e}")

    # 모델 저장 (경로상에 폴더가 없으면 자동 생성)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model_pipeline, model_path)
    print(f"모델 저장 완료 (조도 민감도 극대화 및 로버스트 스케일링 적용): {model_path}")

if __name__ == "__main__":
    train_and_save_model()