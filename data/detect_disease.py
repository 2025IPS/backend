import pandas as pd
import re

# 원본 CSV 파일 경로
input_path = "C:/TodayMenu/backend/data/final_menu_data.csv"

# 결과 저장 경로
output_path = "C:/TodayMenu/backend/data/annotated_menu_data.csv"

# 지병별 위험 키워드 정의
DISEASE_DANGER_FOODS = {
    "당뇨": [
        "설탕", "시럽", "케이크", "디저트", "와플", "라떼", "빙수", "단호박죽", "초코", "빵",
        "젤리", "쿠키", "꿀", "크림", "밀크티", "마카롱", "호떡", "토스트", "핫케이크", "피넛버터", "롤케이크",
        "카라멜", "팥빙수", "생크림", "슈크림", "아이스크림", "팬케이크", "프라푸치노", "스무디", "주스", "쥬스", "양념","허니",
    ],
    "고혈압": [
        "짠", "소금", "라면", "찌개", "간장", "국물", "짬뽕", "된장", "김치찌개", "불고기", "짜장",
        "제육", "곰탕", "육개장", "감자탕", "순대국", "돼지국밥", "해장국", "삼겹살", "닭갈비", "마라탕",
        "간장계란밥", "쌈장", "어묵탕", "우동", "짬짜면", "비빔면", "김치볶음밥", "소세지볶음", "햄", "베이컨"
    ],
    "저혈압": [
        "카페인", "커피", "아메리카노", "에스프레소", "콜드브루", "카푸치노", "더치커피",
        "마끼아또", "프라푸치노", "카페모카", "롱블랙", "브루드커피", "플랫화이트", "라떼", "아포가토"
    ],
    "신장질환": [
        "나트륨", "짠", "국물", "젓갈", "김치", "명란", "어묵", "햄", "소세지", "쏘세지",
        "가공육", "베이컨", "스팸", "멸치볶음", "장조림", "된장국", "김치전", "생선젓", "곱창", "순대"
    ]
}

# 정규화 함수
def normalize_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", str(text).lower())

# 위험 질병 추출 함수 → 리스트 반환
def get_disease_risks(menu_name: str) -> list[str]:
    menu_name = normalize_text(menu_name)
    risks = []
    for disease, keywords in DISEASE_DANGER_FOODS.items():
        for keyword in keywords:
            if normalize_text(keyword) in menu_name:
                risks.append(disease)
                break
    return risks

# 데이터 불러오기
df = pd.read_csv(input_path)

# 분석 적용 → disease 컬럼에 리스트 형태 저장
df["disease"] = df["menu_name"].apply(get_disease_risks)

# 저장
df.to_csv(output_path, index=False)

print(f"✅ 저장 완료: {output_path}")

