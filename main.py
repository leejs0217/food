from datetime import datetime, timedelta
import re
import requests
import streamlit as st
import pytz
import pandas as pd

# 송탄고등학교 고정 정보
ATPT_OFCDC_SC_CODE = "J10"      # 경기도교육청
SD_SCHUL_CODE = "7530480"       # 송탄고등학교
SCHOOL_NAME = "송탄고등학교"

# 페이지 설정
st.set_page_config(
    page_title="최근 한달간 가장 적게 나온 메뉴",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 최근 한달간 가장 적게 나온 메뉴")
st.caption(f"🏫 분석 대상: **{SCHOOL_NAME}** (최근 30일 급식 데이터 기준)")

# 1. 한국 표준시(KST) 기준 날짜 범위 설정 (오늘부터 과거 30일)
tz_kst = pytz.timezone("Asia/Seoul")
today = datetime.now(tz_kst).date()
one_month_ago = today - timedelta(days=30)

# 2. 최근 한 달간 급식 데이터 수집 함수
@st.cache_data(ttl=3600)
def fetch_month_meals(start_date, end_date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": start_date.strftime("%Y%m%d"),
        "MLSV_TO_YMD": end_date.strftime("%Y%m%d"),
        "pSize": 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
        return []
    except Exception:
        return []

# 데이터 로딩 상태 표시
with st.spinner("송탄고등학교의 최근 한 달간 급식 데이터를 불러오는 중입니다..."):
    meals_row = fetch_month_meals(one_month_ago, today)

if meals_row:
    # 3. 메뉴 데이터 정제
    menu_records = []
    
    for row in meals_row:
        date_str = row.get("MLSV_YMD", "")
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        raw_ddish = row.get("DDISH_NM", "")
        
        # <br/> 태그로 메뉴 구분
        items = re.split(r"<br\s*/?>", raw_ddish)
        for item in items:
            item = item.strip()
            if not item:
                continue
            # 알레르기 번호 제거 (예: "쌀밥 (1.2.3)" -> "쌀밥")
            clean_name = re.sub(r"\s*\([^)]*\)", "", item).strip()
            if clean_name:
                menu_records.append({"메뉴명": clean_name, "제공일자": formatted_date})

    df = pd.DataFrame(menu_records)
    
    # 메뉴별 등장 횟수 및 날짜 목록 집계
    summary = df.groupby("메뉴명").agg(
        출현횟수=("제공일자", "count"),
        제공일자_목록=("제공일자", lambda x: ", ".join(sorted(set(x))))
    ).reset_index()

    # 적게 나온 순서(오름차순) 정렬
    summary_sorted = summary.sort_values(by="출현횟수", ascending=True)

    # 상단 요약 카드
    total_days = len(set(row.get("MLSV_YMD") for row in meals_row))
    total_menus = len(summary)
    min_count = summary_sorted["출현횟수"].min()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📅 수집된 급식 일수", f"{total_days}일")
    with col2:
        st.metric("🍱 총 메뉴 종류", f"{total_menus}가지")
    with col3:
        st.metric("⭐ 최소 등장 횟수", f"{min_count}회")

    st.divider()

    # 4. 결과 출력: 가장 적게 나온 메뉴 TOP 10
    st.subheader("🥇 최근 한달간 가장 적게 나온 메뉴 TOP 10")
    st.write("최근 30일 동안 단 1회만 제공된 희귀 메뉴들입니다.")

    top_least = summary_sorted.head(10)

    cols = st.columns(2)
    for idx, (_, row) in enumerate(top_least.iterrows()):
        col_idx = idx % 2
        with cols[col_idx]:
            with st.container(border=True):
                st.markdown(f"### **{row['메뉴명']}**")
                st.markdown(f"* **제공 횟수:** `{row['출현횟수']}회`")
                st.markdown(f"* **제공 날짜:** {row['제공일자_목록']}")

    st.divider()

    # 전체 데이터 표
    with st.expander("📊 전체 메뉴별 등장 횟수 데이터 보기"):
        st.dataframe(summary_sorted, use_container_width=True)

else:
    st.warning("최근 한 달간의 급식 데이터를 불러올 수 없습니다. (방학 기간이거나 급식 데이터가 없는 경우)")
