import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import datetime

# -----------------------------------------------------
# 1. 데이터 로드 및 전처리
# -----------------------------------------------------
@st.cache_data(ttl=60)
def load_and_combine_data(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        all_data = [xls.parse(sheet_name) for sheet_name in xls.sheet_names]
        if not all_data: return pd.DataFrame()
        df = pd.concat(all_data, ignore_index=True)
        
        # 날짜 컬럼명 통일
        if '접수일시' in df.columns:
            df.rename(columns={'접수일시': '발생일'}, inplace=True)
        
        df['발생일'] = pd.to_datetime(df.get('발생일'), errors='coerce')
        df.dropna(subset=['발생일'], inplace=True)
        
        # 시간 추출
        if '발생시간' in df.columns:
            df['temp_time_str'] = df['발생시간'].astype(str)
            df['temp_datetime'] = pd.to_datetime(df['temp_time_str'], errors='coerce')
            df['시간'] = df['temp_datetime'].dt.hour
            df = df.dropna(subset=['시간'])
            df['시간'] = df['시간'].astype(int)
        else:
            df['시간'] = df['발생일'].dt.hour
        
        # 파생 변수
        df['월_표기'] = df['발생일'].dt.strftime('%m월')
        df['일_표기'] = df['발생일'].dt.strftime('%d일')
        df['요일_숫자'] = df['발생일'].dt.weekday 
        day_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
        df['요일_명'] = df['요일_숫자'].map(day_map)

        # 주간 라벨
        df['주_시작일'] = df['발생일'] - pd.to_timedelta((df['발생일'].dt.weekday + 1) % 7, unit='D')
        df['주_종료일'] = df['주_시작일'] + pd.to_timedelta(6, unit='D')
        df['주간_라벨'] = df['주_시작일'].dt.strftime('%m/%d') + "~" + df['주_종료일'].dt.strftime('%m/%d')
        
        return df
    except Exception as e:
        return pd.DataFrame()

FILE_PATH = 'kiosk_data.xlsx'
df = load_and_combine_data(FILE_PATH)

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
    st.stop()

# -----------------------------------------------------
# 2. UI 및 필터링
# -----------------------------------------------------
st.set_page_config(layout="wide", page_title="장애 발생 현황")
st.title("📊 키오스크 장애 발생 현황 대시보드")
st.markdown("---")

current_df = df.copy()

# 사이드바
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

# 데이터셋 분리
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
# KPI 지표 (수정됨: 최다 발생 유형 증감 계산 추가)
# -----------------------------------------------------
kpi1, kpi2, kpi3 = st.columns(3)

# 1. 비교 데이터(지난달 or 지난주) 준비
prev_period_df = pd.DataFrame() # 이전 기간 데이터 담을 변수
kpi_label_suffix = ""           # "(전월 대비)" 같은 텍스트

if selected_week != '전체':
    # 주간 선택 시: 이미 위에서 만든 comparison_df 사용
    if not comparison_df.empty:
        prev_period_df = comparison_df
        kpi_label_suffix = " (지난주 대비)"
elif selected_month != '전체':
    # 월간 선택 시: 이전 달 데이터 추출
    try:
        curr_idx = sorted_months.index(selected_month)
        if curr_idx > 0:
            prev_month_name = sorted_months[curr_idx - 1]
            # 전체 데이터에서 이전 달 필터링
            temp_prev = df[df['월_표기'] == prev_month_name]
            # 유형 필터가 걸려있다면 같이 적용
            if selected_type != '전체':
                temp_prev = temp_prev[temp_prev['장애유형'] == selected_type]
            prev_period_df = temp_prev
            kpi_label_suffix = " (전월 대비)"
    except:
        pass

# 2. KPI 1: 총 발생 건수
total_count = len(detail_df)
total_delta = None

if not prev_period_df.empty:
    diff_total = total_count - len(prev_period_df)
    total_delta = f"{diff_total:+}건" # 부호(+/-) 자동 붙임

with kpi1:
    st.metric("총 발생 건수", f"{total_count:,}건", total_delta, delta_color="inverse")
    if kpi_label_suffix and total_delta:
        st.caption(kpi_label_suffix)

# 3. KPI 2: 일평균 발생
if not detail_df.empty:
    day_count = detail_df['발생일'].nunique()
    avg = total_count / day_count if day_count > 0 else 0
    with kpi2: st.metric("일평균 발생", f"{avg:.1f}건")
else:
    with kpi2: st.metric("일평균 발생", "0건")

# 4. KPI 3: 최다 발생 유형 (증감 로직 적용)
if not detail_df.empty and '장애유형' in detail_df.columns:
    # 현재 가장 많이 발생한 유형 찾기
    top_series = detail_df['장애유형'].value_counts()
    top_type_name = top_series.idxmax() # 유형 이름 (예: 로그인 실패)
    current_type_count = top_series.max() # 현재 건수 (예: 15건)
    
    # 이전 기간(전주/전월)에서 해당 유형의 건수 찾기
    type_delta = None
    if not prev_period_df.empty:
        # 이전 데이터에서 동일한 유형만 필터링해서 개수 셈
        prev_type_count = len(prev_period_df[prev_period_df['장애유형'] == top_type_name])
        diff_type = current_type_count - prev_type_count
        type_delta = f"{diff_type:+}건" # 예: +3건, -2건
    
    with kpi3:
        # 메인 값: 유형 이름 + (현재 건수)
        # 델타 값: 증감량
        st.metric("최다 발생 유형", f"{top_type_name} ({current_type_count}건)", type_delta, delta_color="inverse")
else:
    with kpi3: st.metric("최다 발생 유형", "-")

st.markdown("---")

# -----------------------------------------------------
# 3. 시각화 영역
# -----------------------------------------------------

# [1열] 월간/주간 추이
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
    
    # [수정] key 추가
    st.plotly_chart(fig_m, use_container_width=True, key="chart_monthly_trend")

with col2:
    if selected_week == '전체':
        st.subheader(f"2️⃣ 주간 장애 발생 추이 ({selected_month})")
        w_stats = current_df.groupby(['주_시작일', '주간_라벨']).size().reset_index(name='건수').sort_values('주_시작일')
        fig_w = px.line(w_stats, x='주간_라벨', y='건수', markers=True, text='건수')
        fig_w.update_traces(textposition="top center")
        fig_w.update_layout(xaxis_tickangle=-45, margin=dict(t=20, b=20, l=20, r=20))
        
        # [수정] key 추가
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
        
        # [수정] key 추가
        st.plotly_chart(fig_wow, use_container_width=True, key="chart_daily_comparison")

st.markdown("---")

# [2열] 요일별 / 시간대별
col3, col4 = st.columns(2)

with col3:
    st.subheader("3️⃣ 요일별 발생 패턴")
    if not detail_df.empty:
        d_cnt = detail_df.groupby(['요일_명','요일_숫자']).size().reset_index(name='건수').sort_values('요일_숫자')
        fig_d = px.bar(d_cnt, x='요일_명', y='건수', text='건수')
        fig_d.update_traces(marker_color='#00CC96')
        fig_d.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        
        # [수정] key 추가
        st.plotly_chart(fig_d, use_container_width=True, key="chart_day_pattern")
    else: st.info("데이터 없음")

with col4:
    st.subheader("4️⃣ 시간대별 집중 발생 (Peak Time)")
    if not detail_df.empty:
        h_cnt = detail_df['시간'].value_counts().reindex(range(24), fill_value=0).sort_index()
        h_df = pd.DataFrame({'시간': h_cnt.index, '건수': h_cnt.values})
        h_df['라벨'] = h_df['시간'].apply(lambda x: f"{x:02d}시")
        fig_h = px.bar(h_df, x='라벨', y='건수', text='건수', color='건수', color_continuous_scale='Reds')
        fig_h.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        
        # [수정] key 추가
        st.plotly_chart(fig_h, use_container_width=True, key="chart_time_pattern")
    else: st.info("데이터 없음")

st.markdown("---")

# [3열] 기기별 Top 3
st.subheader("5️⃣ 장애 다발 기기 Top 3")
if not detail_df.empty and '기기명' in detail_df.columns:
    top_devices_list = detail_df['기기명'].value_counts().head(3).index.tolist()
    if top_devices_list:
        top3_df = detail_df[detail_df['기기명'].isin(top_devices_list)]
        chart_data = top3_df.groupby(['기기명', '장애유형']).size().reset_index(name='건수')
        fig_top3 = px.bar(
            chart_data, y='기기명', x='건수', color='장애유형', 
            text='건수', orientation='h', 
            category_orders={"기기명": top_devices_list}
        )
        fig_top3.update_layout(
            yaxis={'categoryorder':'total ascending'}, 
            xaxis_title="발생 건수", yaxis_title="기기명",
            height=300, margin=dict(t=20, b=20, l=20, r=20)
        )
        
        # [수정] key 추가
        st.plotly_chart(fig_top3, use_container_width=True, key="chart_device_top3")
    else: st.info("표시할 데이터가 없습니다.")

st.markdown("---")

# -----------------------------------------------------
# [4열] 6. 장애 유형 상세 비교 (하이라이트 기능 적용)
# -----------------------------------------------------
st.header("6️⃣ 장애 유형 상세 비교 분석")

# 선택된 유형 이름을 저장할 변수
selected_type_name = None

# [1단계] 데이터 집계 및 표 그리기 (먼저 해야 선택된 값을 알 수 있음)
if not prev_period_df.empty and not detail_df.empty:
    # 데이터 병합 및 집계
    curr_s = detail_df['장애유형'].value_counts()
    prev_s = prev_period_df['장애유형'].value_counts()
    
    merged = pd.concat([prev_s, curr_s], axis=1).fillna(0)
    merged.columns = ['이전', '현재']
    merged['증감'] = merged['현재'] - merged['이전']
    merged = merged.sort_values('현재', ascending=False)
    
    # [수정] 컬럼명을 '장애유형'으로 명확하게 지정 (KeyError 방지)
    display_df = merged.reset_index().rename(columns={'index':'장애유형'})
    display_df['이전'] = display_df['이전'].astype(int)
    display_df['현재'] = display_df['현재'].astype(int)
    display_df['증감'] = display_df['증감'].apply(lambda x: f"+{int(x)}" if x > 0 else f"{int(x)}")

    # 레이아웃 설정
    c_prev, c_center, c_curr = st.columns([3, 2, 3])
    legend_setting = dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)

    # 중앙: 증감 내역 표
    with c_center:
        st.subheader("📊 증감 내역")
        st.caption("👇 **행을 클릭**하면 차트가 강조됩니다.")
        
        selection = st.dataframe(
            display_df, 
            hide_index=True, 
            use_container_width=True,
            on_select="rerun",           
            selection_mode="single-row", 
            column_config={
                "장애유형": st.column_config.TextColumn("장애유형", width="small"),
                "이전": st.column_config.NumberColumn("이전", format="%d"),
                "현재": st.column_config.NumberColumn("현재", format="%d"),
                "증감": st.column_config.TextColumn("증감")
            }
        )
        
        # [수정] 선택된 행의 '장애유형' 가져오기
        if selection and selection.selection["rows"]:
            idx = selection.selection["rows"][0]
            selected_type_name = display_df.iloc[idx]['장애유형']

    # 왼쪽: 이전 기간 파이차트 (하이라이트 적용)
    with c_prev:
        label_prev = kpi_label_suffix.replace('대비', '').strip('() ') or "이전 기간"
        st.subheader(f"📉 {label_prev}")
        pie_data_prev = prev_period_df.groupby('장애유형').size().reset_index(name='건수')
        
        # [핵심] 선택된 유형이면 0.2만큼 튀어나오게 설정 (Pull)
        pull_values = [0.2 if x == selected_type_name else 0 for x in pie_data_prev['장애유형']]
        
        fig_p = px.pie(pie_data_prev, names='장애유형', values='건수', hole=0.4)
        fig_p.update_traces(pull=pull_values) # 하이라이트 적용
        fig_p.update_layout(showlegend=True, legend=legend_setting, margin=dict(t=0, b=50, l=0, r=0))
        st.plotly_chart(fig_p, use_container_width=True, key="chart_pie_prev")

    # 오른쪽: 현재 기간 파이차트 (하이라이트 적용)
    with c_curr:
        st.subheader("📈 현재 기간")
        pie_data_curr = detail_df.groupby('장애유형').size().reset_index(name='건수')
        
        # [핵심] 선택된 유형이면 0.2만큼 튀어나오게 설정 (Pull)
        pull_values = [0.2 if x == selected_type_name else 0 for x in pie_data_curr['장애유형']]
        
        fig_c = px.pie(pie_data_curr, names='장애유형', values='건수', hole=0.4)
        fig_c.update_traces(pull=pull_values) # 하이라이트 적용
        fig_c.update_layout(showlegend=True, legend=legend_setting, margin=dict(t=0, b=50, l=0, r=0))
        st.plotly_chart(fig_c, use_container_width=True, key="chart_pie_curr")

