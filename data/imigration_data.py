import pandas as pd

# 1. 기존 CSV 로드
menu_df = pd.read_csv("C:/TodayMenu/backend/data/final_menu_data.csv")

# 2. 질병 키워드 정의
disease_avoid_keywords = {
    "고혈압": ["짠", "간", "국", "찌개", "탕", "면", "김치", "라면", "햄", "소금", "장"],
    "당뇨": ["케이크", "초콜릿", "떡볶이", "아이스크림", "설탕", "달콤", "디저트", "단호박"],
    "신장질환": ["국", "찌개", "라면", "햄", "소시지", "된장", "소금", "짠", "나트륨"]
}

# 3. disease_risk 분류 함수 정의
def classify_menu_disease_risks(menu_df, disease_avoid_keywords):
    menu_df['disease_risk'] = [[] for _ in range(len(menu_df))]
    for idx, menu in menu_df.iterrows():
        risks = []
        for disease, keywords in disease_avoid_keywords.items():
            if any(keyword in str(menu['menu_name']) for keyword in keywords):
                risks.append(disease)
        menu_df.at[idx, 'disease_risk'] = risks
    return menu_df

# 4. 적용
menu_df = classify_menu_disease_risks(menu_df, disease_avoid_keywords)

# 5. 저장
menu_df.to_csv("C:/TodayMenu/backend/data/final_menu_with_risk.csv", index=False)
print("✅ disease_risk 추가 완료 및 저장 완료!")
