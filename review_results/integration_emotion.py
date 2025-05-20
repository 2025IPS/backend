import os
import pandas as pd
from collections import Counter

# 리뷰 폴더 및 메뉴 파일 경로
review_folder = r"C:\TodayMenu\backend\review_results"
menu_data_path = r"C:\TodayMenu\backend\data\final_menu_data.csv"
output_path = r"C:\TodayMenu\backend\data\final_menu_data_with_tags_fuzzy.csv"

# 감성 키워드 사전
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

def extract_emotion_tags(text):
    tags = set()
    for tag, keywords in emotion_keywords.items():
        for kw in keywords:
            if kw in text:
                tags.add(tag)
                break
    return list(tags)

# 감성 태그 통계 저장
emotion_counter = {}
all_reviews = []

# 1️⃣ 리뷰 파일 순회하여 감성 태그 수집
for filename in os.listdir(review_folder):
    if not filename.endswith(".csv"):
        continue

    try:
        filepath = os.path.join(review_folder, filename)

        # 파일명 예시: reviews_일신기사식당_순두부찌개_123456.csv
        name_parts = filename.replace("reviews_", "").replace(".csv", "").split("_")
        place_name = name_parts[0]
        menu_name = name_parts[1] if len(name_parts) > 2 else ""

        df = pd.read_csv(filepath)
        df = df[~df["review"].isin(["더보기", "내꺼"])]
        df = df.dropna(subset=["review"])

        df["place_name"] = place_name
        df["menu_name"] = menu_name
        df["emotion_tags"] = df["review"].apply(lambda x: extract_emotion_tags(str(x)))

        for tags in df["emotion_tags"]:
            key = (place_name, menu_name)
            if key not in emotion_counter:
                emotion_counter[key] = Counter()
            emotion_counter[key].update(tags)

        all_reviews.append(df[["place_name", "menu_name", "review", "emotion_tags"]])

    except Exception as e:
        print(f"❌ 오류 발생: {filename} → {e}")

# 2️⃣ 감성 태그 통계 → DataFrame
tag_stats = []
for (place, menu), counter in emotion_counter.items():
    tag_list = [f"{tag}:{count}" for tag, count in counter.items()]
    tag_stats.append({
        "place_name": place,
        "menu_name": menu,
        "emotion_summary": ", ".join(tag_list),
        "top_tags": ", ".join([tag for tag, _ in counter.most_common(3)])
    })

tag_df = pd.DataFrame(tag_stats)

# 3️⃣ 정확 병합 먼저 수행
menu_df = pd.read_csv(menu_data_path)
merged_df = pd.merge(menu_df, tag_df, on=["place_name", "menu_name"], how="left")

# 4️⃣ 병합되지 않은 행들 → 유사 menu_name으로 fuzzy merge
def fuzzy_merge(unmatched_df, tag_df):
    fixed_rows = []
    for _, row in unmatched_df.iterrows():
        place = row["place_name"]
        menu = row["menu_name"]
        candidates = tag_df[tag_df["place_name"] == place]

        # 포함 관계 기반 유사 메뉴명 찾기
        match = candidates[candidates["menu_name"].apply(lambda x: menu in x or x in menu)]
        if not match.empty:
            tag_row = match.iloc[0]
            row["emotion_summary"] = tag_row["emotion_summary"]
            row["top_tags"] = tag_row["top_tags"]
        fixed_rows.append(row)
    return pd.DataFrame(fixed_rows)

unmatched = merged_df[merged_df["emotion_summary"].isna()]
matched = merged_df[~merged_df["emotion_summary"].isna()]
fixed = fuzzy_merge(unmatched, tag_df)

# 5️⃣ 최종 병합 후 저장
final_df = pd.concat([matched, fixed], ignore_index=True)
final_df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"✅ 감성 태그 병합 완료: {output_path}")
