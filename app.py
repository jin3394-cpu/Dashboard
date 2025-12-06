import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import datetime
import os

# -----------------------------------------------------
# [설정] 장애 유형별 고정 색상 지도 (Color Map)
# -----------------------------------------------------
TYPE_COLOR_MAP = {
    "지폐 미방출": "#C0392B",
    "카드 미방출": "#E74C3C",
    "결제 관련":   "#D35400",
    "카드 부족": "#F39C12",

    "지폐방출기 오류" : "#2C3E50",
    "지폐인식기 오류" : "#34495E",
    "카드리더기 오류" : "#2980B9",
    "여권인식기 오류" : "#4169E1",
    "영수증프린터 오류" : "#3498DB",

    "거래 중 통신장애" : "#27AE60",
    "ROUTER" :  "#2ECC71",
    "유심카드" :  "#16A085",

    "PC" : "#8E44AD",
    "프로그램 오류" : "#9B59B6",
    "재실행"   : "#F1C40F",
    "전기 이슈" : "#FFD700",

    "터치스크린 고장" : "#1ABC9C",
    "USB 카메라 오류" : "#00CED1",
    "모듈 관련": "#7F8C8D",
    "도어센서 오류": "#BDC3C7",
    "셔터": "#95A5A6",
    "기타" : "#ECF0F1",
}



# -----------------------------------------------------
# 1. 데이터 로드 및 전처리
# -----------------------------------------------------
@st.cache_data(ttl=60)
def load_and_combine_data(file_path):
    try:
        if not os.path.isabs(file_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, file_path)

        xls = pd.ExcelFile(file_path, engine='openpyxl')
        all_data = [xls.parse(sheet_name) for sheet_name in xls.sheet_names]
        if not all_data: return pd.DataFrame()
        df = pd.concat(all_data, ignore_index=True)
        
        if '접수일시' in df.columns:
            df.rename(columns={'접수일시': '발생일'}, inplace=True)
        
        df['발생일'] = pd.to_datetime(df.get('발생일'), errors='coerce')
        df.dropna(subset=['발생일'], inplace=True)
        
        if '발생시간' in df.columns:
            df['temp_time_str'] = df['발생시간'].astype(str)
            df['temp_datetime'] = pd.to_datetime(df['temp_time_str'], errors='coerce')
            df['시간'] = df['temp_datetime'].dt.hour
            df = df.dropna(subset=['시간'])
            df['시간'] = df['시간'].astype(int)
        else:
            df['시간'] = df['발생일'].dt.hour
        
        df['월_표기'] = df['발생일'].dt.strftime('%m월')
        df['일_표기'] = df['발생일'].dt.strftime('%d일')
        df['요일_숫자'] = df['발생일'].dt.weekday 
        day_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
        df['요일_명'] = df['요일_숫자'].map(day_map)

        df['주_시작일'] = df['발생일'] - pd.to_timedelta((df['발생일'].dt.weekday + 1) % 7, unit='D')
        df['주_종료일'] = df['주_시작일'] + pd.to_timedelta(6, unit='D')
        df['주간_라벨'] = df['주_시작일'].dt.strftime('%m/%d') + "~" + df['주_종료일'].dt.strftime('%m/%d')
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()

FILE_PATH = 'kiosk_data.xlsx'
df = load_and_combine_data(FILE_PATH)

if df.empty:
    st.error("데이터를 불러올 수 없습니다. 엑셀 파일 경로와 형식을 확인해주세요.")
    st.stop()

# -----------------------------------------------------
# 2. UI 및 필터링
# -----------------------------------------------------
st.set_page_config(layout="wide", page_title="장애 발생 현황")
st.title("📊 키오스크 장애 발생 현황 대시보드")
st.markdown("---")

current_df = df.copy()

st.sidebar.header("필터링 옵션")

# 1. 월별
if '월_표기' in df.columns:
    sorted_months = sorted(df['월_표기'].unique().tolist(), key=lambda x: int(x.replace('월','')))
    unique_months = ['전체'] + sorted_months
    selected_month = st.sidebar.selectbox("📅 1. 월별 선택:", unique_months)
    if selected_month != '전체':
        current_df = current_df[current_df['월_표기'] == selected_month]
