# insights.py
import pandas as pd
from collections import Counter

def analyze_trend(df, x_col, period_name):
    """
    [섹션 1, 2] 월간/분기/주간 추이 분석 멘트 생성
    """
    if df.empty: return "데이터가 부족하여 분석할 수 없습니다."

    # 그룹핑 및 통계 계산
    stats = df.groupby(x_col).size()
    if stats.empty: return "데이터가 없습니다."

    max_val = stats.max()
    max_period = stats.idxmax()
    avg_val = stats.mean()
    
    # 평균 대비 배수 계산
    ratio = max_val / avg_val if avg_val > 0 else 0

    comment = f"💡 **AI 분석:** 전체 기간 중 **'{max_period}'**에 장애가 가장 집중되었습니다. (총 {max_val}건)\n\n"
    comment += f"이는 평균 발생 건수({avg_val:.1f}건) 대비 **약 {ratio:.1f}배 높은 수치**로, 해당 시점의 특이 사항(업데이트, 이벤트 등) 점검이 필요합니다."
    
    return comment

def analyze_day_time(df):
    """
    [섹션 3, 4] 요일 및 시간대 패턴 분석
    """
    if df.empty: return "분석할 데이터가 없습니다."

    # 최다 요일
    top_day = df['요일_명'].mode()[0]
    day_count = len(df[df['요일_명'] == top_day])
    
    # 최다 시간대
    top_time = df['시간'].mode()[0]
    time_count = len(df[df['시간'] == top_time])
    
    # 평일 vs 주말 비중
    weekend_days = [5, 6] # 토, 일
    weekend_cnt = len(df[df['요일_숫자'].isin(weekend_days)])
    weekday_cnt = len(df) - weekend_cnt
    
    pattern = "평일" if weekday_cnt > weekend_cnt else "주말"
    
    comment = f"💡 **AI 분석:** 장애 발생 패턴은 주로 **{pattern}**에 집중되어 있으며, 특히 **'{top_day}요일 {top_time}시'** 대역에 빈도가 가장 높습니다.\n\n"    
    
    return comment

import pandas as pd
from collections import Counter

# ... (기존 analyze_trend, analyze_day_time 함수는 그대로 유지) ...

def analyze_top_devices(df):
    """
    [섹션 5] 기기별 편중도 및 Top 3 상세 원인 분석 (줄바꿈 + 중복 유형 하이라이트)
    """
    if df.empty: return "분석할 데이터가 없습니다."

    # 기기별 건수 카운트 및 상위 3개 추출
    dev_counts = df['기기명'].value_counts().head(3)
    
    if dev_counts.empty: return "데이터가 없습니다."

    # [1] 중복 장애 유형 찾기 (하이라이트용)
    # 상위 3개 기기 각각 어떤 에러들이 있었는지 집합(Set)으로 수집
    device_error_sets = []
    for device in dev_counts.index:
        errors = set(df[df['기기명'] == device]['장애유형'].unique())
        device_error_sets.append(errors)
    
    # 전체 에러 리스트를 만들어서 카운팅
    all_errors = []
    for err_set in device_error_sets:
        all_errors.extend(list(err_set))
    
    # 2개 이상의 기기에서 발견된 에러 찾기
    dup_counter = Counter(all_errors)
    duplicate_errors = {err for err, count in dup_counter.items() if count >= 2}


    # [2] 멘트 생성 시작
    total_cnt = len(df)
    top1_share = (dev_counts.iloc[0] / total_cnt) * 100
    
    comment = f"💡 **AI 분석:** 상위 3개 기기가 전체 장애의 **{top1_share:.1f}%(1위 기준)** 를 점유하고 있습니다. 각 기기별 주요 장애 원인은 다음과 같습니다."    

    # Top 1 ~ Top 3 반복문 실행
    for i, (device, total_val) in enumerate(dev_counts.items(), 1):
        target_device_df = df[df['기기명'] == device]
        error_counts = target_device_df['장애유형'].value_counts()
        
        # 상세 내역 리스트 만들기
        details = []
        for err_type, err_cnt in error_counts.items():
            # 기본 텍스트
            text_part = f"{err_type}({err_cnt}건)"
            
            # [하이라이트] 중복 유형이면 노란색 + 굵게 처리
            if err_type in duplicate_errors:
                text_part = f"<span style='color: #FFD700; font-weight: bold;'>{text_part}</span>"
            
            details.append(text_part)
        
        # [줄바꿈] 리스트 형태로 줄바꿈 연결
        # \n 뒤에 공백을 주어 들여쓰기 효과
        detail_str = "\n   - ".join(details)
        
        comment += f"\n\n**{i}위. {device} (총 {total_val}건)**\n"
        comment += f"   - {detail_str}"

    comment += "\n\n반복적인 장애가 발생하는 기기에 대해서는 부품 교체 이력 및 설치 환경(전원/통신) 정밀 진단이 권장됩니다."
    
    return comment

