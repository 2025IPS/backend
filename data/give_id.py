import pandas as pd

# CSV 불러오기
menu_df = pd.read_csv("./data/final_menu_data_with_emotion.csv")

# 기본 정제
menu_df["region"] = menu_df["region"].str.strip()
menu_df["menu_price"] = menu_df["menu_price"].apply(lambda x: int(str(x).replace(",", "").strip()))

# ✅ allergy: 쉼표 구분 문자열로 유지
menu_df["allergy"] = menu_df["allergy"].apply(
    lambda x: "" if pd.isna(x) else ", ".join([a.strip() for a in str(x).split(",")])
)

# ✅ disease: 문자열 리스트 그대로 유지
menu_df["disease"] = menu_df["disease"].apply(eval)

# ✅ menu_id: 고유 ID 부여
menu_df["menu_id"] = menu_df.reset_index().index

# ✅ restaurant_id: place_name 기준 ID 부여
restaurant_map = {name: i for i, name in enumerate(menu_df["place_name"].unique())}
menu_df["restaurant_id"] = menu_df["place_name"].map(restaurant_map)

# ✅ emotion_summary, top_tags는 그대로 둠

# ✅ disease 컬럼을 문자열로 다시 저장 (CSV 출력 목적)
menu_df["disease"] = menu_df["disease"].apply(str)

# ✅ 최종 저장
menu_df.to_csv("./data/final_menu_data_with_id.csv", index=False)