else:
    selected_month = '전체'

# 2. 주간
selected_week = '전체'
prev_week_label = None

if selected_month != '전체':
    week_group = current_df[['주간_라벨', '주_시작일']].drop_duplicates().sort_values('주_시작일')
    week_list = week_group['주간_라벨'].tolist()
    unique_weeks = ['전체'] + week_list
    selected_week = st.sidebar.selectbox("📅 2. 주간 선택:", unique_weeks)
    
    if selected_week != '전체':
        try:
            curr_idx = week_list.index(selected_week)
            if curr_idx > 0: prev_week_label = week_list[curr_idx - 1]
        except: pass
else:
    st.sidebar.info("월을 선택하면 주간 필터가 나타납니다.")

# 3. 유형
if '장애유형' in df.columns:
    unique_types = ['전체'] + sorted(df['장애유형'].unique().tolist())
    selected_type = st.sidebar.selectbox("🛠️ 3. 장애 유형 선택:", unique_types)
    if selected_type != '전체':
        current_df = current_df[current_df['장애유형'] == selected_type]

detail_df = current_df.copy()
if selected_week != '전체':
    detail_df = detail_df[detail_df['주간_라벨'] == selected_week]

comparison_df = pd.DataFrame()
if selected_week != '전체' and prev_week_label:
    comparison_df = df[(df['주간_라벨'] == prev_week_label)]
    if selected_type != '전체':
        comparison_df = comparison_df[comparison_df['장애유형'] == selected_type]

st.sidebar.markdown(f"**선택된 데이터:** {len(detail_df):,}건")


# -----------------------------------------------------
# KPI 지표
# -----------------------------------------------------
kpi1, kpi2, kpi3 = st.columns(3)

prev_period_df = pd.DataFrame() 
kpi_label_suffix = ""           

if selected_week != '전체':
    if not comparison_df.empty:
        prev_period_df = comparison_df
        kpi_label_suffix = " (지난주 대비)"
elif selected_month != '전체':
    try:
        curr_idx = sorted_months.index(selected_month)
        if curr_idx > 0:
            prev_month_name = sorted_months[curr_idx - 1]
            temp_prev = df[df['월_표기'] == prev_month_name]
            if selected_type != '전체':
                temp_prev = temp_prev[temp_prev['장애유형'] == selected_type]
            prev_period_df = temp_prev
            kpi_label_suffix = " (전월 대비)"
    except: pass

total_count = len(detail_df)
total_delta = None

if not prev_period_df.empty:
    diff_total = total_count - len(prev_period_df)
    total_delta = f"{diff_total:+}건" 

with kpi1:
    st.metric("총 발생 건수", f"{total_count:,}건", total_delta, delta_color="inverse")
    if kpi_label_suffix and total_delta:
        st.caption(kpi_label_suffix)

if not detail_df.empty:
    day_count = detail_df['발생일'].nunique()
    avg = total_count / day_count if day_count > 0 else 0
    with kpi2: st.metric("일평균 발생", f"{avg:.1f}건")
else:
    with kpi2: st.metric("일평균 발생", "0건")

if not detail_df.empty and '장애유형' in detail_df.columns:
    top_series = detail_df['장애유형'].value_counts()
    top_type_name = top_series.idxmax()
    current_type_count = top_series.max()
    
    type_delta = None
    if not prev_period_df.empty:
        prev_type_count = len(prev_period_df[prev_period_df['장애유형'] == top_type_name])
        diff_type = current_type_count - prev_type_count
        type_delta = f"{diff_type:+}건" 
    
    with kpi3:
        st.metric("최다 발생 유형", f"{top_type_name} ({current_type_count}건)", type_delta, delta_color="inverse")
else:
    with kpi3: st.metric("최다 발생 유형", "-")

st.markdown("---")

