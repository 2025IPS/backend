from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
import random

router = APIRouter()

# ------------------------------
# 데이터 로드 및 정제
# ------------------------------

menu_df = pd.read_csv("./data/final_menu_data.csv", on_bad_lines='skip')

# 공백 제거 및 타입 정제
menu_df["region"] = menu_df["region"].str.strip()
menu_df["menu_price"] = menu_df["menu_price"].apply(lambda x: int(str(x).replace(",", "").strip()))
menu_df["allergy"] = menu_df["allergy"].apply(lambda x: [] if pd.isna(x) else [a.strip() for a in str(x).split(",")])

# ------------------------------
# 요청 데이터 모델
# ------------------------------
class MenuRecommendInput(BaseModel):
    region: str
    alone: str
    budget: str
    drink: str
    hunger: str
    allergies: list[str] = []
    diseases: list[str] = []

# ------------------------------
# 응답 없음 처리
# ------------------------------
def no_menu_response(msg):
    return {
        "menu_name": msg,
        "place_name": "-",
        "menu_price": "-",
        "distance": "-",
        "address": "-",
        "url": "-",
        "nutrient": {}
    }

# ------------------------------
# 추천 API
# ------------------------------
@router.post("/menu-recommend")
def recommend_menu(input_data: MenuRecommendInput):
    try:
        # STEP 1. 지역 필터
        filtered = menu_df[menu_df["region"] == input_data.region]

        if filtered.empty:
            return no_menu_response("해당 지역에 메뉴가 없습니다")

        # STEP 2. 예산 필터
        price_min, price_max = 0, 999999
        if "1만원 미만" in input_data.budget:
            price_max = 10000
        elif "1~2만원" in input_data.budget:
            price_min, price_max = 10000, 20000
        elif "2~3만원" in input_data.budget:
            price_min, price_max = 20000, 30000
        elif "3~4만원" in input_data.budget:
            price_min, price_max = 30000, 40000
        elif "4만원 이상" in input_data.budget:
            price_min = 40000

        filtered = filtered[(filtered["menu_price"] >= price_min) & (filtered["menu_price"] <= price_max)]
        if filtered.empty:
            return no_menu_response("예산에 맞는 메뉴가 없습니다")

        # STEP 3. 알러지 필터
        filtered = filtered[filtered["allergy"].apply(lambda x: len(set(x) & set(input_data.allergies)) == 0)]
        if filtered.empty:
            return no_menu_response("알러지에 맞는 메뉴가 없습니다")

        # STEP 4. 후보 메뉴 가중치 부여
        candidates = []
        for _, row in filtered.iterrows():
            weight = 1
            if input_data.alone == "혼자" and row["menu_price"] <= 10000:
                weight += 1
            if input_data.drink != "없음" and "탕수육" in row["menu_name"]:
                weight += 1
            if input_data.hunger == "많이" and row["menu_price"] >= 12000:
                weight += 1
            candidates += [row] * weight

        if not candidates:
            return no_menu_response("조건에 맞는 메뉴가 없습니다")

        # STEP 5. 추천 결과 반환
        selected = random.choice(candidates)

        return {
            "menu_name": selected["menu_name"],
            "place_name": selected["place_name"],
            "menu_price": selected["menu_price"],
            "distance": "도보 10분 이내",
            "address": selected["address"],
            "url": selected["url"],
            "nutrient": {}  # 영양 정보는 아직 없음
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return no_menu_response("서버 오류: " + str(e))
