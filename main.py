import re
from datetime import datetime
import pytz
import requests
import streamlit as st

st.set_page_config(page_title="학교 급식 조회 서비스", page_icon="🏫")


# 한국 시간(KST) 기준 오늘 날짜 구하기
def get_today_kr():
    kr_tz = pytz.timezone("Asia/Seoul")
    return datetime.now(kr_tz).date()


# Streamlit Secrets에서 API 인증키 가져오기 (없으면 None)
def get_api_key():
    try:
        return st.secrets.get("NEIS_API_KEY", None)
    except Exception:
        return None


# 축약어 확장 처리
def expand_school_name(name):
    name_expanded = name
    replacements = [
        ("여고", "여자고등학교"),
        ("남고", "남자고등학교"),
        ("여중", "여자중학교"),
        ("남중", "남자중학교"),
        ("고", "고등학교"),
        ("중", "중학교"),
        ("초", "초등학교"),
    ]

    for short, full in replacements:
        if name_expanded.endswith(short):
            name_expanded = name_expanded[: -len(short)] + full
            break

    return name_expanded


# 1. 학교 검색 API 호출
def search_school(school_name):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    api_key = get_api_key()

    params = {"Type": "json", "SCHUL_NM": school_name}
    if api_key:
        params["KEY"] = api_key

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if "schoolInfo" in data:
            return data["schoolInfo"][1]["row"]
        return []
    except Exception:
        return []


# 2. 급식 정보 API 호출
def get_meal_info(office_code, school_code, ymd_str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    api_key = get_api_key()

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": ymd_str,
        "MLSV_TO_YMD": ymd_str,
        "pSize": 1000,
    }
    if api_key:
        params["KEY"] = api_key

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            if rows:
                return rows[0]
        return None
    except Exception:
        return None


# UI 화면 구성
st.title("🏫 학교 급식(중식) 조회")

# 학교 입력 및 검색
input_name = st.text_input(
    "학교 이름을 입력하세요", placeholder="예: 수도여고, 서울고"
)
selected_school = None

if input_name:
    search_keyword = input_name.strip()
    results = search_school(search_keyword)

    # 검색 결과가 없으면 줄임말 확장 후 재검색
    if not results:
        expanded_keyword = expand_school_name(search_keyword)
        if expanded_keyword != search_keyword:
            st.info(
                f"'{search_keyword}' 검색 결과가 없어 '{expanded_keyword}'(으)로 다시 검색합니다."
            )
            results = search_school(expanded_keyword)

    if results:
        options = {
            f"{row['SCHUL_NM']} ({row['LCTN_SC_NM']})": row for row in results
        }
        selected_label = st.selectbox(
            "학교를 선택하세요", options=list(options.keys())
        )
        selected_school = options[selected_label]
    else:
        st.warning("해당 이름의 학교를 찾을 수 없습니다. 이름을 확인해 주세요.")

# 날짜 선택 및 급식 결과 출력
if selected_school:
    st.divider()
    st.subheader(
        f"📍 {selected_school['SCHUL_NM']} ({selected_school['LCTN_SC_NM']})"
    )

    today = get_today_kr()
    selected_date = st.date_input("날짜를 선택하세요", value=today)
    ymd_str = selected_date.strftime("%Y%m%d")

    meal_data = get_meal_info(
        selected_school["ATPT_OFCDC_SC_CODE"],
        selected_school["SD_SCHUL_CODE"],
        ymd_str,
    )

    if meal_data:
        st.markdown(f"### 🍽️ {selected_date.strftime('%Y년 %m월 %d일')} 중식")

        cal_info = meal_data.get("CAL_INFO", "정보 없음")
        st.caption(f"🔥 칼로리: {cal_info}")

        ddish_nm = meal_data.get("DDISH_NM", "")
        clean_menu = re.sub(r"<br\s*/?>", "\n", ddish_nm)

        st.markdown("**[메뉴 및 알레르기 번호]**")
        st.text(clean_menu)
    else:
        st.info("선택하신 날짜에는 급식 정보가 없습니다.")