# -----------------------------------------------------
# 3. 시각화 영역
# -----------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ 월간 장애 발생 추이")
    base_df = df.copy()
    if selected_type != '전체': base_df = base_df[base_df['장애유형'] == selected_type]
    m_stats = base_df.groupby('월_표기').size().reset_index(name='건수')
    m_stats['sort'] = m_stats['월_표기'].str.replace('월','').astype(int)
    m_stats = m_stats.sort_values('sort')
    colors = ['#EF553B' if m == selected_month else '#ABACF7' for m in m_stats['월_표기']]
    fig_m = go.Figure(data=[go.Bar(x=m_stats['월_표기'], y=m_stats['건수'], marker_color=colors, text=m_stats['건수'])])
    fig_m.update_traces(textposition='outside')
    fig_m.update_layout(xaxis_title="월", yaxis_title="건수", margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_m, use_container_width=True, key="chart_monthly_trend")

with col2:
    if selected_week == '전체':
        st.subheader(f"2️⃣ 주간 장애 발생 추이 ({selected_month})")
        w_stats = current_df.groupby(['주_시작일', '주간_라벨']).size().reset_index(name='건수').sort_values('주_시작일')
        fig_w = px.line(w_stats, x='주간_라벨', y='건수', markers=True, text='건수')
        fig_w.update_traces(textposition="top center")
        fig_w.update_layout(xaxis_tickangle=-45, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_w, use_container_width=True, key="chart_weekly_trend")
    else:
        st.subheader(f"2️⃣ 일별 발생 패턴 (이번 주 vs 지난주)")
        curr_daily = detail_df.groupby('요일_숫자').size().reindex(range(7), fill_value=0)
        prev_daily = comparison_df.groupby('요일_숫자').size().reindex(range(7), fill_value=0) if not comparison_df.empty else pd.Series([0]*7)
        days = ['월', '화', '수', '목', '금', '토', '일']
        fig_wow = go.Figure()
        fig_wow.add_trace(go.Scatter(x=days, y=prev_daily.values, name=f"지난주 ({prev_week_label})", line=dict(color='gray', width=2, dash='dot')))
        fig_wow.add_trace(go.Scatter(x=days, y=curr_daily.values, name=f"선택 주 ({selected_week})", line=dict(color='#EF553B', width=4), mode='lines+markers+text', text=curr_daily.values, textposition='top center'))
        fig_wow.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_wow, use_container_width=True, key="chart_daily_comparison")

st.markdown("---")

# ... (이전 코드 생략)

# -----------------------------------------------------
# [2열] 요일별 / 시간대별 (전체 패턴 vs 선택 패턴 비교 적용)
# -----------------------------------------------------
# ... (이전 코드 생략)

# -----------------------------------------------------
# [2열] 요일별 / 시간대별 (비율 기반 패턴 비교)
# -----------------------------------------------------
col3, col4 = st.columns(2)

with col3:
    st.subheader("3️⃣ 요일별 발생 패턴 (분포 비교)")
    if not detail_df.empty:
        # 1. [선택 기간] 데이터 집계 및 비율 계산
        d_cnt = detail_df.groupby(['요일_명','요일_숫자']).size().reset_index(name='건수').sort_values('요일_숫자')
        current_total = d_cnt['건수'].sum()
        d_cnt['비율'] = (d_cnt['건수'] / current_total) * 100 # % 계산

        # 2. [전체 누적] 데이터 집계 및 비율 계산
        total_d_cnt = df.groupby(['요일_명','요일_숫자']).size().reset_index(name='전체건수').sort_values('요일_숫자')
        all_total = total_d_cnt['전체건수'].sum()
        total_d_cnt['전체비율'] = (total_d_cnt['전체건수'] / all_total) * 100 # % 계산

        # 3. 시각화 (Y축을 %로 통일)
        fig_d = go.Figure()

        # (1) 배경: 전체 평균 분포 (회색 선/영역)
        fig_d.add_trace(go.Scatter(
            x=total_d_cnt['요일_명'], 
            y=total_d_cnt['전체비율'],
            name='평소 패턴(%)',
            mode='lines+markers',
            line=dict(color='rgba(180, 180, 180, 0.5)', width=2, dash='dot'),
            hovertemplate='평소 비중: %{y:.1f}%<br>(누적 %{text}건)',
            text=total_d_cnt['전체건수'] # 호버용 데이터
        ))

        # (2) 전경: 선택 기간 분포 (컬러 막대)
        fig_d.add_trace(go.Bar(
            x=d_cnt['요일_명'], 
            y=d_cnt['비율'],
            name='선택 기간(%)',
            marker_color='#00CC96',
            text=d_cnt['건수'], # 막대 위에는 '실제 건수' 표시
            texttemplate='%{text}건', # 텍스트 포맷
            textposition='auto',
            hovertemplate='이번 비중: %{y:.1f}%<br>(실제 %{text}건)'
        ))

        fig_d.update_layout(
            yaxis=dict(title="발생 비중 (%)", ticksuffix="%"), # Y축은 퍼센트
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=40, b=20, l=20, r=20),
            hovermode="x unified" # 마우스 올리면 둘 다 비교
        )
        
        st.plotly_chart(fig_d, use_container_width=True, key="chart_day_pattern")
    else: st.info("데이터 없음")

