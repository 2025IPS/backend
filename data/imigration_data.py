import pandas as pd
import re

# 데이터 불러오기
menu_df = pd.read_csv("./data/menu_price.csv")
store_df = pd.read_csv("./data/청파동식당.csv")
nutrient_df = pd.read_csv("./data/menu_nutrient.csv")

# 주소에서 동(지역) 추출 함수
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

# 가게 데이터에 지역 컬럼 추가
store_df["region"] = store_df["address"].apply(extract_region)

# 메뉴와 가게 데이터 병합
merged_df = pd.merge(menu_df, store_df, left_on="place_name", right_on="name", how="left")

# 메뉴와 영양정보 데이터 병합
merged_df = pd.merge(merged_df, nutrient_df, left_on="menu_name", right_on="name", how="left")

# 최종 필요한 컬럼만 정리
final_df = merged_df[[
    "place_name", "region", "menu_name", "menu_price", "address", "url", "allergy"
]]

# 저장 (원하면 ./data/final_menu_data.csv 로)
final_df.to_csv("./data/final_menu_data.csv", index=False, encoding="utf-8-sig")

print("최종 메뉴 데이터 저장 완료")
