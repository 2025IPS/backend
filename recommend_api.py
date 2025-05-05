from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
import re
import random

router = APIRouter()

# ------------------------------
# 데이터 로드 + 정제 (시작 시 1회 실행)
# ------------------------------

# 메뉴 가격 데이터
menu_df = pd.read_csv("./data/menu_price.csv", on_bad_lines='skip')

# 메뉴 가격 정제 (가격이 없는 경우 제거)
def clean_price(value):
    try:
        value = str(value).strip().replace("-", "").replace(" ", "")
        if value == "" or pd.isna(value):
            return None
        return int(float(value))
    except:
        return None

menu_df["menu_price"] = menu_df["menu_price"].apply(clean_price)
menu_df = menu_df.dropna(subset=["menu_price"])
menu_df["menu_price"] = menu_df["menu_price"].astype(int)

# 영양소 데이터
nutrient_df = pd.read_csv("./data/menu_nutrient.csv", on_bad_lines='skip')

# 가게 데이터
place_df = pd.read_csv("./data/청파동식당.csv", on_bad_lines='skip')

# 주소 → 지역 추출
def extract_region(address):
    match = re.search(r"용산구\s([^\s]+)", str(address))
    if match:
        dong = match.group(1)
        if "청파" in dong:
            return "청파동"
        elif "갈월" in dong:
            return "갈월동"
        elif "효창" in dong:
            return "효창동"
        elif "남영" in dong:
            return "남영동"
        else:
            return dong
    return "기타"

place_df["region"] = place_df["address"].apply(extract_region)

# ------------------------------
# 요청 데이터 모델
# ------------------------------
class MenuRecommendInput(BaseModel):
    region: str
    alone: str
    budget: str
    drink: str
    hunger: str

# ------------------------------
# 추천 API
# ------------------------------
@router.post("/menu-recommend")
def recommend_menu(input_data: MenuRecommendInput):
    try:
        # STEP 1. 지역 기반 가게 필터
        target_places = place_df[place_df["region"] == input_data.region]

        if target_places.empty:
            return no_menu_response("해당 지역에 가게가 없습니다")

        # STEP 2. 가게명 → 메뉴 가격 테이블 join
        menus = menu_df[menu_df["place_name"].isin(target_places["name"])]

        if menus.empty:
            return no_menu_response("해당 지역 가게에 메뉴가 없습니다")

        # STEP 3. 예산 필터
        price_limit = 999999
        if "1만원 미만" in input_data.budget:
            price_limit = 10000
        elif "1~2만원" in input_data.budget:
            price_limit = 20000
        elif "2~3만원" in input_data.budget:
            price_limit = 30000
        elif "3~4만원" in input_data.budget:
            price_limit = 40000

        menus = menus[menus["menu_price"] <= price_limit]

        if menus.empty:
            return no_menu_response("예산에 맞는 메뉴가 없습니다")

        # STEP 4. 혼밥/음주/공복 (간단한 랜덤 가중치 필터 적용 예시 → 가볍게)
        candidates = menus.to_dict(orient="records")

        weighted_candidates = []
        for item in candidates:
            weight = 1  # 기본 가중치

            if input_data.alone == "혼자" and item["menu_price"] <= 10000:
                weight += 1
            if input_data.drink != "없음" and "탕수육" in item["menu_name"]:
                weight += 1
            if input_data.hunger == "많이" and item["menu_price"] >= 12000:
                weight += 1

            weighted_candidates += [item] * weight  # 가중치만큼 추가

        if not weighted_candidates:
            return no_menu_response("조건에 맞는 메뉴가 없습니다")

        # STEP 5. 최종 추천
        selected = random.choice(weighted_candidates)

        # 가게 정보 가져오기
        place = target_places[target_places["name"] == selected["place_name"]].iloc[0]

        # 영양 정보 가져오기 (선택적, 없으면 None)
        nutrient = nutrient_df[nutrient_df["name"] == selected["menu_name"]]
        if not nutrient.empty:
            nutrient_info = nutrient.iloc[0].to_dict()
        else:
            nutrient_info = {}

        return {
            "menu_name": selected["menu_name"],
            "place_name": selected["place_name"],
            "menu_price": selected["menu_price"],
            "distance": "도보 10분 이내",
            "address": place["address"],
            "url": place["url"],
            "nutrient": nutrient_info  # 추가 영양 정보
        }

    except Exception as e:
        import traceback
        traceback.print_exc()

        return no_menu_response(f"서버 오류: {str(e)}")


# 메뉴 없을때 반환 함수
def no_menu_response(msg):
    return {
        "menu_name": msg,
        "place_name": "-",
        "menu_price": "-",
        "distance": "-",
        "address": "-",
        "url": "-"
    }
