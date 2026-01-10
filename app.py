import streamlit as st
import pandas as pd
import data_loader as dl
import charts as ch
import insights as ins  # [추가] 새로 만든 모듈 임포트

# -----------------------------------------------------
# [신규] 커스텀 디자인 함수 (흰색 텍스트 박스)
# -----------------------------------------------------
def ui_info(text):
    # 배경색은 어두운 남색(#1E2A45), 글자색은 흰색(#FFFFFF)
    st.markdown(f"""
        <div style="
            background-color: #1E2A45;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #4da6ff;
            color: #FFFFFF;
            margin-bottom: 20px;
            font-size: 16px;
            line-height: 1.6;
        ">
            {text.replace('\n', '<br>')}
        </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------
# 1. 초기 설정 및 데이터 로드
# -----------------------------------------------------
st.set_page_config(layout="wide", page_title="장애 발생 현황")

FILE_PATHS = ['kiosk_data_2025.xlsx', 'kiosk_data_2026.xlsx']
df = dl.load_and_combine_data(FILE_PATHS)

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
    st.stop()

st.title("📊 키오스크 장애 발생 현황 대시보드")
st.markdown("---")

# -----------------------------------------------------
# 2. 사이드바 필터링 (모드 스위칭 적용)
# -----------------------------------------------------
st.sidebar.header("필터링 옵션")

# [핵심] 조회 기준 선택 스위치
analysis_mode = st.sidebar.radio(
    "🔍 조회 기준 선택",
    ["월간/주간 보기", "분기별 보기"],
    horizontal=True
)
st.sidebar.markdown("---")

# 변수 초기화 (KPI 로직에서 공통으로 쓰기 위함)
detail_df = pd.DataFrame()     # 선택된 현재 데이터
comparison_df = pd.DataFrame() # 비교할 과거 데이터
selected_month = '전체'        # 차트 타이틀용
selected_week = '전체'         # 차트 타이틀용
prev_week_label = None         # 차트 비교용

# =========================================================
# [MODE 1] 기존 월간/주간 보기 (기존 코드 그대로 이동)
# =========================================================
if analysis_mode == "월간/주간 보기":
    
    # 1) 월별 선택
    sorted_months = sorted(df['월_표기'].unique().tolist(), reverse=True)
    unique_months = ['전체'] + sorted_months
    selected_month = st.sidebar.selectbox("📅 1. 월별 선택:", unique_months)
    
    # 2) 주간 선택
    if selected_month != '전체':
        temp_month_df = df[df['월_표기'] == selected_month]
        week_group = temp_month_df[['주간_라벨', '주_시작일']].drop_duplicates().sort_values('주_시작일')
        week_list = week_group['주간_라벨'].tolist()
        unique_weeks = ['전체'] + week_list
        selected_week = st.sidebar.selectbox("📅 2. 주간 선택:", unique_weeks)
        
        if selected_week != '전체':
            try:
                curr_idx = week_list.index(selected_week)
                if curr_idx > 0: prev_week_label = week_list[curr_idx - 1]
            except: pass

    # 데이터 필터링 로직
    if selected_week != '전체':
        current_df = df[df['주간_라벨'] == selected_week].copy()
    elif selected_month != '전체':
        current_df = df[df['월_표기'] == selected_month].copy()
    else:
        current_df = df.copy()

    # 3) 유형 선택
    unique_types = ['전체'] + sorted(df['장애유형'].unique().tolist()) if '장애유형' in df.columns else ['전체']
    selected_type = st.sidebar.selectbox("🛠️ 3. 장애 유형 선택:", unique_types)
    if selected_type != '전체':
        current_df = current_df[current_df['장애유형'] == selected_type]

    # 최종 데이터 확정
    detail_df = current_df.copy()
    
    # 비교 데이터(comparison_df) 설정 (월간/주간용)
    if selected_week != '전체' and prev_week_label:
        comparison_df = df[df['주간_라벨'] == prev_week_label]
        if selected_type != '전체':
            comparison_df = comparison_df[comparison_df['장애유형'] == selected_type]
    
    # KPI 라벨 설정 로직은 아래 KPI 섹션에서 처리

# =========================================================
# [MODE 2] 신규 분기별 보기 (새로 추가된 로직)
# =========================================================
else:
    # 1) 연도 선택
    unique_years = sorted(df['연도'].unique().tolist(), reverse=True)
    selected_year = st.sidebar.selectbox("📅 1. 연도 선택:", unique_years)
    
    # 2) 분기 선택
    # 해당 연도에 데이터가 있는 분기만 보여줌
    year_df = df[df['연도'] == selected_year]
    unique_quarters = sorted(year_df['분기'].unique().tolist())
    selected_quarter = st.sidebar.selectbox("📅 2. 분기 선택:", unique_quarters)
    
    # 3) 유형 선택
    unique_types = ['전체'] + sorted(df['장애유형'].unique().tolist()) if '장애유형' in df.columns else ['전체']
    selected_type = st.sidebar.selectbox("🛠️ 3. 장애 유형 선택:", unique_types)

    # 데이터 필터링
    current_df = df[(df['연도'] == selected_year) & (df['분기'] == selected_quarter)].copy()
    if selected_type != '전체':
        current_df = current_df[current_df['장애유형'] == selected_type]
        
    detail_df = current_df.copy()
    
    # 비교 데이터(comparison_df) 설정 (전분기 대비)
    # 로직: 1분기면 작년 4분기, 아니면 같은 해 이전 분기
    curr_q_num = int(selected_quarter.replace('분기',''))
    prev_q_num = curr_q_num - 1
    prev_year_val = selected_year
    
    if prev_q_num == 0: # 1분기 이전은 작년 4분기
        prev_q_num = 4
        prev_year_val = str(int(selected_year.replace('년','')) - 1) + "년"
    
    prev_q_str = f"{prev_q_num}분기"
    
    comparison_df = df[(df['연도'] == prev_year_val) & (df['분기'] == prev_q_str)]
    if selected_type != '전체':
        comparison_df = comparison_df[comparison_df['장애유형'] == selected_type]


st.sidebar.markdown(f"**선택된 데이터:** {len(detail_df):,}건")


# -----------------------------------------------------
# 3. KPI 지표 계산 (공통 로직 활용)
# -----------------------------------------------------
kpi1, kpi2, kpi3 = st.columns(3)

prev_period_df = pd.DataFrame()
kpi_label_suffix = ""

# 비교 데이터 연결
if not comparison_df.empty:
    prev_period_df = comparison_df
    if analysis_mode == "분기별 보기":
        kpi_label_suffix = " (전분기 대비)"
    elif selected_week != '전체':
        kpi_label_suffix = " (지난주 대비)"

# 월간 보기일 때 전월 비교 처리 (기존 로직)
if analysis_mode == "월간/주간 보기" and selected_week == '전체' and selected_month != '전체':
    try:
        curr_idx = sorted_months.index(selected_month)
        if curr_idx + 1 < len(sorted_months):
            prev_month_name = sorted_months[curr_idx + 1]
            temp_prev = df[df['월_표기'] == prev_month_name]
            if selected_type != '전체':
                temp_prev = temp_prev[temp_prev['장애유형'] == selected_type]
            prev_period_df = temp_prev
            kpi_label_suffix = " (전월 대비)"
    except: pass

# KPI 출력 (공통)
total_count = len(detail_df)
total_delta = None
if not prev_period_df.empty:
    diff_total = total_count - len(prev_period_df)
    total_delta = f"{diff_total:+}건"

with kpi1:
    st.metric("총 발생 건수", f"{total_count:,}건", total_delta, delta_color="inverse")
    if kpi_label_suffix and total_delta: st.caption(kpi_label_suffix)

day_count = detail_df['발생일'].nunique() if not detail_df.empty else 0
avg = total_count / day_count if day_count > 0 else 0
with kpi2: st.metric("일평균 발생", f"{avg:.1f}건")

if not detail_df.empty and '장애유형' in detail_df.columns:
    top_series = detail_df['장애유형'].value_counts()
    top_type_name = top_series.idxmax()
    current_type_count = top_series.max()
    type_delta = None
    if not prev_period_df.empty:
        prev_count_series = prev_period_df[prev_period_df['장애유형'] == top_type_name]
        prev_type_count = len(prev_count_series)
        diff_type = current_type_count - prev_type_count
        type_delta = f"{diff_type:+}건"
    with kpi3:
        st.metric("최다 발생 유형", f"{top_type_name} ({current_type_count}건)", type_delta, delta_color="inverse")
else:
    with kpi3: st.metric("최다 발생 유형", "-")

st.markdown("---")


# -----------------------------------------------------
# 4. 시각화 영역
# -----------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    if analysis_mode == "분기별 보기":
        st.subheader(f"1️⃣ {selected_year} 분기별 장애 발생 추이")
        base_df = df[df['연도'] == selected_year].copy()
        if selected_type != '전체': base_df = base_df[base_df['장애유형'] == selected_type]
        
        # [추가] AI 인사이트
        ui_info(ins.analyze_trend(base_df, '분기', '분기'))
        
        st.plotly_chart(ch.plot_quarterly_trend(base_df, selected_year), width="stretch", key="chart_quarterly")
        
    else:
        st.subheader("1️⃣ 월간 장애 발생 추이")
        base_df = df.copy()
        if selected_type != '전체': base_df = base_df[base_df['장애유형'] == selected_type]
        
        # [추가] AI 인사이트
        ui_info(ins.analyze_trend(base_df, '월_표기', '월'))
        
        st.plotly_chart(ch.plot_monthly_trend(base_df, selected_type, selected_month), width="stretch", key="chart_monthly")

with col2:
    if analysis_mode == "분기별 보기":
         st.subheader(f"2️⃣ 주간 장애 발생 추이 ({selected_quarter})")
         # [추가] 주간 데이터에 대한 인사이트는 생략하거나 필요시 추가 가능
         st.plotly_chart(ch.plot_weekly_trend(current_df), width="stretch", key="chart_weekly_quarter")
    
    elif selected_week == '전체':
        st.subheader(f"2️⃣ 주간 장애 발생 추이 ({selected_month if selected_month != '전체' else '전체'})")
        st.plotly_chart(ch.plot_weekly_trend(current_df), width="stretch", key="chart_weekly")
    else:
        st.subheader(f"2️⃣ 일별 발생 패턴 (이번 주 vs 지난주)")
        st.plotly_chart(ch.plot_daily_comparison(detail_df, comparison_df, selected_week, prev_week_label), width="stretch", key="chart_daily")

st.markdown("---")

# [2열] 요일/시간 패턴 (통합 인사이트 제공)
st.subheader("3️⃣/4️⃣ 요일 및 시간대 집중 분석")
# [추가] 요일/시간 패턴에 대한 AI 인사이트 (차트 위에 크게 하나로 표시)
if not detail_df.empty:
    ui_info(ins.analyze_day_time(detail_df))

col3, col4 = st.columns(2)
with col3:
    # st.subheader("3️⃣ 요일별 발생 패턴") -> 위에서 통합 제목을 썼으므로 생략 가능하나 유지해도 됨
    if not detail_df.empty:
        st.plotly_chart(ch.plot_day_pattern(detail_df), width="stretch", key="chart_day_pat")
    else: st.info("데이터 없음")

with col4:
    # st.subheader("4️⃣ 시간대별 집중 발생")
    if not detail_df.empty:
        st.plotly_chart(ch.plot_time_pattern(detail_df), width="stretch", key="chart_time_pat")
    else: st.info("데이터 없음")

st.markdown("---")

st.subheader("5️⃣ 장애 다발 기기 Top 3")
# [추가] 기기 분석 AI 인사이트
if not detail_df.empty:
    ui_info(ins.analyze_top_devices(detail_df))
    
    fig_top3 = ch.plot_top3_devices(detail_df)
    if fig_top3:
        st.plotly_chart(fig_top3, width="stretch", key="chart_device_top3")
    else: st.info("데이터 없음")
else: st.info("데이터 없음")

st.markdown("---")


# -----------------------------------------------------
# 5. 상호작용 및 상세 데이터 (기존 유지)
# -----------------------------------------------------
# (이하 섹션 6, 7 코드는 detail_df, prev_period_df만 있으면 자동으로 동작하므로 수정할 필요 없습니다.)
# (app.py의 나머지 뒷부분 코드는 기존 그대로 두시면 됩니다.)
# ...
# ... (코드 생략 없이 기존 코드 유지해주세요)
# ...
st.header("6️⃣ 장애 유형 상세 비교 분석")

ui_info(ins.analyze_comparison(prev_period_df, detail_df))

# 세션 상태 초기화
if 'dashboard_selected_type' not in st.session_state:
    st.session_state.dashboard_selected_type = None

# 비교 데이터 준비
if not prev_period_df.empty and not detail_df.empty:
    # 막대 데이터 생성
    df_curr_long = detail_df.groupby('장애유형').size().reset_index(name='건수')
    df_curr_long['기간'] = '현재 기간'
    df_prev_long = prev_period_df.groupby('장애유형').size().reset_index(name='건수')
    df_prev_long['기간'] = '이전 기간'
    bar_df_long = pd.concat([df_prev_long, df_curr_long], ignore_index=True)

    tab_pie, tab_bar = st.tabs(["📊 기간별 비교 (막대그래프)","🥧 유형별 점유율"])

    # [탭 1] 막대 그래프 (클릭 이벤트 포함)
    with tab_pie:
        st.subheader("📊 기간별 발생 건수 상세 비교")
        st.caption("👇 막대를 클릭하면 하단에 상세 내역이 표시됩니다.")
        
        # charts 모듈 함수 호출
        fig_bar = ch.plot_comparison_bar(bar_df_long)
        
        event_bar = st.plotly_chart(
            fig_bar, width="stretch", key="chart_grouped_bar",
            on_select="rerun", selection_mode="points"
        )
        
        if event_bar and event_bar.selection["points"]:
            clicked_bar_type = event_bar.selection["points"][0]["x"]
            if st.session_state.dashboard_selected_type != clicked_bar_type:
                st.session_state.dashboard_selected_type = clicked_bar_type
                st.rerun()

    # [탭 2] 파이 차트
    with tab_bar:
        c_prev, c_curr = st.columns(2)
        current_selection = st.session_state.dashboard_selected_type
        
        with c_prev:
            st.subheader("📉 이전 기간")
            pie_prev = prev_period_df.groupby('장애유형').size().reset_index(name='건수')
            pull_vals_p = [0.2 if x == current_selection else 0 for x in pie_prev['장애유형']]
            st.plotly_chart(ch.plot_pie_chart(pie_prev, pull_vals_p), width="stretch", key="pie_prev")
            
        with c_curr:
            st.subheader("📈 현재 기간")
            pie_curr = detail_df.groupby('장애유형').size().reset_index(name='건수')
            pull_vals_c = [0.2 if x == current_selection else 0 for x in pie_curr['장애유형']]
            st.plotly_chart(ch.plot_pie_chart(pie_curr, pull_vals_c), width="stretch", key="pie_curr")

else:
    # 단독 모드 (비교 데이터 없음)
    st.info("비교할 과거 데이터가 없어 현재 데이터만 표시합니다.")
    if not detail_df.empty:
        pie_data_curr = detail_df.groupby('장애유형').size().reset_index(name='건수')
        current_selection = st.session_state.dashboard_selected_type
        pull_vals = [0 if x == current_selection else 0 for x in pie_data_curr['장애유형']]
        st.plotly_chart(ch.plot_pie_chart(pie_data_curr, pull_vals), width="stretch", key="pie_solo")


# -----------------------------------------------------
# 6. 상세 데이터 원본 조회 (Drill-down)
# -----------------------------------------------------
st.markdown("---")
final_selected_type = st.session_state.dashboard_selected_type
target_cols = ['발생일', '발생시간','기기명', '장애유형', '장애알람', '조치 내용','교체일시','교체 기기명','교체 모듈']

if final_selected_type:
    st.header(f"7️⃣ 상세 데이터 원본 조회: :red[{final_selected_type}]")
    
    # 데이터 필터링 및 날짜 포맷 함수
    def format_and_show(source_df):
        f_df = source_df[source_df['장애유형'] == final_selected_type].copy()
        if not f_df.empty:
            v_cols = [c for c in target_cols if c in f_df.columns]
            s_df = f_df[v_cols].sort_values('발생일', ascending=False)
            if '발생일' in s_df.columns:
                s_df['발생일'] = s_df['발생일'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else "")
            st.dataframe(s_df, width="stretch", hide_index=True)
        else:
            st.warning("데이터가 없습니다.")

    t1, t2 = st.tabs(["📈 현재 기간 데이터", "📉 이전 기간 데이터"])
    with t1: format_and_show(detail_df)
    with t2:
        if not prev_period_df.empty: format_and_show(prev_period_df)
        else: st.info("이전 기간 데이터 없음")

else:
    st.header("7️⃣ 상세 데이터 원본 조회 (전체)")
    if not detail_df.empty:
        v_cols = [c for c in target_cols if c in detail_df.columns]
        s_df = detail_df[v_cols].sort_values('발생일', ascending=False) if v_cols else detail_df
        if '발생일' in s_df.columns:
            s_df['발생일'] = s_df['발생일'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else "")
        st.dataframe(s_df, width="stretch", hide_index=True)
    else:
        st.info("데이터가 없습니다.")