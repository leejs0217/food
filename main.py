from collections import Counter, defaultdict
from datetime import datetime
import re
import pandas as pd
import pytz
import requests
import streamlit as st

st.set_page_config(
    page_title="평택 5개 고교 디저트 월별 비교 분석",
    page_icon="🍰",
    layout="wide",
)

# --- 1. 학교 목록 설정 ---
TARGET_SCHOOLS = [
    {"name": "송탄고등학교", "short": "송탄고"},
    {"name": "은혜고등학교", "short": "은혜고"},
    {"name": "효명고등학교", "short": "효명고"},
    {"name": "이충고등학교", "short": "이충고"},
    {"name": "태광고등학교", "short": "태광고"},
]

DESSERT_KEYWORDS = [
    "케이크",
    "케익",
    "푸딩",
    "아이스크림",
    "와플",
    "마카롱",
    "에이드",
    "주스",
    "쥬스",
    "요거트",
    "요구르트",
    "빵",
    "쿠키",
    "타르트",
    "파이",
    "슈",
    "도넛",
    "젤리",
    "과일",
    "사과",
    "바나나",
    "포도",
    "딸기",
    "수박",
    "참외",
    "멜론",
    "메론",
    "귤",
    "한라봉",
    "에그타르트",
    "슈크림",
    "스무디",
    "라떼",
]


def get_api_key():
    try:
        return st.secrets.get("NEIS_API_KEY", None)
    except Exception:
        return None


@st.cache_data(ttl=86400)
def fetch_school_codes():
    url = "https://open.neis.go.kr/hub/schoolInfo"
    api_key = get_api_key()
    school_info_map = {}

    for sch in TARGET_SCHOOLS:
        params = {"Type": "json", "SCHUL_NM": sch["name"]}
        if api_key:
            params["KEY"] = api_key

        try:
            res = requests.get(url, params=params, timeout=5).json()
            if "schoolInfo" in res:
                row = res["schoolInfo"][1]["row"][0]
                school_info_map[sch["short"]] = {
                    "office_code": row["ATPT_OFCDC_SC_CODE"],
                    "school_code": row["SD_SCHUL_CODE"],
                }
        except Exception:
            continue
    return school_info_map


@st.cache_data(ttl=3600)
def fetch_and_analyze_desserts(start_ymd, end_ymd):
    school_map = fetch_school_codes()
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    api_key = get_api_key()

    records = []
    monthly_menu_detail = defaultdict(lambda: defaultdict(list))

    for sch_short, info in school_map.items():
        params = {
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": info["office_code"],
            "SD_SCHUL_CODE": info["school_code"],
            "MMEAL_SC_CODE": "2",
            "MLSV_FROM_YMD": start_ymd,
            "MLSV_TO_YMD": end_ymd,
            "pSize": 1000,
        }
        if api_key:
            params["KEY"] = api_key

        try:
            res = requests.get(url, params=params, timeout=10).json()
            if "mealServiceDietInfo" not in res:
                continue

            rows = res["mealServiceDietInfo"][1]["row"]
            for row in rows:
                ymd = row.get("MLSV_YMD", "")
                if len(ymd) < 6:
                    continue

                month_str = f"{int(ymd[4:6])}월"
                ddish_nm = row.get("DDISH_NM", "")
                clean_menu = re.sub(r"\([0-9\.]+\)", "", ddish_nm)
                items = clean_menu.split("<br/>")

                for item in items:
                    item_clean = item.strip()
                    for kw in DESSERT_KEYWORDS:
                        if kw in item_clean:
                            records.append(
                                {
                                    "학교": sch_short,
                                    "날짜": ymd,
                                    "월": month_str,
                                    "디저트명": item_clean,
                                }
                            )
                            monthly_menu_detail[sch_short][month_str].append(
                                item_clean
                            )
                            break
        except Exception:
            continue

    return pd.DataFrame(records), monthly_menu_detail


# --- UI ---
st.title("📊 각 학교별로 디저트가 가장 많이 나온 달은?")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("조회 시작일", value=datetime(2025, 3, 1).date())
with col2:
    end_date = st.date_input("조회 종료일", value=datetime(2026, 2, 28).date())

start_ymd = start_date.strftime("%Y%m%d")
end_ymd = end_date.strftime("%Y%m%d")

with st.spinner("급식 데이터를 분석 중입니다..."):
    df, monthly_detail = fetch_and_analyze_desserts(start_ymd, end_ymd)

if df.empty:
    st.warning("데이터가 없거나 급식 정보를 불러올 수 없습니다.")
else:
    months_order = [f"{m}월" for m in range(1, 13)]

    # 요약 카드
    st.divider()
    st.subheader("🏆 학교별 디저트가 가장 많이 나온 달")

    summary_cols = st.columns(5)
    schools = ["송탄고", "은혜고", "효명고", "이충고", "태광고"]

    for idx, sch in enumerate(schools):
        sch_df = df[df["학교"] == sch]
        with summary_cols[idx]:
            if not sch_df.empty:
                counts = sch_df["월"].value_counts()
                top_month = counts.index[0]
                top_count = counts.iloc[0]
                top_item = sch_df["디저트명"].mode()
                top_item_str = (
                    top_item.iloc[0] if not top_item.empty else "정보 없음"
                )

                st.metric(
                    label=f"🏫 {sch}",
                    value=f"{top_month}",
                    delta=f"{top_count}회 제공",
                )
                st.caption(f"**대표 후식**: {top_item_str}")
            else:
                st.metric(label=f"🏫 {sch}", value="데이터 없음")

    # 기본 Streamlit 바 차트
    st.divider()
    st.subheader("📈 학교별 월별 디저트 제공 건수")

    pv_df = (
        df.groupby(["월", "학교"]).size().unstack(fill_value=0).reindex(months_order).dropna(how="all")
    )
    st.bar_chart(pv_df)

    # 상세 정보
    st.divider()
    st.subheader("🍰 학교별 / 달별 최다 제공 후식 세부사항")

    selected_sch = st.selectbox("학교 선택", schools)
    sch_detail_df = df[df["학교"] == selected_sch]

    if not sch_detail_df.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"#### 🍩 {selected_sch} 인기 후식 Top 10")
            item_counts = (
                sch_detail_df["디저트명"]
                .value_counts()
                .head(10)
                .reset_index(name="제공 횟수")
            )
            st.dataframe(item_counts, use_container_width=True)

        with col_b:
            st.markdown(f"#### 📅 {selected_sch} 월별 후식 목록")
            avail_months = [
                m for m in months_order if m in sch_detail_df["월"].unique()
            ]
            if avail_months:
                selected_m = st.selectbox("달 선택", avail_months)
                m_items = monthly_detail[selected_sch][selected_m]
                m_counts = Counter(m_items).most_common()
                st.dataframe(
                    pd.DataFrame(m_counts, columns=["후식 메뉴명", "제공 횟수"]),
                    use_container_width=True,
                )