with col4:
    st.subheader("4️⃣ 시간대별 집중 발생 (Peak Time)")
    if not detail_df.empty:
        # 1. [선택 기간] 데이터
        h_cnt = detail_df['시간'].value_counts().reindex(range(24), fill_value=0).sort_index()
        current_total_h = h_cnt.sum()
        h_pct = (h_cnt / current_total_h * 100).fillna(0) # % 계산

        # 2. [전체 누적] 데이터
        total_h_cnt = df['시간'].value_counts().reindex(range(24), fill_value=0).sort_index()
        all_total_h = total_h_cnt.sum()
        total_h_pct = (total_h_cnt / all_total_h * 100).fillna(0) # % 계산
        
        hours = [f"{i:02d}시" for i in range(24)]

        # 3. 시각화
        fig_h = go.Figure()

        # (1) 배경: 전체 평균 분포
        fig_h.add_trace(go.Scatter(
            x=hours, 
            y=total_h_pct.values,
            name='평소 패턴(%)',
            mode='lines',
            fill='tozeroy',
            fillcolor='rgba(200, 200, 200, 0.1)',
            line=dict(color='rgba(180, 180, 180, 0.5)', width=1),
            hovertemplate='평소 비중: %{y:.1f}%<br>(누적 %{text}건)',
            text=total_h_cnt.values
        ))

        # (2) 전경: 선택 기간 분포
        fig_h.add_trace(go.Bar(
            x=hours, 
            y=h_pct.values,
            name='선택 기간(%)',
            marker_color='#EF553B',
            text=h_cnt.values, # 막대 위에는 '실제 건수'
            texttemplate='%{text}', # 0건일 때 등 고려하여 포맷 단순화
            textposition='outside', # 막대 밖으로 표시
            hovertemplate='이번 비중: %{y:.1f}%<br>(실제 %{text}건)'
        ))

        fig_h.update_layout(
            yaxis=dict(title="발생 비중 (%)", ticksuffix="%"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=40, b=20, l=20, r=20),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_h, use_container_width=True, key="chart_time_pattern")
    else: st.info("데이터 없음")

# ... (이후 코드 유지)

st.markdown("---")

# 5. 기기별 Top 3 (여기도 색상 맵 적용)
st.subheader("5️⃣ 장애 다발 기기 Top 3")
if not detail_df.empty and '기기명' in detail_df.columns:
    top_devices_list = detail_df['기기명'].value_counts().head(3).index.tolist()
    if top_devices_list:
        top3_df = detail_df[detail_df['기기명'].isin(top_devices_list)]
        chart_data = top3_df.groupby(['기기명', '장애유형']).size().reset_index(name='건수')
        
        # [수정] color='장애유형' 및 color_discrete_map 적용
        fig_top3 = px.bar(
            chart_data, y='기기명', x='건수', 
            color='장애유형',             # 색상 기준
            color_discrete_map=TYPE_COLOR_MAP, # 고정 색상표 적용
            text='건수', orientation='h', 
            category_orders={"기기명": top_devices_list}
        )
        fig_top3.update_layout(
            yaxis={'categoryorder':'total ascending'}, 
            xaxis_title="발생 건수", yaxis_title="기기명",
            height=300, margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_top3, use_container_width=True, key="chart_device_top3")
    else: st.info("표시할 데이터가 없습니다.")

st.markdown("---")

# -----------------------------------------------------
# 6. 장애 유형 상세 비교 분석 (핵심: 고정 색상 적용)
# -----------------------------------------------------

