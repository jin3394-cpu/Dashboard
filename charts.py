import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# -----------------------------------------------------
# 차트 생성 함수 모음
# -----------------------------------------------------

def plot_monthly_trend(base_df, selected_type, selected_month):
    """월간 장애 발생 추이 차트"""
    m_stats = base_df.groupby('월_표기').size().reset_index(name='건수')
    
    # [수정] 정렬 방식 변경
    # 기존: 숫자로 변환해서 정렬 -> 에러 발생 원인
    # 변경: 'YYYY년 MM월' 문자열 그대로 정렬해도 날짜순으로 잘 정렬됩니다.
    m_stats = m_stats.sort_values('월_표기')
    
    colors = ['#EF553B' if m == selected_month else '#ABACF7' for m in m_stats['월_표기']]
    fig = go.Figure(data=[go.Bar(x=m_stats['월_표기'], y=m_stats['건수'], marker_color=colors, text=m_stats['건수'])])
    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_title="월", yaxis_title="건수", margin=dict(t=20, b=20, l=20, r=20))
    return fig

def plot_weekly_trend(current_df):
    """주간 장애 발생 추이 라인 차트"""
    w_stats = current_df.groupby(['주_시작일', '주간_라벨']).size().reset_index(name='건수').sort_values('주_시작일')
    fig = px.line(w_stats, x='주간_라벨', y='건수', markers=True, text='건수')
    fig.update_traces(textposition="top center")
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=20, b=20, l=20, r=20))
    return fig

def plot_daily_comparison(detail_df, comparison_df, selected_week, prev_week_label):
    """일별 발생 패턴 비교 (이번주 vs 지난주)"""
    curr_daily = detail_df.groupby('요일_숫자').size().reindex(range(7), fill_value=0)
    prev_daily = comparison_df.groupby('요일_숫자').size().reindex(range(7), fill_value=0) if not comparison_df.empty else pd.Series([0]*7)
    days = ['월', '화', '수', '목', '금', '토', '일']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=prev_daily.values, name=f"지난주 ({prev_week_label})", line=dict(color='gray', width=2, dash='dot')))
    fig.add_trace(go.Scatter(x=days, y=curr_daily.values, name=f"선택 주 ({selected_week})", line=dict(color='#EF553B', width=4), mode='lines+markers+text', text=curr_daily.values, textposition='top center'))
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=40, b=20, l=20, r=20))
    return fig

def plot_day_pattern(detail_df):
    """요일별 발생 패턴"""
    d_cnt = detail_df.groupby(['요일_명','요일_숫자']).size().reset_index(name='건수').sort_values('요일_숫자')
    fig = px.bar(d_cnt, x='요일_명', y='건수', text='건수')
    fig.update_traces(marker_color='#00CC96')
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    return fig

def plot_time_pattern(detail_df):
    """시간대별 발생 패턴"""
    h_cnt = detail_df['시간'].value_counts().reindex(range(24), fill_value=0).sort_index()
    h_df = pd.DataFrame({'시간': h_cnt.index, '건수': h_cnt.values})
    h_df['라벨'] = h_df['시간'].apply(lambda x: f"{x:02d}시")
    fig = px.bar(h_df, x='라벨', y='건수', text='건수', color='건수', color_continuous_scale='Reds')
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    return fig

def plot_top3_devices(detail_df):
    """기기별 Top 3 막대 차트"""
    top_devices_list = detail_df['기기명'].value_counts().head(3).index.tolist()
    if not top_devices_list: return None
    
    top3_df = detail_df[detail_df['기기명'].isin(top_devices_list)]
    chart_data = top3_df.groupby(['기기명', '장애유형']).size().reset_index(name='건수')
    
    fig = px.bar(
        chart_data, y='기기명', x='건수', color='장애유형', 
        text='건수', orientation='h', 
        category_orders={"기기명": top_devices_list}
    )
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'}, 
        xaxis_title="발생 건수", yaxis_title="기기명",
        height=300, margin=dict(t=20, b=20, l=20, r=20)
    )
    return fig

def plot_comparison_bar(bar_df_long):
    """유형 상세 비교 (그룹형 막대)"""
    fig = px.bar(
        bar_df_long, x='장애유형', y='건수', color='기간', barmode='group',
        text='건수', color_discrete_map={'이전 기간': '#ABACF7', '현재 기간': '#EF553B'},
        category_orders={"기간": ["이전 기간", "현재 기간"]}
    )
    fig.update_layout(
        xaxis_title=None, yaxis_title="발생 건수", legend_title=None,
        margin=dict(t=20, b=20, l=20, r=20), hovermode="x unified",
        clickmode='event+select'
    )
    fig.update_traces(
        textfont_color='white', textposition='outside',
        selected=dict(marker=dict(opacity=1), textfont=dict(color='white')),
        unselected=dict(marker=dict(opacity=1), textfont=dict(color='white'))
    )
    return fig

def plot_pie_chart(data, pull_vals):
    """파이 차트 생성"""
    fig = px.pie(data, names='장애유형', values='건수', hole=0.4)
    fig.update_traces(pull=pull_vals)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5), margin=dict(t=0, b=50, l=0, r=0))
    return fig