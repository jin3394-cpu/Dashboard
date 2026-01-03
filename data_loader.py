import streamlit as st
import pandas as pd
import datetime

# -----------------------------------------------------
# 데이터 로드 및 전처리 함수
# -----------------------------------------------------
@st.cache_data(ttl=60)
def load_and_combine_data(file_paths): 
    """
    여러 개의 엑셀 파일 경로(List)를 받아 하나로 통합하고 전처리하는 함수
    """
    try:
        all_df_list = []
        
        for file_path in file_paths:
            try:
                xls = pd.ExcelFile(file_path)
                sheet_data = [xls.parse(sheet_name) for sheet_name in xls.sheet_names]
                if sheet_data:
                    all_df_list.extend(sheet_data)
            except Exception as e:
                print(f"파일 로드 실패 ({file_path}): {e}")
                continue

        if not all_df_list: return pd.DataFrame()
        
        # 1. 일단 합치기
        df = pd.concat(all_df_list, ignore_index=True)
        
        # 2. 전처리 먼저 수행 (날짜 표준화)
        if '접수일시' in df.columns:
            df.rename(columns={'접수일시': '발생일'}, inplace=True)
        
        df['발생일'] = pd.to_datetime(df.get('발생일'), errors='coerce')
        df.dropna(subset=['발생일'], inplace=True)
        
        # 시간 추출
        if '발생시간' in df.columns:
            df['temp_time_str'] = df['발생시간'].astype(str)
            df['temp_datetime'] = pd.to_datetime(df['temp_time_str'], errors='coerce')
            df['시간'] = df['temp_datetime'].dt.hour
            # 시간 추출 후 임시 컬럼 삭제 (깔끔하게)
            df.drop(columns=['temp_time_str', 'temp_datetime'], inplace=True, errors='ignore') 
            df = df.dropna(subset=['시간'])
            df['시간'] = df['시간'].astype(int)
        else:
            df['시간'] = df['발생일'].dt.hour
        
        # 월 표기 및 기타 파생 변수
        df['월_표기'] = df['발생일'].dt.strftime('%Y년 %m월')
        df['일_표기'] = df['발생일'].dt.strftime('%d일')
        df['요일_숫자'] = df['발생일'].dt.weekday 
        day_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
        df['요일_명'] = df['요일_숫자'].map(day_map)

        df['주_시작일'] = df['발생일'] - pd.to_timedelta((df['발생일'].dt.weekday + 1) % 7, unit='D')
        df['주_종료일'] = df['주_시작일'] + pd.to_timedelta(6, unit='D')
        df['주간_라벨'] = df['주_시작일'].dt.strftime('%m/%d') + "~" + df['주_종료일'].dt.strftime('%m/%d')

        # -------------------------------------------------------
        # [수정] 중복 제거 위치 변경 (맨 마지막)
        # 모든 형식이 통일된 상태에서 중복을 검사해야 정확합니다.
        # -------------------------------------------------------
        df.drop_duplicates(inplace=True)
        
        return df

    except Exception as e:
        return pd.DataFrame()