from collections import Counter
import re
import requests

# 탐색할 디저트 관련 대표 키워드 목록 정의
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
    "파르페",
    "젤리",
    "과일",
    "사과",
    "바나나",
    "포도",
    "딸기",
    "수박",
    "참외",
    "메론",
    "귤",
    "한라봉",
]


def analyze_dessert_by_month(office_code, school_code, from_ymd, to_ymd, api_key=None):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd,
        "pSize": 1000,
    }
    if api_key:
        params["KEY"] = api_key

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "mealServiceDietInfo" not in data:
            return None

        rows = data["mealServiceDietInfo"][1]["row"]
        monthly_dessert_counts = Counter()

        for row in rows:
            ymd = row.get("MLSV_YMD", "")  # 예: "20250915"
            if len(ymd) >= 6:
                year_month = ymd[:6]  # "202509" (연월 추출)

            ddish_nm = row.get("DDISH_NM", "")
            # 메뉴명 내 알레르기 번호 및 원산지 표기 등 제거
            clean_menu = re.sub(r"\([0-9\.]+\)", "", ddish_nm)

            # 디저트 키워드 포함 여부 검사
            dessert_count = 0
            for menu_item in clean_menu.split("<br/>"):
                for kw in DESSERT_KEYWORDS:
                    if kw in menu_item:
                        dessert_count += 1
                        break

            if dessert_count > 0:
                monthly_dessert_counts[year_month] += dessert_count

        return monthly_dessert_counts

    except Exception as e:
        print(f"오류 발생: {e}")
        return None
