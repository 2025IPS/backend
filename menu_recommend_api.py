from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
import random

router = APIRouter()

# 최종 통합 데이터 불러오기
menu_df = pd.read_csv("./data/final_menu_data.csv")

class MenuRecommendInput(BaseModel):
    region: str
    alone: str
    budget: str
    drink: str
    hunger: str

@router.post("/menu-recommend")
def recommend_menu(input_data: MenuRecommendInput):
    try:
        # 예산 필터 설정 (최소~최대 가격 설정)
        if "1만원 미만" in input_data.budget:
            price_min = 0
            price_max = 10000
        elif "1~2만원" in input_data.budget:
            price_min = 10000
            price_max = 20000
        elif "2~3만원" in input_data.budget:
            price_min = 20000
            price_max = 30000
        elif "3~4만원" in input_data.budget:
            price_min = 30000
            price_max = 40000
        else:
            price_min = 0
            price_max = 999999

        # 필터 적용 (최소 이상 최대 이하인 메뉴만 필터링)
        filtered = menu_df[
            (menu_df["region"] == input_data.region) &
            (menu_df["menu_price"] >= price_min) &
            (menu_df["menu_price"] <= price_max)
        ]

        if filtered.empty:
            return {
                "menu_name": "추천할 메뉴가 없습니다",
                "place_name": "-",
                "menu_price": "-",
                "distance": "-",
                "address": "-",
                "url": "-"
            }

        # 랜덤 추천
        result = filtered.sample(1).iloc[0]

        return {
            "menu_name": result["menu_name"],
            "place_name": result["place_name"],
            "menu_price": result["menu_price"],
            "distance": "도보 10분 이내",
            "address": result["address"],
            "url": result["url"]
        }

    except Exception as e:
        print("[ERROR]", e)
        return {
            "menu_name": "추천 중 오류가 발생했습니다. 다시 시도해주세요.",
            "place_name": "-",
            "menu_price": "-",
            "distance": "-",
            "address": "-",
            "url": "-"
        }