# ... (마지막 analyze_comparison 함수는 그대로 유지) ...
# [수정] 건수 + 증감률(%) 함께 표시
def analyze_comparison(prev_df, curr_df):
    """
    [섹션 6] 기간별 장애 유형 증감 상세 분석 (건수 + 퍼센트 + 하이라이트)
    """
    if curr_df.empty: return "분석할 현재 데이터가 없습니다."
    
    curr_counts = curr_df['장애유형'].value_counts()
    
    if prev_df.empty:
        top_type = curr_counts.idxmax()
        return f"💡 **AI 분석:** 현재 기간에는 **'{top_type}'** 유형이 가장 높은 비중을 차지하고 있습니다. 과거 데이터와 비교하려면 비교 기간을 설정해주세요."

    prev_counts = prev_df['장애유형'].value_counts()
    all_types = list(set(curr_counts.index) | set(prev_counts.index))
    
    changes = []
    for t in all_types:
        c_val = curr_counts.get(t, 0)
        p_val = prev_counts.get(t, 0)
        diff = c_val - p_val
        
        # 증감률 계산 (0으로 나누기 방지)
        if p_val > 0:
            pct = (diff / p_val) * 100
        else:
            pct = None # 이전 데이터가 0이면 계산 불가 (신규 발생)

        changes.append({'type': t, 'diff': diff, 'pct': pct, 'p_val': p_val})
    
    if not changes: return "변동 사항이 없습니다."

    # 1. 가장 많이 증가한 유형 (Worst)
    max_inc = max(changes, key=lambda x: x['diff'])
    # 2. 가장 많이 감소한 유형 (Best)
    max_dec = min(changes, key=lambda x: x['diff'])
    
    comment_parts = []
    
    # [증가 이슈 언급] - 빨간색 하이라이트
    if max_inc['diff'] > 0:
        # 퍼센트 문자열 처리
        if max_inc['pct'] is not None:
            pct_str = f"({max_inc['pct']:.1f}%)"
        else:
            pct_str = "(신규)"
            
        highlight_text = f"<span style='color: #FF6B6B; font-weight: bold;'>'{max_inc['type']}' 유형이 {int(max_inc['diff'])}건{pct_str} 증가</span>"
        comment_parts.append(f"🔴 주의: 지난 기간 대비 {highlight_text}하여 가장 큰 상승폭을 보였습니다.")
    
    # [감소(개선) 이슈 언급] - 하늘색 하이라이트
    if max_dec['diff'] < 0:
        # 퍼센트 문자열 처리 (감소이므로 절대값 사용)
        if max_dec['pct'] is not None:
            pct_str = f"({abs(max_dec['pct']):.1f}%)"
        else:
            pct_str = ""
            
        highlight_text = f"<span style='color: #4BCFFA; font-weight: bold;'>'{max_dec['type']}' 유형은 {abs(int(max_dec['diff']))}건{pct_str} 감소</span>"
        comment_parts.append(f"🔵 긍정: 지난 기간 대비 {highlight_text}하여 가장 뚜렷한 개선 효과를 보였습니다.")
    
    if not comment_parts:
        return "💡 **AI 분석:** 지난 기간과 비교했을 때 장애 발생 건수에 큰 변동이 없습니다."
    
    # 문장 합치기
    full_comment = "💡 **AI 분석:** 상세 비교 결과입니다.\n\n" + "\n\n".join(comment_parts)
              
    return full_comment
