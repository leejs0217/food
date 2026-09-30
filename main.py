from collections import Counter, defaultdict
from datetime import datetime
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
import requests
import streamlit as st

st.set_page_config(
    page_title="평택 5개 고교 디저트 월별 비교 분석",
    page_icon="🍰",
    layout="wide",
)

# --- 1. 기본 설정 및 학교 목록 ---
TARGET_SCHOOLS = [
    {"name": "송탄고등학교", "short": "송탄고"},
    {"name": "은혜고등학교", "short": "은혜고"},
    {"name": "효명고등학교", "short": "효명고"},
    {"name": "이충고등학교", "short": "이충고"},
    {"name": "태광고등학교", "short": "태광고"},
]

# 디저트 판별 키워드 및 대표 카테고리
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


# --- 2. NEIS API 학교 코드 자동 조회 ---
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
                    "fullname": row["SCHUL_NM"],
                    "office_code": row["ATPT_OFCDC_SC_CODE"],
                    "school_code": row["SD_SCHUL_CODE"],
                    "location": row["LCTN_SC_NM"],
                }
        except Exception:
            continue
    return school_info_map


# --- 3. 연간 급식 데이터 수집 및 디저트 분석 ---
@st.cache_data(ttl=3600)
def fetch_and_analyze_desserts(start_ymd, end_ymd):
    school_map = fetch_school_codes()
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    api_key = get_api_key()

    records = []
    monthly_menu_detail = defaultdict(
        lambda: defaultdict(list)
    )  # [school][month] -> list of dessert names

    for sch_short, info in school_map.items():
        params = {
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": info["office_code"],
            "SD_SCHUL_CODE": info["school_code"],
            "MMEAL_SC_CODE": "2",  # 중식
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

                year_month = f"{ymd[:4]}년 {int(ymd[4:6])}월"
                month_str = f"{int(ymd[4:6])}월"

                ddish_nm = row.get("DDISH_NM", "")
                # 알레르기 번호 제거
                clean_menu = re.sub(r"\([0-9\.]+\)", "", ddish_nm)
                items = clean_menu.split("<br/>")

                for item in items:
                    item_clean = item.strip()
                    # 디저트 키워드 검사
                    for kw in DESSERT_KEYWORDS:
                        if kw in item_clean:
                            records.append(
                                {
                                    "학교": sch_short,
                                    "날짜": ymd,
                                    "연월": year_month,
                                    "월": month_str,
                                    "디저트명": item_clean,
                                    "키워드": kw,
                                }
                            )
                            monthly_menu_detail[sch_short][month_str].append(
                                item_clean
                            )
                            break
        except Exception:
            continue

    df = pd.DataFrame(records)
    return df, monthly_menu_detail


# --- 4. UI 화면 구성 ---
st.title("📊 각 학교별로 디저트가 가장 많이 나온 달은?")
st.caption(
    "송탄고 · 은혜고 · 효명고 · 이충고 · 태광고 5개 학교의 NEIS 급식 데이터를 분석하여 월별 디저트 제공 현황을 비교합니다."
)

# 조회 기간 선택
col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input(
        "조회 시작일", value=datetime(2025, 3, 1).date()
    )
with col_date2:
    end_date = st.date_input("조회 종료일", value=datetime(2026, 2, 28).date())

start_ymd = start_date.strftime("%Y%m%d")
end_ymd = end_date.strftime("%Y%m%d")

with st.spinner("5개 학교의 급식 디저트 데이터를 수집하고 분석 중입니다..."):
    df, monthly_detail = fetch_and_analyze_desserts(start_ymd, end_ymd)

if df.empty:
    st.warning(
        "선택한 기간의 급식 디저트 데이터를 불러올 수 없거나 급식 정보가 없습니다."
    )
else:
    # 월 정렬을 위한 순서 리스트
    months_order = [f"{m}월" for m in range(1, 13)]

    # 학교별 / 월별 디저트 수량 피벗 테이블 생성
    pv_df = (
        df.groupby(["학교", "월"]).size().unstack(fill_value=0).reset_index()
    )
    # 월 순서대로 재정렬
    existing_months = [m for m in months_order if m in pv_df.columns]
    pv_df = pv_df[["학교"] + existing_months]

    # --- 핵심 답변: 학교별 최다 디저트 제공 월 요약 ---
    st.divider()
    st.subheader("🏆 학교별 디저트가 가장 많이 나온 달")

    summary_cols = st.columns(5)
    schools = ["송탄고", "은혜고", "효명고", "이충고", "태광고"]

    top_months_summary = []

    for idx, sch in enumerate(schools):
        sch_df = df[df["학교"] == sch]
        with summary_cols[idx]:
            if not sch_df.empty:
                counts = sch_df["월"].value_counts()
                top_month = counts.index[0]
                top_count = counts.iloc[0]

                # 가장 자주 나온 후식 종류 1위
                top_item = sch_df["디저트명"].mode()
                top_item_str = (
                    top_item.iloc[0] if not top_item.empty else "정보 없음"
                )

                st.metric(
                    label=f"🏫 {sch}",
                    value=f"{top_month}",
                    delta=f"총 {top_count}회 제공",
                )
                st.caption(f"**최다 후식**: {top_item_str}")

                top_months_summary.append(
                    {
                        "학교": sch,
                        "최다 제공 달": top_month,
                        "제공 횟수": f"{top_count}회",
                        "대표 인기 디저트": top_item_str,
                    }
                )
            else:
                st.metric(label=f"🏫 {sch}", value="데이터 없음")

    # --- 시각화 1: 학교별 월별 디저트 제공 횟수 비교 그래프 ---
    st.divider()
    st.subheader("📈 학교별 월별 디저트 제공 횟수 비교")

    # Grouped Bar Chart
    monthly_counts = (
        df.groupby(["학교", "월"]).size().reset_index(name="제공횟수")
    )

    fig_bar = px.bar(
        monthly_counts,
        x="월",
        y="제공횟수",
        color="학교",
        barmode="group",
        category_orders={"월": months_order},
        title="월별 디저트 제공 건수 비교 (학교별)",
        text_auto=True,
    )
    fig_bar.update_layout(xaxis_title="달 (월)", yaxis_title="디저트 제공 횟수")
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- 시각화 2: 디저트 분석 히트맵 (Heatmap) ---
    st.subheader("🔥 월별 디저트 집중도 히트맵")

    pv_heatmap = pv_df.set_index("학교")
    fig_heat = px.imshow(
        pv_heatmap,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Blues",
        labels=dict(x="달", y="학교", color="제공 횟수"),
        title="학교 x 월별 디저트 제공 횟수 분포",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # --- 상세 분석 탭: 각 달별 가장 많이 나온 후식 종류 ---
    st.divider()
    st.subheader("🍰 달별 / 학교별 가장 많이 나온 후식 종류 상세 보기")

    selected_sch = st.selectbox(
        "상세 내역을 확인할 학교를 선택하세요", schools
    )
    sch_detail_df = df[df["학교"] == selected_sch]

    if not sch_detail_df.empty:
        col_tab1, col_tab2 = st.columns([1, 1])

        with col_tab1:
            st.markdown(f"#### 🍩 {selected_sch} 가장 자주 제공된 디저트 Top 10")
            item_counts = (
                sch_detail_df["디저트명"]
                .value_counts()
                .head(10)
                .reset_index(name="횟수")
            )
            item_counts.columns = ["디저트 이름", "제공 횟수"]
            st.dataframe(item_counts, use_container_width=True)

        with col_tab2:
            st.markdown(f"#### 📅 {selected_sch} 월별 주요 디저트 목록")
            selected_m = st.selectbox(
                "달 선택",
                [
                    m
                    for m in months_order
                    if m in sch_detail_df["월"].unique()
                ],
            )
            m_items = monthly_detail[selected_sch][selected_m]

            if m_items:
                m_counts = Counter(m_items).most_common()
                m_df = pd.DataFrame(
                    m_counts, columns=["후식 메뉴명", "제공 횟수"]
                )
                st.dataframe(m_df, use_container_width=True)
            else:
                st.info("해당 달에는 집계된 디저트가 없습니다.")
