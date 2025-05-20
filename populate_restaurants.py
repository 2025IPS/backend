# backend/populate_restaurants.py

import pandas as pd
from database import SessionLocal
from models import Restaurant  # ✅ Restaurant 모델 import 필요

# CSV 파일 로드
df = pd.read_csv("./data/final_menu_data.csv")

# DB 연결
db = SessionLocal()

# ✅ place_name과 restaurant_id 쌍 추출 → 중복 제거
unique_restaurants = df[["place_name", "restaurant_id"]].drop_duplicates()

for _, row in unique_restaurants.iterrows():
    restaurant = Restaurant(
        id=int(row["restaurant_id"]),
        name=row["place_name"].strip()
    )
    db.add(restaurant)

db.commit()
db.close()
print("✅ 레스토랑 데이터 삽입 완료")
