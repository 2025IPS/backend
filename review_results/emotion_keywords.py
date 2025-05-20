import os
import pandas as pd

# 경로 설정 (로컬 환경 기준)
review_folder = r"C:\TodayMenu\backend\review_results"

# 키워드 사전 정의
emotion_keywords = {
    "매움": ["맵", "매콤", "얼얼", "불맛"],
    "단맛": ["달아", "달콤", "단맛"],
    "짠맛": ["짭", "짠맛"],
    "양많음": ["푸짐", "양이 많", "듬뿍"],
    "가성비": ["가성비", "가격대비", "혜자", "저렴"],
    "재방문": ["또 가", "다시 가", "재방문", "생각나", "단골"],
    "친절함": ["친절", "서비스 좋", "응대"],
    "분위기좋음": ["분위기", "깔끔", "조용", "청결", "인테리어"],
    "속풀이": ["해장", "속이 풀"],
    "야식": ["야식", "늦게", "밤에"],
    "중독성": ["중독", "계속", "자꾸", "생각나"],
    "특별함": ["특이", "독특", "색다른"],
    "냄새없음": ["잡내", "냄새 안"],
    "포장추천": ["포장", "배달"]
}

# 감성 태그 추출 함수
def extract_emotion_tags(text):
    tags = set()
    for tag, keywords in emotion_keywords.items():
        for kw in keywords:
            if kw in text:
                tags.add(tag)
                break
    return list(tags)

# 전체 리뷰 결과를 담을 리스트
all_reviews = []

# 폴더 내 모든 csv 파일 순회
for filename in os.listdir(review_folder):
    if filename.endswith(".csv"):
        filepath = os.path.join(review_folder, filename)
        place_name = filename.replace("reviews_", "").replace(".csv", "").split("_")[0]
        try:
            df = pd.read_csv(filepath)
            df = df[~df["review"].isin(["더보기", "내꺼"])]
            df = df.dropna(subset=["review"])

            df["place_name"] = place_name
            df["emotion_tags"] = df["review"].apply(lambda x: extract_emotion_tags(str(x)))

            all_reviews.append(df[["place_name", "review", "emotion_tags"]])
        except Exception as e:
            print(f"❌ 오류 발생: {filename} → {e}")

# 통합된 DataFrame 생성
combined_df = pd.concat(all_reviews, ignore_index=True)

# CSV로 저장
output_path = r"C:\TodayMenu\backend\data\all_reviews_with_tags.csv"
combined_df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"✅ 감성 태그 추출 완료: {output_path}")
