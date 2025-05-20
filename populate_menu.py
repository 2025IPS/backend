# backend/populate_menu.py

import pandas as pd
from database import SessionLocal
from models import Menu

df = pd.read_csv("./data/final_menu_data.csv")
db = SessionLocal()

for _, row in df.iterrows():
    menu = Menu(
        place_name=row['place_name'],
        menu_name=row['menu_name'],
        price=row['menu_price'],
        category="",  # 필요시 채우세요
        weather="",
        allergy=row['allergy'],
    )
    menu.id = int(row['menu_id'])
    menu.restaurant_id = int(row['restaurant_id'])

    db.add(menu)

db.commit()
db.close()
print("✅ 메뉴 데이터 삽입 완료")
