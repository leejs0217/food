from datetime import datetime
import re
import requests
import streamlit as st
import pytz

# 송탄고등학교 고정 정보
ATPT_OFCDC_SC_CODE = "J10"      # 경기도교육청
SD_SCHUL_CODE = "7530480"       # 송탄고등학교
SCHOOL_NAME = "송탄고등학교"

# 페이지 설정
st.set_page_config(
    page_title="각 학교별로 디저트가 많이 나온 날은?",
    page_icon="📅",
    layout="wide"
)

st.title("📅 각 학교별로 디저트가 많이 나온 날은?")
st.caption(f"🏫 대상 학교: **{SCHOOL_NAME}** (경기도평택교육지원청 / 경기도교육청)")

# 1. 한국 표준시(KST) 기준 오늘 날짜 구하기
tz_kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.now(tz_kst).date()

# 2. 상단 컨트롤 영역 (날짜 선택 & 알레르기 스위치 나란히 배치)
col_control1, col_control2 = st.columns([2, 1])

with col_control1:
    selected_date = st.date_input("📆 조회할 날짜를 선택하세요", value=today_kst)

with col_control2:
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

st.divider()

# 3. 급식 정보 API 조회 함수
def get_songtan_meal(date_str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": date_str,
        "MLSV_TO_YMD": date_str,
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"][0]
        return None
    except Exception:
        return None

# 4. 조회 실행 및 결과 화면 구성
date_str = selected_date.strftime("%Y%m%d")
meal_data = get_songtan_meal(date_str)

if meal_data:
    raw_ddish = meal_data.get("DDISH_NM", "")
    
    # <br/> 및 <br> 태그로 메뉴 분리
    raw_items = [
        item.strip() 
        for item in re.split(r"<br\s*/?>", raw_ddish) 
        if item.strip()
    ]
    
    # 알레르기 스위치가 꺼져있으면 괄호 안 숫자/문자 제거
    processed_items = []
    for item in raw_items:
        if not show_allergy:
            # 메뉴명 뒤 괄호와 그 안의 알레르기 번호 제거 (예: "쌀밥 (1.2.3)" -> "쌀밥")
            clean_item = re.sub(r"\s*\([^)]*\)", "", item).strip()
            processed_items.append(clean_item)
        else:
            processed_items.append(item)
            
    cal_info = meal_data.get("CAL_INFO", "정보 없음")

    # [큰 숫자 카드] 요약 지표 (메뉴 가짓수 & 칼로리)
    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric(label="📋 총 메뉴 수", value=f"{len(processed_items)}개")
    with metric_col2:
        st.metric(label="🔥 총 칼로리", value=cal_info)

    st.subheader(f"🍱 {selected_date.strftime('%Y년 %m월 %d일')} 중식 식단")

    # [메뉴 카드 배치] 여러 개 카드로 나란히 시각화
    num_cols = min(4, len(processed_items)) if processed_items else 1
    cols = st.columns(num_cols)

    for idx, item_name in enumerate(processed_items):
        col_idx = idx % num_cols
        with cols[col_idx]:
            with st.container(border=True):
                st.markdown(f"**{item_name}**")

else:
    # 급식이 없거나 조회 실패 시 안내 문구
    st.info("🚫 급식이 없는 날입니다. (주말, 공휴일 또는 방학)")
