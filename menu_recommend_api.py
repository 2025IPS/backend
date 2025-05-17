from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
import random
import datetime
import sqlite3

router = APIRouter()

# 데이터 로드
menu_df = pd.read_csv("./data/final_menu_data.csv")

# menu_price를 int로 변환 → 오류 방지용 추가
menu_df["menu_price"] = menu_df["menu_price"].astype(int)
menu_df["region"] = menu_df["region"].str.strip()  # 꼭 추가!


# 알러지 데이터 처리
menu_df["allergy"] = menu_df["allergy"].apply(lambda x: [] if pd.isna(x) else [a.strip() for a in x.split(",")])

# 지병 위험 키워드 매핑
DISEASE_DANGER_FOODS = {
    "당뇨": ["설탕", "당", "디저트"],
    "고혈압": ["짠", "소금", "라면", "찌개"],
    "저혈압": ["카페인"],
    "신장질환": ["나트륨", "짠"]
}

# 공복 키워드 매핑
HUNGER_FOOD_CATEGORIES = {
    "적음": ["샐러드", "요거트", "버블티", "샌드위치"],
    "많이": ["피자", "치킨", "덮밥", "찌개", "고기"]
}

# 음주 메뉴 매핑
DRINK_PAIRINGS = {
    "소주": ["삼겹살", "족발", "찌개", "전"],
    "맥주": ["치킨", "피자", "감자튀김", "소시지"],
    "와인": ["치즈", "파스타", "스테이크"]
}

# DB 경로
DB_PATH = "./recommend_history.db"

# DB 초기화
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS recommend_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            region TEXT,
            menu_name TEXT,
            place_name TEXT,
            price INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 요청 모델
class MenuRecommendInput(BaseModel):
    region: str
    alone: str
    budget: str
    drink: str
    hunger: str
    allergies: list[str]
    diseases: list[str]

# 추천 없음 반환
def no_menu_response(msg):
    return {
        "menu_name": msg,
        "place_name": "-",
        "menu_price": "-",
        "distance": "-",
        "address": "-",
        "url": "-"
    }

# 메뉴 추천 API
@router.post("/menu-recommend")
def recommend_menu(input_data: MenuRecommendInput):
    try:
        # 예산 필터링
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
            price_min, price_max = 40000, 99999999  # 4만원 이상 처리 추가

        # 지역 + 예산 필터링
        filtered = menu_df[
            (menu_df["region"] == input_data.region) &
            (menu_df["menu_price"] >= price_min) &
            (menu_df["menu_price"] <= price_max)
        ]

        if filtered.empty:
            return no_menu_response("추천할 메뉴가 없습니다")

        # 알러지 필터링
        filtered = filtered[filtered["allergy"].apply(lambda x: len(set(x) & set(input_data.allergies)) == 0)]
        if filtered.empty:
            return no_menu_response("알러지에 맞는 메뉴가 없습니다")

        # 지병 필터링
        def is_safe_for_disease(menu_name, diseases):
            for disease in diseases:
                danger_keywords = DISEASE_DANGER_FOODS.get(disease, [])
                if any(keyword in menu_name for keyword in danger_keywords):
                    return False
            return True

        filtered = filtered[filtered["menu_name"].apply(lambda x: is_safe_for_disease(x, input_data.diseases))]
        if filtered.empty:
            return no_menu_response("지병에 맞는 메뉴가 없습니다")

        # 후보 메뉴 가중치 계산
        candidates = []
        for _, row in filtered.iterrows():
            weight = 1
            menu_name = row["menu_name"]

            # 혼밥 → 저가 메뉴 가중치
            if input_data.alone == "혼자" and row["menu_price"] <= 10000:
                weight += 2

            # 공복 정도 가중치
            hunger_keywords = HUNGER_FOOD_CATEGORIES.get(input_data.hunger, [])
            if any(word in menu_name for word in hunger_keywords):
                weight += 2

            # 음주 메뉴 가중치
            drink_keywords = DRINK_PAIRINGS.get(input_data.drink, [])
            if any(word in menu_name for word in drink_keywords):
                weight += 2

            candidates += [row] * weight

        if not candidates:
            return no_menu_response("조건에 맞는 메뉴가 없습니다")

        # 추천 메뉴 선택
        selected = random.choice(candidates)

        result = {
            "menu_name": selected["menu_name"],
            "place_name": selected["place_name"],
            "menu_price": selected["menu_price"],
            "distance": "도보 10분 이내",
            "address": selected["address"],
            "url": selected["url"]
        }

        # 추천 기록 저장
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO recommend_history (datetime, region, menu_name, place_name, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.datetime.now().isoformat(),
            input_data.region,
            selected["menu_name"],
            selected["place_name"],
            selected["menu_price"]
        ))
        conn.commit()
        conn.close()

        return result

    except Exception as e:
        print("[ERROR]", e)
        return no_menu_response("추천 중 오류가 발생했습니다. 다시 시도해주세요.")

# 추천 기록 조회 API
@router.get("/menu-recommend/history")
def get_recommend_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, datetime, region, menu_name, place_name, price FROM recommend_history ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "datetime": row[1],
            "region": row[2],
            "menu_name": row[3],
            "place_name": row[4],
            "price": row[5]
        })

    return history
