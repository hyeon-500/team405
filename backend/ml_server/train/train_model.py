# train_model.py

import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

def train_and_save_model(data_path='./data/ai_master_dataset.csv', model_path='./risk_model.pkl'):
    print(f"[{data_path}] 파일에서 데이터를 불러옵니다...")
    
    # 1. 데이터 로드
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"데이터 파일이 없습니다. 전처리 코드를 먼저 실행해 주세요: {data_path}")
        
    df = pd.read_csv(data_path)

    # 2. 특성(X)과 라벨(y) 분리
    X = df[['Weather', 'Road_Surface', 'Time_of_Day', 'Speed', 'korea_fatality_weight']]
    y = df['Risk_Level']

    # 3. 전처리 파이프라인 생성
    categorical_features = ['Weather', 'Road_Surface', 'Time_of_Day']
    numeric_features = ['Speed', 'korea_fatality_weight']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])

    # 4. 모델 파이프라인 생성 (★사용자 제안: 과적합 방지 하이퍼파라미터 적용)
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, 
                                              max_depth=10,             # 트리 깊이 제한 추가
                                              min_samples_split=5,      # 분할 최소 샘플 수 추가
                                              random_state=42, 
                                              class_weight='balanced',
                                              n_jobs=-1))
    ])

    # 5. 데이터 분할
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 6. 모델 학습
    print("RandomForest 모델 학습을 시작합니다...")
    model_pipeline.fit(X_train, y_train)

    # 7. 모델 성능 평가
    y_pred = model_pipeline.predict(X_test)
    print("\n[모델 평가 결과]")
    print(f"정확도(Accuracy): {accuracy_score(y_test, y_pred):.4f}")
    print("-" * 55)
    print(classification_report(y_test, y_pred))
    print("-" * 55)

    # 8. ★사용자 제안: 변수 중요도(Feature Importance) 추출
    try:
        # 원핫 인코딩된 범주형 특성 이름 가져오기
        cat_features = preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_features)
        all_features = numeric_features + list(cat_features)
        
        # 모델의 변수 중요도 추출
        importances = model_pipeline.named_steps['classifier'].feature_importances_
        
        # 중요도 순으로 정렬하여 출력
        feature_importance_df = pd.DataFrame({'Feature': all_features, 'Importance': importances})
        print("\n[변수 중요도 Top 5]")
        print(feature_importance_df.sort_values(by='Importance', ascending=False).head(5))
        print("-" * 55)
    except Exception as e:
        print(f"\n[변수 중요도 추출 중 오류 발생]: {e}")

    # 9. 모델 저장
    joblib.dump(model_pipeline, model_path)
    print(f"성공적으로 통합 저장되었습니다: {model_path}")

# 실행
if __name__ == "__main__":
    train_and_save_model()