else:
    # 단독 모드 (비교 데이터 없음)
    st.info("비교할 과거 데이터가 없어 현재 데이터만 표시합니다.")
    if not detail_df.empty:
        col1, col2 = st.columns([1, 2])
        
        # 데이터 준비
        display_df = detail_df['장애유형'].value_counts().reset_index().rename(columns={'index':'장애유형', 'count':'건수'})
        if '장애유형' not in display_df.columns: display_df.rename(columns={'index':'장애유형'}, inplace=True) # 안전장치

        with col1:
             st.subheader("📊 유형 선택")
             selection = st.dataframe(display_df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
             if selection and selection.selection["rows"]:
                idx = selection.selection["rows"][0]
                selected_type_name = display_df.iloc[idx]['장애유형']
                
        with col2:
            pie_data_curr = detail_df.groupby('장애유형').size().reset_index(name='건수')
            pull_values = [0.2 if x == selected_type_name else 0 for x in pie_data_curr['장애유형']]
            
            fig_t = px.pie(pie_data_curr, names='장애유형', values='건수', hole=0.3)
            fig_t.update_traces(pull=pull_values)
            st.plotly_chart(fig_t, use_container_width=True, key="chart_pie_fallback")

# -----------------------------------------------------
# [7번] 상세 데이터 원본 조회
# -----------------------------------------------------
st.markdown("---")

# 사용자 지정 컬럼 리스트
target_cols = ['발생일', '기기명', '장애유형', '장애알람', '조치 내용', '출동', '처리자']

if selected_type_name:
    st.header(f"7️⃣ 상세 데이터 원본 조회: :red[{selected_type_name}]")
    
    # 탭 생성 (현재 / 이전)
    tab1, tab2 = st.tabs(["📈 현재 기간 데이터", "📉 이전 기간 데이터"])
    
    # [탭1] 현재 데이터
    with tab1:
        curr_filtered = detail_df[detail_df['장애유형'] == selected_type_name].copy()
        if not curr_filtered.empty:
            valid_cols = [c for c in target_cols if c in curr_filtered.columns]
            st.dataframe(curr_filtered[valid_cols].sort_values('발생일', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.warning("데이터가 없습니다.")

    # [탭2] 이전 데이터
    with tab2:
        if not prev_period_df.empty:
            prev_filtered = prev_period_df[prev_period_df['장애유형'] == selected_type_name].copy()
            if not prev_filtered.empty:
                valid_cols = [c for c in target_cols if c in prev_filtered.columns]
                st.dataframe(prev_filtered[valid_cols].sort_values('발생일', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.warning("데이터가 없습니다.")
        else:
            st.info("비교할 이전 기간 데이터가 없습니다.")

else:
    # 아무것도 선택 안 했을 때 -> 전체 리스트 (현재 기간)
    st.header("7️⃣ 상세 데이터 원본 조회 (전체)")
    
    if not detail_df.empty:
        valid_cols = [c for c in target_cols if c in detail_df.columns]
        if valid_cols:
            st.dataframe(detail_df[valid_cols].sort_values('발생일', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.dataframe(detail_df.sort_values('발생일', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("조회된 데이터가 없습니다.")

st.markdown("---")