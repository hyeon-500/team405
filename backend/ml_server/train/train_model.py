# train_model.py

import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, RobustScaler # ★ StandardScaler 대신 RobustScaler 사용
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# 무적의 폴더 분리형 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
ML_SERVER_DIR = os.path.dirname(BASE_DIR)             
DEFAULT_DATA_PATH = os.path.join(ML_SERVER_DIR, 'dataset', 'ai_master_dataset.csv')
DEFAULT_MODEL_PATH = os.path.join(ML_SERVER_DIR, 'model', 'risk_model.pkl')

def train_and_save_model(data_path=DEFAULT_DATA_PATH, model_path=DEFAULT_MODEL_PATH):
    print(f"[{data_path}] 파일에서 데이터를 불러옵니다...")
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"데이터 파일이 없습니다. 전처리 코드를 먼저 실행해 주세요: {data_path}")
        
    df = pd.read_csv(data_path)

    X = df[['Weather', 'Road_Surface', 'Speed', 'lux', 'korea_fatality_weight']]
    y = df['Risk_Level']

    # 2. 전처리 파이프라인 생성 (여기서도 Time_of_Day 제거)
    categorical_features = ['Weather', 'Road_Surface']
    numeric_features = ['Speed', 'lux', 'korea_fatality_weight']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', RobustScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])
    
    # 3. 모델 파이프라인 생성 (안정적인 설정은 그대로 유지)
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

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("RandomForest 모델 학습을 시작합니다... (하이퍼파라미터 튜닝 적용)")
    model_pipeline.fit(X_train, y_train)

    y_pred = model_pipeline.predict(X_test)
    print("\n[모델 평가 결과]")
    print(f"정확도(Accuracy): {accuracy_score(y_test, y_pred):.4f}")
    print("-" * 55)
    print(classification_report(y_test, y_pred))
    print("-" * 55)

    try:
        cat_features = preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_features)
        all_features = numeric_features + list(cat_features)
        
        importances = model_pipeline.named_steps['classifier'].feature_importances_
        
        feature_importance_df = pd.DataFrame({'Feature': all_features, 'Importance': importances})
        print("\n[변수 중요도 Top 5]")
        print(feature_importance_df.sort_values(by='Importance', ascending=False).head(5))
        print("-" * 55)
    except Exception as e:
        print(f"\n[변수 중요도 추출 중 오류 발생]: {e}")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model_pipeline, model_path)
    print(f"조도(lux) 민감도 극대화 모델 통합 저장 완료: {model_path}")

if __name__ == "__main__":
    train_and_save_model()