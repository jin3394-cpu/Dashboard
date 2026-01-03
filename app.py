import streamlit as st
import pandas as pd
import data_loader as dl  # 분리한 데이터 로드 모듈
import charts as ch       # 분리한 차트 모듈

# -----------------------------------------------------
# 1. 초기 설정 및 데이터 로드
# -----------------------------------------------------
st.set_page_config(layout="wide", page_title="장애 발생 현황")

# [수정 1] 2025년, 2026년 파일 경로 리스트
FILE_PATHS = ['kiosk_data_2025.xlsx', 'kiosk_data_2026.xlsx']

# 모듈을 통해 통합 데이터 로드
df = dl.load_and_combine_data(FILE_PATHS)

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
    st.stop()

st.title("📊 키오스크 장애 발생 현황 대시보드")
st.markdown("---")

# -----------------------------------------------------
# 2. 사이드바 필터링 (로직 변경 구간)
# -----------------------------------------------------
st.sidebar.header("필터링 옵션")

# 1) 월별 선택 (데이터 필터링용 X, 주간 목록 생성용 O)
# 내림차순 정렬 (최신 월이 위로)
sorted_months = sorted(df['월_표기'].unique().tolist(), reverse=True)
unique_months = ['전체'] + sorted_months
selected_month = st.sidebar.selectbox("📅 1. 월별 선택:", unique_months)

# 2) 주간 선택
selected_week = '전체'
prev_week_label = None

# 월을 선택했을 때, 해당 월에 '걸쳐있는' 주간 목록을 보여줌
if selected_month != '전체':
    # 주간 목록을 만들기 위해 임시로 필터링 (실제 데이터엔 영향 없음)
    temp_month_df = df[df['월_표기'] == selected_month]
    week_group = temp_month_df[['주간_라벨', '주_시작일']].drop_duplicates().sort_values('주_시작일')
    week_list = week_group['주간_라벨'].tolist()
    unique_weeks = ['전체'] + week_list
    
    selected_week = st.sidebar.selectbox("📅 2. 주간 선택:", unique_weeks)
    
    # 이전 주 라벨 찾기 (KPI 비교용)
    if selected_week != '전체':
        try:
            curr_idx = week_list.index(selected_week)
            # 리스트에 없더라도 전체 데이터 기준 이전 주를 찾을 수 있으면 좋겠지만, 
            # 일단 목록 내에서 이전 주를 찾습니다.
            if curr_idx > 0: prev_week_label = week_list[curr_idx - 1]
        except: pass

# [중요] 3) 기본 데이터셋(current_df) 확정 로직
# 월 선택이 데이터를 자르지 않도록 순서를 조정했습니다.

if selected_week != '전체':
    # Case A: 주간을 선택했다면? -> 월 무시하고 '주간 라벨'로 전체에서 검색
    # (이렇게 해야 12월을 선택했어도 1월 데이터가 포함된 주간 데이터를 온전히 가져옴)
    current_df = df[df['주간_라벨'] == selected_week].copy()
elif selected_month != '전체':
    # Case B: 주간은 전체고, 월만 선택했다면? -> 그제서야 월별로 자름
    current_df = df[df['월_표기'] == selected_month].copy()
else:
    # Case C: 아무것도 선택 안 함 -> 전체 데이터
    current_df = df.copy()

# 4) 유형 선택 (확정된 current_df 내에서 필터링)
unique_types = ['전체'] + sorted(df['장애유형'].unique().tolist()) if '장애유형' in df.columns else ['전체']
selected_type = st.sidebar.selectbox("🛠️ 3. 장애 유형 선택:", unique_types)

if selected_type != '전체':
    current_df = current_df[current_df['장애유형'] == selected_type]

# 데이터셋 최종 명명 (가독성을 위해)
detail_df = current_df.copy()

# 비교 데이터셋(comparison_df) 생성 - KPI용
comparison_df = pd.DataFrame()

if selected_week != '전체' and prev_week_label:
    # 비교 데이터는 항상 '전체 원본(df)'에서 찾습니다. (월 경계 무시)
    comparison_df = df[df['주간_라벨'] == prev_week_label]
    if selected_type != '전체':
        comparison_df = comparison_df[comparison_df['장애유형'] == selected_type]

