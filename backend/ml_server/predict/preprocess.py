import pandas as pd
import numpy as np
import glob
import os

# 절대 경로 고정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'dataset')

def create_master_dataset(data_dir=DEFAULT_DATA_DIR):
    print(f"데이터셋 로딩 및 전처리 시작... [경로: {data_dir}]")
    
    # 한국 통계 데이터(도로교통공단) 로드 및 전처리
    file_pattern = os.path.join(data_dir, '한국도로교통공단_도로종류별_기상상태별_교통사고_통계_*.csv')
    file_list = glob.glob(file_pattern)
    
    if not file_list:
        raise FileNotFoundError(f"'{data_dir}' 폴더에 공공데이터(통계) 파일이 없습니다. 먼저 다운로드해 주세요.")
    
    kor_df_list = []
    for f in file_list:
        # 여러 인코딩 방식을 순차적으로 시도하도록 예외 처리 추가
        try:
            df = pd.read_csv(f, encoding='cp949')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(f, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(f, encoding='euc-kr')
        kor_df_list.append(df)
        
    kor_df = pd.concat(kor_df_list, ignore_index=True)
    
    # 글로벌 데이터와 병합하기 위해 기상 상태를 영어 기준으로 통일
    kor_weather_to_eng = {'맑음': 'Clear', '비': 'Rain', '눈': 'Snow', '안개': 'Fog', '흐림': 'Cloudy'}
    kor_df['Weather'] = kor_df['기상상태'].map(kor_weather_to_eng).fillna('Other')
    
    kor_grouped = kor_df.groupby('Weather')[['사고건수', '사망자수']].sum().reset_index()
    
    # 사고 1건당 사망자 발생 비율(치사율) 계산
    kor_grouped['Fatality_Rate'] = np.where(
        kor_grouped['사고건수'] > 0,
        (kor_grouped['사망자수'] / kor_grouped['사고건수']) * 100, 
        0
    )
    base_fatality_mapping = dict(zip(kor_grouped['Weather'], kor_grouped['Fatality_Rate']))

    # 해외 사고 데이터 로드 및 병합
    pred_path = os.path.join(data_dir, 'dataset_traffic_accident_prediction1.csv')
    traffic_path = os.path.join(data_dir, 'traffic_accidents.csv')
    
    if not (os.path.exists(pred_path) and os.path.exists(traffic_path)):
        raise FileNotFoundError("🚨 해외 사고 데이터셋 CSV 파일이 누락되었습니다. dataset 폴더를 확인해 주세요.")
        
    # 두 데이터셋의 컬럼명이 달라서 결측치가 생기지 않도록 하나로 맵핑하여 통일
    df_pred = pd.read_csv(pred_path).rename(columns={'Accident_Severity': 'Severity'})
    df_traffic = pd.read_csv(traffic_path).rename(columns={
        'weather_condition': 'Weather',
        'roadway_surface_cond': 'Road_Condition',
        'crash_hour': 'Time_of_Day',
        'injuries_total': 'injuries_total',
        'injuries_fatal': 'injuries_fatal'
    })
    
    df_master = pd.concat([df_pred, df_traffic], ignore_index=True)
  # 텍스트 데이터 범주화
    # 해외 데이터셋은 날씨나 노면 상태가 자유 텍스트(예: Fog, foggy, Smoke 등)로 되어 있어서,
    # 정규표현식(str.contains)을 써서 우리 기준(Clear, Rain, Snow, Fog, Cloudy)으로 깔끔하게 통일함
    w_lower = df_master['Weather'].astype(str).str.lower()
    df_master['Weather'] = np.select(
        [w_lower.str.contains('fog|smoke', na=False),
         w_lower.str.contains('rain|storm', na=False),
         w_lower.str.contains('snow|sleet', na=False),
         w_lower.str.contains('cloud|overcast', na=False)], 
        ['Fog', 'Rain', 'Snow', 'Cloudy'], default='Clear'
    )
    
    # 노면 상태(Road_Condition)도 Icy, Wet, Dry 3가지로 압축
    s_lower = df_master['Road_Condition'].astype(str).str.lower()
    df_master['Road_Surface'] = np.select(
        [s_lower.str.contains('ice|icy|snow', na=False),
         s_lower.str.contains('wet|water', na=False)],
        ['Icy', 'Wet'], default='Dry'
    )
    
    # 시간대(Time_of_Day) 처리: 어떤 데이터는 숫자로(18시), 어떤 건 문자로(Night) 섞여 들어옴.
    # 숫자인 경우와 문자인 경우를 나눠서 새벽(Dawn), 야간(Night), 주간(Daylight)으로 맵핑
    t_str = df_master['Time_of_Day'].astype(str).str.lower()
    is_digit = t_str.str.isnumeric()
    t_num = pd.to_numeric(t_str, errors='coerce').fillna(-1)
    
    # 숫자형 시간대 분류 (6~17시: 주간, 18~23시: 야간, 0~5시: 새벽)
    cond_day_num = is_digit & (t_num >= 6) & (t_num <= 17)
    cond_night_num = is_digit & (t_num >= 18) & (t_num <= 23)
    cond_dawn_num = is_digit & (t_num >= 0) & (t_num <= 5)
    
    # 문자형 시간대 분류
    cond_dawn_str = ~is_digit & t_str.str.contains('morning|dawn', na=False)
    cond_night_str = ~is_digit & t_str.str.contains('night|evening', na=False)
    
    df_master['Time_of_Day'] = np.select(
        [cond_dawn_num | cond_dawn_str, cond_night_num | cond_night_str],
        ['Dawn', 'Night'], default='Daylight'
    )
    
    # 사상자 수 컬럼이 아예 없는 데이터셋과 병합될 때 KeyError가 나는 걸 방지하기 위한 방어 로직
    if 'injuries_total' not in df_master.columns: df_master['injuries_total'] = 0
    if 'injuries_fatal' not in df_master.columns: df_master['injuries_fatal'] = 0
    df_master['injuries_total'] = df_master['injuries_total'].fillna(0).astype(int)
    df_master['injuries_fatal'] = df_master['injuries_fatal'].fillna(0).astype(int)

    # 한국형 복합 위험도 가중치 산출 (핵심 튜닝 포인트)
    # 단순 기상 상태뿐만 아니라 '노면 상태'와 '시간대'를 곱해서 입체적인 위험도를 만듦
    base_weight = df_master['Weather'].map(base_fatality_mapping).fillna(1.0)
    
    # 결빙(Icy)은 1.5배, 젖은 노면(Wet)은 1.2배 가중치 (논문 및 도로교통공단 통계 참고)
    surface_mult = np.select([df_master['Road_Surface'] == 'Icy', df_master['Road_Surface'] == 'Wet'], [1.5, 1.2], default=1.0)
    
    # 시야 확보가 어려운 야간(Night)과 새벽(Dawn) 시간대는 사고 위험이 크므로 1.3배 가중치 부여
    time_mult = np.where(df_master['Time_of_Day'].isin(['Night', 'Dawn']), 1.3, 1.0)
    
    # 3가지 요소를 모두 곱해 최종 가중치 산출 (소수점 둘째 자리까지 반올림해서 모델 입력용으로 정리)
    df_master['korea_fatality_weight'] = np.round(base_weight * surface_mult * time_mult, 2)

    # 5. 권장 속도 역산 및 최종 위험도(Risk_Level) 라벨링
    # 원본 데이터에 '차량 주행 속도'가 없어서, 사고 심각도와 기상 악화 시 
    # 도로교통법상 감속 규정(20%~50%)을 역산하여 주행 속도를 추정하는 로직 구현
    np.random.seed(42) # 데이터가 틀어지지 않게 난수 고정
    
    # 기상 및 노면 상태에 따른 법정 권장 속도 도출 (안개/결빙은 50%, 비/눈은 20% 감속)
    cond_rec_50 = (df_master['Weather'] == 'Fog') | (df_master['Road_Surface'] == 'Icy')
    cond_rec_80 = df_master['Weather'].isin(['Rain', 'Snow']) | (df_master['Road_Surface'] == 'Wet')
    
    rec_speed = np.select([cond_rec_50, cond_rec_80], [1, 2], default=100)

    # 사고 심각도(사망/부상 여부)와 복합 가중치(2.5 이상)를 기준으로 과속 여부 추정
    is_fatal = (df_master['injuries_fatal'] > 0) | (df_master.get('Severity') == 'High')
    is_injured = (df_master['injuries_total'] > 0) | (df_master.get('Severity') == 'Moderate')
    is_high_weight = df_master['korea_fatality_weight'] > 2.5
    
    # 심각한 사고일수록 권장 속도를 크게 초과(과속)했을 것으로 가정하여 난수 범위 세팅
    low_bounds = np.select(
        [is_fatal, is_injured & is_high_weight, is_injured],
        [rec_speed + 30, rec_speed + 10, rec_speed - 10], default=30
    )
    high_bounds = np.select(
        [is_fatal, is_injured & is_high_weight, is_injured],
        [150, rec_speed + 31, rec_speed + 16], default=rec_speed + 6
    )
    
    # 난수 생성 시 low가 high보다 커지는 에러(ValueError) 방지용 안전장치
    high_bounds = np.maximum(low_bounds + 1, high_bounds)
    
    df_master['Speed'] = [np.random.randint(low, high) for low, high in zip(low_bounds, high_bounds)]

    # 모델이 학습할 정답지(Target) 생성: 위험 요소를 종합해 3단계 등급으로 맵핑
    conditions = [
        # [DANGER] 치명적 위험: 안개, 빙판길, 실제 대형 사고 발생이거나 
        # 야간에 비/눈이 겹쳐 시야 확보가 아예 안 되는 최악의 환경
        (df_master['Weather'] == 'Fog') | 
        (df_master['Road_Surface'] == 'Icy') | 
        (df_master['injuries_fatal'] > 0) | 
        (df_master.get('Severity') == 'High') |
        ((df_master['Time_of_Day'] == 'Night') & (df_master['Weather'].isin(['Rain', 'Snow']))), 
        
        # [WARNING] 주의 구간: 경상 사고, 비/눈/흐림, 젖은 노면, 어두운 시간대(야간/새벽)
        (df_master['injuries_total'] > 0) | 
        (df_master['Weather'].isin(['Rain', 'Snow', 'Cloudy'])) | 
        (df_master['Road_Surface'] == 'Wet') | 
        (df_master.get('Severity') == 'Moderate') |
        (df_master['Time_of_Day'].isin(['Night', 'Dawn'])) 
    ]
    choices = ['DANGER', 'WARNING']
    df_master['Risk_Level'] = np.select(conditions, choices, default='SAFE')

    # 하드웨어 연동을 위한 조도(lux) 센서 데이터 가상 생성
    # 실제 관제 시스템(STM32)의 BH1750 조도 센서값과 매핑시키기 위해 시간대와 기상을 엮어 생성함
    np.random.seed(42) 
    size = len(df_master)

    # 1차적으로 주야간 기준에 맞춰 현실적인 기본 조도(lux) 할당
    lux_cond = [df_master['Time_of_Day'] == 'Daylight', 
                df_master['Time_of_Day'] == 'Dawn', 
                df_master['Time_of_Day'] == 'Night']
    
    # 낮: 1000~5000 / 새벽 및 어스름: 50~400 / 밤: 0~50
    df_master['lux'] = np.select(lux_cond, 
                                 [np.random.uniform(1000, 5000, size), 
                                  np.random.uniform(50, 400, size), 
                                  np.random.uniform(0, 50, size)], 
                                 default=0)
    
    # 디테일 추가: 악천후(비, 눈, 안개) 시에는 먹구름이나 빛 산란으로 인해 조도가 떨어지는 현상(-60%) 반영
    df_master.loc[df_master['Weather'].isin(['Fog', 'Rain', 'Snow']), 'lux'] *= 0.4

    # 하드웨어 센서 해상도에 맞춰 소수점 1자리로 정리
    df_master['lux'] = np.round(df_master['lux'], 1)

    # 최종 데이터셋 정리 및 저장
    # 데이터 누수 우려로 사상자 수(injuries)를 버리고 실시간으로 수집 가능한 환경 및 주행 특성만 남김
    final_columns = ['Weather', 'Road_Surface', 'Time_of_Day', 'Speed', 'lux', 'korea_fatality_weight', 'Risk_Level']
    ai_master_dataset = df_master[final_columns].copy().dropna()
    
    output_file = os.path.join(data_dir, 'ai_master_dataset.csv')
    ai_master_dataset.to_csv(output_file, index=False)
    
    print(f"분석 및 전처리 완료, 마스터 데이터셋 저장됨: {output_file}")
    
    return ai_master_dataset

if __name__ == "__main__":
    master_df = create_master_dataset()
