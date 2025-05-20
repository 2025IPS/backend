from fastapi import APIRouter, Depends
from pydantic import BaseModel
import pandas as pd
import random
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models import RecommendationHistory

router = APIRouter()

# CSV 로드
menu_df = pd.read_csv("./data/final_menu_data.csv")
menu_df["menu_price"] = menu_df["menu_price"].astype(int)
menu_df["region"] = menu_df["region"].str.strip()
menu_df["allergy"] = menu_df["allergy"].apply(lambda x: [] if pd.isna(x) else [a.strip() for a in x.split(",")])

# ✅ menu_id, restaurant_id 존재 여부 확인
if "menu_id" not in menu_df.columns or "restaurant_id" not in menu_df.columns:
    raise ValueError("menu_id 또는 restaurant_id 컬럼이 누락되었습니다. CSV 파일을 확인해주세요.")

# 위험 재료 매핑
DISEASE_DANGER_FOODS = {
    "당뇨": ["설탕", "당", "디저트"],
    "고혈압": ["짠", "소금", "라면", "찌개"],
    "저혈압": ["카페인"],
    "신장질환": ["나트륨", "짠"]
}
HUNGER_FOOD_CATEGORIES = {
    "적음": ["샐러드", "요거트", "버블티", "샌드위치"],
    "많이": ["피자", "치킨", "덮밥", "찌개", "고기"]
}
DRINK_PAIRINGS = {
    "소주": ["삼겹살", "족발", "찌개", "전"],
    "맥주": ["치킨", "피자", "감자튀김", "소시지"],
    "와인": ["치즈", "파스타", "스테이크"]
}

# DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 요청 모델
class MenuRecommendInput(BaseModel):
    user_id: int
    region: str
    alone: str
    budget: str
    drink: str
    hunger: str
    allergies: list[str]
    diseases: list[str]

# 실패 응답 포맷
def no_menu_response(msg):
    return {
        "menu_name": msg,
        "place_name": "-",
        "menu_price": "-",
        "distance": "-",
        "address": "-",
        "url": "-",
        "user_id": None,
        "menu_id": None,
        "restaurant_id": None
    }

# 추천 API
@router.post("/menu-recommend")
def recommend_menu(input_data: MenuRecommendInput, db: Session = Depends(get_db)):
    try:
        # STEP 1: 예산 필터
        price_min, price_max = 0, 99999999
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

        filtered = menu_df[
            (menu_df["region"] == input_data.region) &
            (menu_df["menu_price"] >= price_min) &
            (menu_df["menu_price"] <= price_max)
        ]

        if filtered.empty:
            return no_menu_response("추천할 메뉴가 없습니다 (예산 필터)")

        # STEP 2: 알러지 필터
        filtered = filtered[filtered["allergy"].apply(lambda x: not any(a in input_data.allergies for a in x))]
        if filtered.empty:
            return no_menu_response("알러지를 고려했을 때 추천할 수 있는 메뉴가 없습니다")

        # STEP 3: 지병 필터
        def is_safe_for_disease(menu_name, diseases):
            for disease in diseases:
                danger_keywords = DISEASE_DANGER_FOODS.get(disease, [])
                for keyword in danger_keywords:
                    if keyword in menu_name:
                        return False
            return True

        filtered = filtered[filtered["menu_name"].apply(lambda x: is_safe_for_disease(x, input_data.diseases))]
        if filtered.empty:
            return no_menu_response("지병을 고려했을 때 안전한 메뉴가 없습니다")

        # STEP 4: 가중치 부여
        candidates = []
        for _, row in filtered.iterrows():
            weight = 1
            menu_name = row["menu_name"]
            if input_data.alone == "혼자" and row["menu_price"] <= 10000:
                weight += 2
            if any(word in menu_name for word in HUNGER_FOOD_CATEGORIES.get(input_data.hunger, [])):
                weight += 2
            if any(word in menu_name for word in DRINK_PAIRINGS.get(input_data.drink, [])):
                weight += 2
            candidates += [row] * weight

        if not candidates:
            return no_menu_response("조건에 맞는 메뉴가 없습니다")

        selected = random.choice(candidates)

        # STEP 5: SQLAlchemy로 추천 기록 저장
        new_rec = RecommendationHistory(
            user_id=input_data.user_id,
            place_name=selected["place_name"],
            menu_name=selected["menu_name"],
            menu_id=int(selected["menu_id"]),
            restaurant_id=int(selected["restaurant_id"])
        )
        db.add(new_rec)
        db.commit()

        return {
            "menu_name": selected["menu_name"],
            "place_name": selected["place_name"],
            "menu_price": selected["menu_price"],
            "distance": "도보 10분 이내",
            "address": selected["address"],
            "url": selected["url"],
            "user_id": input_data.user_id,
            "menu_id": int(selected["menu_id"]),
            "restaurant_id": int(selected["restaurant_id"])
        }

    except Exception as e:
        print("[ERROR]", e)
        return no_menu_response("추천 중 오류가 발생했습니다. 다시 시도해주세요.")
