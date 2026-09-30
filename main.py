from collections import Counter
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

# --- 1. 학교 목록 및 디저트 키워드 설정 ---
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
    "우유",
    "초코",
]


def get_api_key():
    try:
        return st.secrets.get("NEIS_API_KEY", None)
    except Exception:
        return None


# --- 2. 학교 코드 가져오기 ---
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


# --- 3. 3월~12월 급식 데이터 수집 (안정적 월별 분할 요청) ---
@st.cache_data(ttl=3600)
def fetch_and_analyze_desserts(year):
    school_map = fetch_school_codes()
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    api_key = get_api_key()

    records = []
    monthly_menu_detail = {}

    # 3월부터 12월까지 반복 수집
    months = list(range(3, 13))

    for sch_short, info in school_map.items():
        if sch_short not in monthly_menu_detail:
            monthly_menu_detail[sch_short] = {}

        for m in months:
            month_str = f"{m}월"
            if month_str not in monthly_menu_detail[sch_short]:
                monthly_menu_detail[sch_short][month_str] = []

            # 해당 월의 시작일과 종료일 계산 (예: 20250301~20250331)
            start_ymd = f"{year}{m:02d}01"
            # 12월은 31일, 4,6,9,11월은 30일, 나머지 31일
            end_day = 30 if m in [4, 6, 9, 11] else 31
            end_ymd = f"{year}{m:02d}{end_day}"

            params = {
                "Type": "json",
                "ATPT_OFCDC_SC_CODE": info["office_code"],
                "SD_SCHUL_CODE": info["school_code"],
                "MMEAL_SC_CODE": "2",
                "MLSV_FROM_YMD": start_ymd,
                "MLSV_TO_YMD": end_ymd,
                "pSize": 100,
            }
            if api_key:
                params["KEY"] = api_key

            try:
                res = requests.get(url, params=params, timeout=5).json()
                if "mealServiceDietInfo" not in res:
                    continue

                rows = res["mealServiceDietInfo"][1]["row"]
                for row in rows:
                    ymd = row.get("MLSV_YMD", "")
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
                                        "월_숫자": m,
                                        "디저트명": item_clean,
                                    }
                                )
                                monthly_menu_detail[sch_short][
                                    month_str
                                ].append(item_clean)
                                break
            except Exception:
                continue

    return pd.DataFrame(records), monthly_menu_detail


# --- UI 화면 구성 ---
st.title("📊 평택 5개 고교 디저트 월별(3월~12월) 비교 분석")

# 학년도 연도 선택
selected_year = st.selectbox(
    "조회할 학년도(연도)를 선택하세요", [2025, 2024, 2026], index=0
)

with st.spinner(
    f"{selected_year}년 3월부터 12월까지의 급식 데이터를 수집 중입니다..."
):
    df, monthly_detail = fetch_and_analyze_desserts(selected_year)

if df.empty:
    st.warning("선택한 연도에 급식 데이터가 없거나 수집하지 못했습니다.")
else:
    # 3월 ~ 12월 정렬 순서
    months_order = [f"{m}월" for m in range(3, 13)]

    # 1. 메인 질문: 학교별로 디저트가 가장 많이 나온 달
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
                    delta=f"총 {top_count}회 제공",
                )
                st.caption(f"**최다 후식**: {top_item_str}")
            else:
                st.metric(label=f"🏫 {sch}", value="데이터 없음")

    # 2. 학교별 월별 제공 건수 비교 차트
    st.divider()
    st.subheader("📈 학교별 월별(3월~12월) 디저트 제공 건수")

    pv_df = (
        df.groupby(["월", "학교"])
        .size()
        .unstack(fill_value=0)
        .reindex(months_order)
        .fillna(0)
    )
    st.bar_chart(pv_df)

    # 3. 추가 기능: 특정 달을 지정해서 5개 학교 비교하기
    st.divider()
    st.subheader("🔍 특정 달(월) 기준 5개 학교 디저트 제공량 비교")

    selected_compare_month = st.selectbox(
        "비교할 달을 선택하세요",
        months_order,
        index=2,  # 기본값 5월
    )

    m_comp_df = df[df["월"] == selected_compare_month]

    if not m_comp_df.empty:
        comp_counts = (
            m_comp_df.groupby("학교")
            .size()
            .reindex(schools)
            .fillna(0)
            .astype(int)
            .reset_index(name="디저트 제공 횟수")
        )

        col_c1, col_c2 = st.columns([1, 1])
        with col_c1:
            st.markdown(
                f"##### 📊 {selected_compare_month} 학교별 디저트 제공 횟수"
            )
            st.dataframe(comp_counts, use_container_width=True)
        with col_b_chart := col_c2:
            st.markdown(
                f"##### 🍩 {selected_compare_month} 학교별 최다 디저트 메뉴"
            )
            top_per_school = []
            for sch in schools:
                sch_m_df = m_comp_df[m_comp_df["학교"] == sch]
                if not sch_m_df.empty:
                    most_common = sch_m_df["디저트명"].value_counts().idxmax()
                    cnt = sch_m_df["디저트명"].value_counts().max()
                    top_per_school.append(
                        {
                            "학교": sch,
                            "가장 자주 나온 디저트": most_common,
                            "횟수": f"{cnt}회",
                        }
                    )
                else:
                    top_per_school.append(
                        {
                            "학교": sch,
                            "가장 자주 나온 디저트": "없음",
                            "횟수": "0회",
                        }
                    )
            st.dataframe(
                pd.DataFrame(top_per_school), use_container_width=True
            )

    # 4. 학교별 / 달별(3월~12월) 상세 후식 세부사항
    st.divider()
    st.subheader("🍰 학교별 / 달별 최다 제공 후식 세부사항")

    selected_sch = st.selectbox("학교 선택", schools)
    sch_detail_df = df[df["학교"] == selected_sch]

    if not sch_detail_df.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"#### 🍩 {selected_sch} 전체 인기 후식 Top 10")
            item_counts = (
                sch_detail_df["디저트명"]
                .value_counts()
                .head(10)
                .reset_index(name="제공 횟수")
            )
            st.dataframe(item_counts, use_container_width=True)

        with col_b:
            st.markdown(f"#### 📅 {selected_sch} 월별 후식 목록")

            # 3월부터 12월까지 전체 달이 드롭다운에 표시됨
            selected_m = st.selectbox("달 선택", months_order)

            m_items = monthly_detail.get(selected_sch, {}).get(selected_m, [])
            if m_items:
                m_counts = Counter(m_items).most_common()
                st.dataframe(
                    pd.DataFrame(m_counts, columns=["후식 메뉴명", "제공 횟수"]),
                    use_container_width=True,
                )
            else:
                st.info(f"{selected_sch}의 {selected_m}에는 디저트 데이터가 없습니다.")
