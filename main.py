import requests
from datetime import datetime

# 1. API 기본 설정
NEIS_API_KEY = "f56c2783d18b4089843754fcbf477e6c"  # 나이스 Open API 키
ATPT_OFCDC_SC_CODE = "J10"  # 경기도교육청 코드

# 2. 학교 정보 (학교명: 행정표준코드)
SCHOOLS = {
    "효명고등학교": "7530182",
    "이충고등학교": "7530863",
    "송탄고등학교": "7530170"
}

def get_today_meal():
    # 오늘 날짜 구하기 (YYYYMMDD)
    today = datetime.now().strftime("%Y%m%d")
    today_formatted = datetime.now().strftime("%Y년 %m월 %d일")
    
    print(f"==========================================")
    print(f" 🍱 오늘 나온 급식은? ({today_formatted})")
    print(f"==========================================\n")

    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"

    for school_name, school_code in SCHOOLS.items():
        params = {
            "KEY": NEIS_API_KEY,
            "Type": "json",
            "pIndex": 1,
            "pSize": 100,
            "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
            "SD_SCHUL_CODE": school_code,
            "MLSV_YMD": today
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            print(f"[{school_name}]")

            if "mealServiceDietInfo" in data:
                row_list = data["mealServiceDietInfo"][1]["row"]
                for meal in row_list:
                    meal_type = meal.get("MMEAL_SC_NM", "급식")
                    dish_name = meal.get("DDISH_NM", "메뉴 정보 없음")
                    
                    # 줄바꿈 및 깔끔한 출력 정제
                    cleaned_dishes = dish_name.replace("<br/>", "\n   • ").replace("<br>", "\n   • ")
                    
                    print(f" ▶ {meal_type}")
                    print(f"   • {cleaned_dishes}\n")
            else:
                msg = data.get("RESULT", {}).get("MESSAGE", "급식 정보가 없거나 휴업일입니다.")
                print(f"   {msg}\n")

        except Exception as e:
            print(f"   오류 발생: {e}\n")

if __name__ == "__main__":
    get_today_meal()