st.header("6️⃣ 장애 유형 상세 비교 분석")

if not prev_period_df.empty and not detail_df.empty:
    c_prev, c_center, c_curr = st.columns([3, 2, 3])
    
    # 공통 범례 설정 (차트 하단 가로 배치)
    legend_setting = dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)

    # 1. 왼쪽: 이전 차트
    with c_prev:
        label_prev = kpi_label_suffix.replace('대비', '').strip('() ') or "이전 기간"
        st.subheader(f"📉 {label_prev}")
        prev_cnt = prev_period_df.groupby('장애유형').size().reset_index(name='건수')
        
        fig_p = px.pie(
            prev_cnt, 
            names='장애유형', 
            values='건수', 
            hole=0.4,
            color='장애유형',                  # 색상 기준 컬럼
            color_discrete_map=TYPE_COLOR_MAP  # 커스텀 색상 맵 적용
        )
        
        # 텍스트 포맷 설정: 이름 <br> 건수 / 퍼센트
        fig_p.update_traces(
            texttemplate='%{label}<br>%{value}건 / %{percent}',
            textposition='inside'
        )
        
        fig_p.update_layout(
            showlegend=True, 
            legend=legend_setting,
            margin=dict(t=0, b=50, l=0, r=0)
        )
        st.plotly_chart(fig_p, use_container_width=True, key="chart_pie_prev")

    # 2. 중앙: 증감 내역
    with c_center:
        st.subheader("📊 증감 내역")
        curr_s = detail_df['장애유형'].value_counts()
        prev_s = prev_period_df['장애유형'].value_counts()
        
        merged = pd.concat([prev_s, curr_s], axis=1).fillna(0)
        merged.columns = ['이전', '현재']
        merged['증감'] = merged['현재'] - merged['이전']
        merged = merged.sort_values('현재', ascending=False)
        
        display_df = merged.reset_index().rename(columns={'index':'유형'})
        display_df['이전'] = display_df['이전'].astype(int)
        display_df['현재'] = display_df['현재'].astype(int)
        display_df['증감'] = display_df['증감'].apply(lambda x: f"+{int(x)}" if x > 0 else f"{int(x)}")

        st.dataframe(
            display_df, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "유형": st.column_config.TextColumn("유형", width="medium"),
                "이전": st.column_config.NumberColumn("이전", format="%d건"),
                "현재": st.column_config.NumberColumn("현재", format="%d건"),
                "증감": st.column_config.TextColumn("증감 (Diff)")
            }
        )

    # 3. 오른쪽: 현재 차트
    with c_curr:
        st.subheader("📈 현재 기간")
        curr_cnt = detail_df.groupby('장애유형').size().reset_index(name='건수')
        
        fig_c = px.pie(
            curr_cnt, 
            names='장애유형', 
            values='건수', 
            hole=0.4,
            color='장애유형',                  # 색상 기준 컬럼
            color_discrete_map=TYPE_COLOR_MAP  # 커스텀 색상 맵 적용
        )
        
        # 텍스트 포맷 설정
        fig_c.update_traces(
            texttemplate='%{label}<br>%{value}건 / %{percent}',
            textposition='inside'
        )
        
        fig_c.update_layout(
            showlegend=True, 
            legend=legend_setting,
            margin=dict(t=0, b=50, l=0, r=0)
        )
        st.plotly_chart(fig_c, use_container_width=True, key="chart_pie_curr")

else:
    st.info("비교할 과거 데이터가 없어 현재 데이터만 표시합니다.")
    if not detail_df.empty:
        t_cnt = detail_df.groupby('장애유형').size().reset_index(name='건수')
        
        fig_t = px.pie(
            t_cnt, 
            names='장애유형', 
            values='건수', 
            hole=0.3,
            color='장애유형',                  # 색상 기준 컬럼
            color_discrete_map=TYPE_COLOR_MAP  # 커스텀 색상 맵 적용
        )
        
        # 텍스트 포맷 설정
        fig_t.update_traces(
            texttemplate='%{label}<br>%{value}건 / %{percent}',
            textposition='inside'
        )
        
        st.plotly_chart(fig_t, use_container_width=True, key="chart_pie_fallback")

st.markdown("---")









