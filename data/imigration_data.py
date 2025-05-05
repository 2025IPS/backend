import pandas as pd
import re

# 데이터 불러오기
menu_df = pd.read_csv("./data/청파동_menu_price.csv")
store_df = pd.read_csv("./data/청파동식당.csv")

# 컬럼명 확인 후 address 컬럼 강제 지정 (중요!!!)
if "address" not in store_df.columns:
    # 만약 컬럼이 '주소' 라면 변경
    if "주소" in store_df.columns:
        store_df = store_df.rename(columns={"주소": "address"})
    else:
        raise ValueError(f"store_df 컬럼에 address 또는 주소가 없습니다. 현재 컬럼들: {store_df.columns}")

# 지역(region) 추출 함수
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

# store_df에 region 컬럼 추가
store_df["region"] = store_df["address"].apply(extract_region)

# 메뉴 데이터 컬럼 정리
menu_df.columns = ["place_name", "category", "menu_name", "weather", "menu_price"]
menu_df["menu_price"] = menu_df["menu_price"].apply(lambda x: int(float(x)) if pd.notna(x) else None)

# 가게 데이터 병합
merged_df = pd.merge(menu_df, store_df, left_on="place_name", right_on="name", how="left")

# allergy 컬럼 추가
merged_df["allergy"] = ""

# 최종 데이터 정리
final_df = merged_df[[
    "place_name", "region", "menu_name", "menu_price", "address", "url", "allergy"
]]

# 저장
final_df.to_csv("./data/청파_menu_data.csv", index=False, encoding="utf-8-sig")
print("최종 효창 메뉴 데이터 저장 완료")