st.sidebar.markdown(f"**선택된 데이터:** {len(detail_df):,}건")


# -----------------------------------------------------
# 3. KPI 지표 계산
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
        if curr_idx + 1 < len(sorted_months): # 내림차순이므로 다음 인덱스가 이전 달
            prev_month_name = sorted_months[curr_idx + 1]
            temp_prev = df[df['월_표기'] == prev_month_name]
            if selected_type != '전체':
                temp_prev = temp_prev[temp_prev['장애유형'] == selected_type]
            prev_period_df = temp_prev
            kpi_label_suffix = " (전월 대비)"
    except: pass

# KPI 1: 총 발생 건수
total_count = len(detail_df)
total_delta = None
if not prev_period_df.empty:
    diff_total = total_count - len(prev_period_df)
    total_delta = f"{diff_total:+}건"

with kpi1:
    st.metric("총 발생 건수", f"{total_count:,}건", total_delta, delta_color="inverse")
    if kpi_label_suffix and total_delta: st.caption(kpi_label_suffix)

# KPI 2: 일평균 발생
day_count = detail_df['발생일'].nunique() if not detail_df.empty else 0
avg = total_count / day_count if day_count > 0 else 0
with kpi2: st.metric("일평균 발생", f"{avg:.1f}건")

# KPI 3: 최다 발생 유형
if not detail_df.empty and '장애유형' in detail_df.columns:
    top_series = detail_df['장애유형'].value_counts()
    top_type_name = top_series.idxmax()
    current_type_count = top_series.max()
    
    type_delta = None
    if not prev_period_df.empty:
        # 이전 기간 데이터에서 동일 유형 개수 찾기
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
# 4. 시각화 영역 (charts 모듈 사용)
# -----------------------------------------------------
# [1열] 월간/주간
col1, col2 = st.columns(2)
with col1:
    st.subheader("1️⃣ 월간 장애 발생 추이")
    base_df = df.copy() # 월간 추이는 전체 흐름을 봐야 하므로 전체 df 사용
    if selected_type != '전체': base_df = base_df[base_df['장애유형'] == selected_type]
    st.plotly_chart(ch.plot_monthly_trend(base_df, selected_type, selected_month), width="stretch", key="chart_monthly")

with col2:
    if selected_week == '전체':
        st.subheader(f"2️⃣ 주간 장애 발생 추이 ({selected_month if selected_month != '전체' else '전체'})")
        # 주간 추이는 선택된 범위(월 or 전체) 내에서 보여줌
        st.plotly_chart(ch.plot_weekly_trend(current_df), width="stretch", key="chart_weekly")
    else:
        st.subheader(f"2️⃣ 일별 발생 패턴 (이번 주 vs 지난주)")
        st.plotly_chart(ch.plot_daily_comparison(detail_df, comparison_df, selected_week, prev_week_label), width="stretch", key="chart_daily")

st.markdown("---")

# [2열] 요일/시간
col3, col4 = st.columns(2)
with col3:
    st.subheader("3️⃣ 요일별 발생 패턴")
    if not detail_df.empty:
        st.plotly_chart(ch.plot_day_pattern(detail_df), width="stretch", key="chart_day_pat")
    else: st.info("데이터 없음")

with col4:
    st.subheader("4️⃣ 시간대별 집중 발생")
    if not detail_df.empty:
        st.plotly_chart(ch.plot_time_pattern(detail_df), width="stretch", key="chart_time_pat")
    else: st.info("데이터 없음")

st.markdown("---")

# [3열] 기기 Top 3
st.subheader("5️⃣ 장애 다발 기기 Top 3")
if not detail_df.empty:
    fig_top3 = ch.plot_top3_devices(detail_df)
    if fig_top3:
        st.plotly_chart(fig_top3, width="stretch", key="chart_device_top3")
    else: st.info("데이터 없음")
else: st.info("데이터 없음")

st.markdown("---")


# -----------------------------------------------------
# 5. 상호작용 및 상세 비교 (Interactivity)
# -----------------------------------------------------
st.header("6️⃣ 장애 유형 상세 비교 분석")

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

