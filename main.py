import requests
import json
from datetime import datetime

# 1. API 설정
NEIS_API_KEY = "f56c2783d18b4089843754fcbf477e6c"  # 발급받은 1년치 API 인증키
ATPT_OFCDC_SC_CODE = "J10"  # 경기도교육청 교육청코드

# 2. 학교 정보 정의 (학교명: 행정표준코드)
SCHOOLS = {
    "효명고등학교": "7530182",
    "이충고등학교": "7530863",
    "송탄고등학교": "7530170"
}

def get_meal_info(school_name, school_code, date_str):
    """
    지정한 학교와 날짜의 급식 정보를 조회합니다.
    :param school_name: 학교 이름
    :param school_code: 표준학교코드
    :param date_str: YYYYMMDD 형식 날짜 (예: '20260930')
    """
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    
    params = {
        "KEY": NEIS_API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": school_code,
        "MLSV_YMD": date_str
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        print(f"\n==========================================")
        print(f" 🍱 {school_name} 급식 정보 ({date_str})")
        print(f"==========================================")

        # 결과 검증 및 데이터 출력
        if "mealServiceDietInfo" in data:
            row_list = data["mealServiceDietInfo"][1]["row"]
            for meal in row_list:
                meal_type = meal.get("MMEAL_SC_NM", "급식") # 중식/석식 구분
                dish_name = meal.get("DDISH_NM", "메뉴 정보 없음")
                
                # 원재료 알레르기 표시 번호 정제 (예: '쌀밥<br/>' -> '쌀밥')
                cleaned_dishes = dish_name.replace("<br/>", "\n   - ").replace("<br>", "\n   - ")
                
                print(f"[{meal_type}]")
                print(f"   - {cleaned_dishes}\n")
        else:
            result_msg = data.get("RESULT", {}).get("MESSAGE", "급식 정보가 없거나 휴일입니다.")
            print(f"   {result_msg}")

    except Exception as e:
        print(f"   API 요청 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    # 오늘 날짜 (YYYYMMDD)
    target_date = datetime.now().strftime("%Y%m%d")
    
    print(f"🔍 평택 지역 3개 고등학교 급식 정보 조회를 시작합니다.")
    
    # 3개 학교 급식 반복 조회
    for name, code in SCHOOLS.items():
        get_meal_info(name, code, target_date)
