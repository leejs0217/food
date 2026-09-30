
# 페이지 설정 및 제목
st.set_page_config(page_title="우리 학교에서 가장 적게 나온 메뉴는?", page_icon="🍱")
st.title("우리 학교에서 가장 적게 나온 메뉴는?")


# 1. 학교 정보 검색 함수
def search_school(keyword):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": keyword}

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        # 데이터 존재 여부 확인
        if "schoolInfo" in data:
            return data["schoolInfo"][1]["row"]
        return []
    except Exception:
        return []


# 줄여 쓴 학교명 자동 보정 검색 함수
def get_school_list(query):
    query = query.strip()
    if not query:
        return []

    # 1차 검색
    results = search_school(query)

    # 검색 결과가 없고 대체 규칙 적용 가능한 경우 2차 검색
    if not results:
        expanded_query = query
        # '여고' -> '여자고등학교', '고' -> '고등학교' (순서 중요)
        if "여고" in expanded_query:
            expanded_query = expanded_query.replace("여고", "여자고등학교")
        elif expanded_query.endswith("고"):
            expanded_query = expanded_query[:-1] + "고등학교"
        elif "고" in expanded_query and not expanded_query.endswith("고등학교"):
            expanded_query = expanded_query.replace("고", "고등학교")

        if expanded_query != query:
            results = search_school(expanded_query)

    return results


# 2. 급식 정보 조회 함수
def get_meal_info(atpt_code, school_code, date_str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": date_str,
        "MLSV_TO_YMD": date_str,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if "mealServiceDietInfo" in data:
            row = data["mealServiceDietInfo"][1]["row"][0]
            return row
        return None
    except Exception:
        return None


# --- UI 구성 ---

# 학교 이름 입력
school_name_input = st.text_input(
    "학교 이름을 입력하세요", placeholder="예: 수도여고, 서울고, 신사중"
)

selected_school = None

if school_name_input:
    schools = get_school_list(school_name_input)

    if not schools:
        st.warning("해당 이름의 학교를 찾을 수 없습니다. 검색어를 확인해 주세요.")
    else:
        # 셀렉트박스에 표시할 레이블 생성 (학교명 + 지역)
        options = {
            f"{s['SCHUL_NM']} ({s['LCTN_SC_NM']})": s for s in schools
        }
        selected_option = st.selectbox(
            "학교를 선택하세요", list(options.keys())
        )
        selected_school = options[selected_option]

st.divider()

# 날짜 선택 (기본값: 한국 표준시 KST 기준 오늘)
tz_kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.now(tz_kst).date()

selected_date = st.date_input("날짜를 선택하세요", value=today_kst)

# 급식 조회 및 출력
if selected_school:
    date_str = selected_date.strftime("%Y%m%d")

    meal_data = get_meal_info(
        selected_school["ATPT_OFCDC_SC_CODE"],
        selected_school["SD_SCHUL_CODE"],
        date_str,
    )

    st.subheader(
        f"🍱 {selected_school['SCHUL_NM']} ({selected_date.strftime('%Y년 %m월 %d일')}) 중식"
    )

    if meal_data:
        # DDISH_NM 내 <br/> 태그를 줄바꿈으로 변경
        raw_menu = meal_data["DDISH_NM"]
        clean_menu = raw_menu.replace("<br/>", "\n").replace("<br>", "\n")

        st.markdown("### 식단 메뉴")
        st.text(clean_menu)

        # 칼로리 정보 표기
        cal_info = meal_data.get("CAL_INFO", "정보 없음")
        st.info(f"🔥 **총 칼로리:** {cal_info}")
    else:
        st.info("해당 날짜에 조회된 급식 정보가 없습니다. (휴교일 또는 방학)")
else:
    st.info("학교를 먼저 검색하고 선택해 주세요.")
