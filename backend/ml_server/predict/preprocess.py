# preprocess.py

import pandas as pd
import numpy as np
import glob
import os

# 1. 현재 파일(preprocess.py)이 있는 'predict' 폴더의 절대 경로를 구합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 상위 폴더(ml_server)로 한 칸 올라간 뒤, 'dataset' 폴더를 가리키도록 설정합니다.
# os.path.dirname(BASE_DIR)가 바로 'ml_server' 폴더를 의미합니다.
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'dataset')

# 3. 함수의 기본(default) 경로를 위에서 만든 완벽한 절대 경로로 지정합니다.
def create_master_dataset(data_dir=DEFAULT_DATA_DIR):
    print(f"[{data_dir}] 폴더에서 데이터 로딩 및 벡터화 전처리를 시작합니다...")
    
    # =================================================================
    # 1단계: 한국 통계 데이터 로드 및 전처리
    # =================================================================
    file_pattern = os.path.join(data_dir, '한국도로교통공단_도로종류별_기상상태별_교통사고_통계_*.csv')
    file_list = glob.glob(file_pattern)
    
    if not file_list:
        raise FileNotFoundError(f"'{data_dir}' 폴더에 한국도로교통공단 통계 파일이 없습니다.")
    
    kor_df_list = []
    for f in file_list:
        try:
            df = pd.read_csv(f, encoding='cp949')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(f, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(f, encoding='euc-kr')
        kor_df_list.append(df)
        
    kor_df = pd.concat(kor_df_list, ignore_index=True)
    
    kor_weather_to_eng = {'맑음': 'Clear', '비': 'Rain', '눈': 'Snow', '안개': 'Fog', '흐림': 'Cloudy'}
    kor_df['Weather'] = kor_df['기상상태'].map(kor_weather_to_eng).fillna('Other')
    
    kor_grouped = kor_df.groupby('Weather')[['사고건수', '사망자수']].sum().reset_index()
    
    kor_grouped['Fatality_Rate'] = np.where(
        kor_grouped['사고건수'] > 0,
        (kor_grouped['사망자수'] / kor_grouped['사고건수']) * 100, 
        0
    )
    base_fatality_mapping = dict(zip(kor_grouped['Weather'], kor_grouped['Fatality_Rate']))

    # =================================================================
    # 2단계: 해외 사고 데이터 로드 및 병합
    # =================================================================
    pred_path = os.path.join(data_dir, 'dataset_traffic_accident_prediction1.csv')
    traffic_path = os.path.join(data_dir, 'traffic_accidents.csv')
    
    if not (os.path.exists(pred_path) and os.path.exists(traffic_path)):
        raise FileNotFoundError("해외 사고 데이터 파일(CSV)이 존재하지 않습니다. 경로를 다시 확인해주세요.")
        
    df_pred = pd.read_csv(pred_path).rename(columns={'Accident_Severity': 'Severity'})
    df_traffic = pd.read_csv(traffic_path).rename(columns={
        'weather_condition': 'Weather',
        'roadway_surface_cond': 'Road_Condition',
        'crash_hour': 'Time_of_Day',
        'injuries_total': 'injuries_total',
        'injuries_fatal': 'injuries_fatal'
    })
    
    df_master = pd.concat([df_pred, df_traffic], ignore_index=True)

    # =================================================================
    # 3단계: 벡터화(Vectorization) 범주화
    # =================================================================
    w_lower = df_master['Weather'].astype(str).str.lower()
    df_master['Weather'] = np.select(
        [w_lower.str.contains('fog|smoke', na=False),
         w_lower.str.contains('rain|storm', na=False),
         w_lower.str.contains('snow|sleet', na=False)],
        ['Fog', 'Rain', 'Snow'], default='Clear'
    )
    
    s_lower = df_master['Road_Condition'].astype(str).str.lower()
    df_master['Road_Surface'] = np.select(
        [s_lower.str.contains('ice|icy|snow', na=False),
         s_lower.str.contains('wet|water', na=False)],
        ['Icy', 'Wet'], default='Dry'
    )
    
    t_str = df_master['Time_of_Day'].astype(str).str.lower()
    is_digit = t_str.str.isnumeric()
    t_num = pd.to_numeric(t_str, errors='coerce').fillna(-1)
    
    cond_day_num = is_digit & (t_num >= 6) & (t_num <= 17)
    cond_night_num = is_digit & (t_num >= 18) & (t_num <= 23)
    cond_dawn_num = is_digit & (t_num >= 0) & (t_num <= 5)
    
    cond_dawn_str = ~is_digit & t_str.str.contains('morning|dawn', na=False)
    cond_night_str = ~is_digit & t_str.str.contains('night|evening', na=False)
    
    df_master['Time_of_Day'] = np.select(
        [cond_dawn_num | cond_dawn_str, cond_night_num | cond_night_str],
        ['Dawn', 'Night'], default='Daylight'
    )
    
    if 'injuries_total' not in df_master.columns: df_master['injuries_total'] = 0
    if 'injuries_fatal' not in df_master.columns: df_master['injuries_fatal'] = 0
    df_master['injuries_total'] = df_master['injuries_total'].fillna(0).astype(int)
    df_master['injuries_fatal'] = df_master['injuries_fatal'].fillna(0).astype(int)

    # =================================================================
    # 4단계: 복합 가중치 산출
    # =================================================================
    base_weight = df_master['Weather'].map(base_fatality_mapping).fillna(1.0)
    surface_mult = np.select([df_master['Road_Surface'] == 'Icy', df_master['Road_Surface'] == 'Wet'], [1.5, 1.2], default=1.0)
    time_mult = np.where(df_master['Time_of_Day'].isin(['Night', 'Dawn']), 1.3, 1.0)
    df_master['korea_fatality_weight'] = np.round(base_weight * surface_mult * time_mult, 2)

    # =================================================================
    # 5단계: 권장 속도 역산 및 Risk_Level 산출
    # =================================================================
    np.random.seed(42)
    
    cond_rec_50 = (df_master['Weather'] == 'Fog') | (df_master['Road_Surface'] == 'Icy')
    cond_rec_80 = df_master['Weather'].isin(['Rain', 'Snow']) | (df_master['Road_Surface'] == 'Wet')
    
    # 명시적 범위 할당
    rec_speed = np.select([cond_rec_50, cond_rec_80], [50, 80], default=100)

    is_fatal = (df_master['injuries_fatal'] > 0) | (df_master.get('Severity') == 'High')
    is_injured = (df_master['injuries_total'] > 0) | (df_master.get('Severity') == 'Moderate')
    is_high_weight = df_master['korea_fatality_weight'] > 2.5

    low_bounds = np.select(
        [is_fatal, is_injured & is_high_weight, is_injured],
        [rec_speed + 30, rec_speed + 10, rec_speed - 10], default=30
    )
    high_bounds = np.select(
        [is_fatal, is_injured & is_high_weight, is_injured],
        [150, rec_speed + 31, rec_speed + 16], default=rec_speed + 6
    )
    
    # 무조건 low가 high보다 작게 보정 (에러 차단)
    high_bounds = np.maximum(low_bounds + 1, high_bounds)
    
    df_master['Speed'] = [np.random.randint(low, high) for low, high in zip(low_bounds, high_bounds)]

    conditions = [
        # 🔴 DANGER 조건 (아래 중 하나라도 걸리면 치명적 위험)
        (df_master['Weather'] == 'Fog') | 
        (df_master['Road_Surface'] == 'Icy') | 
        (df_master['injuries_fatal'] > 0) | 
        (df_master.get('Severity') == 'High') |
        ((df_master['Time_of_Day'] == 'Night') & (df_master['Weather'].isin(['Rain', 'Snow']))), # [추가] 밤인데 비나 눈이 오면 최악의 시야 + 미끄러움 = DANGER!
        
        # 🟡 WARNING 조건 (아래 중 하나라도 걸리면 주의)
        (df_master['injuries_total'] > 0) | 
        (df_master['Weather'].isin(['Rain', 'Snow'])) | 
        (df_master['Road_Surface'] == 'Wet') | 
        (df_master.get('Severity') == 'Moderate') |
        (df_master['Time_of_Day'].isin(['Night', 'Dawn'])) # 🔥 [추가] 밤이나 새벽(어두운 상태)이면 기본적으로 WARNING을 깔고 감!
    ]
    choices = ['DANGER', 'WARNING']
    df_master['Risk_Level'] = np.select(conditions, choices, default='SAFE')

    # =================================================================
    # 6단계: 조도(lux) 데이터 가상 생성 및 병합
    # =================================================================
    np.random.seed(42) # 난수 고정
    size = len(df_master)

    # 주야간(Time_of_Day)을 기준으로 현실적인 기본 조도(lux) 생성
    lux_cond = [df_master['Time_of_Day'] == 'Daylight', 
                df_master['Time_of_Day'] == 'Dawn', 
                df_master['Time_of_Day'] == 'Night']
    
    # 낮: 1000~5000, 새벽/어스름: 50~400, 밤: 0~50
    df_master['lux'] = np.select(lux_cond, 
                                 [np.random.uniform(1000, 5000, size), 
                                  np.random.uniform(50, 400, size), 
                                  np.random.uniform(0, 50, size)], 
                                 default=0)
    
    # 악천후 시 조도 감소 패널티 (낮이라도 비나 안개가 오면 어두워짐)
    df_master.loc[df_master['Weather'].isin(['Fog', 'Rain', 'Snow']), 'lux'] *= 0.4

    # 소수점 1자리로 깔끔하게 반올림
    df_master['lux'] = np.round(df_master['lux'], 1)

    # =================================================================
    # 7단계: 기존 컬럼 + 조도(lux) 유지하여 최종 저장
    # =================================================================
    final_columns = ['Weather', 'Road_Surface', 'Time_of_Day', 'Speed', 'lux', 'korea_fatality_weight', 'Risk_Level']
    ai_master_dataset = df_master[final_columns].copy().dropna()
    
    output_file = os.path.join(data_dir, 'ai_master_dataset.csv')
    ai_master_dataset.to_csv(output_file, index=False)
    print(f"데이터셋 생성 완료: {output_file}")
    
    return ai_master_dataset

if __name__ == "__main__":
    # ✅ 괄호 안을 비우면, 위에서 정의한 DEFAULT_DATA_DIR가 자동으로 들어갑니다.
    master_df = create_master_dataset()