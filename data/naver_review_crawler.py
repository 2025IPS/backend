from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import os
import re

# ✅ 입력 파일 경로 및 출력 폴더
input_csv = "data/final_menu_data.csv"
output_dir = "review_results"
os.makedirs(output_dir, exist_ok=True)

# ✅ place_id 추출 함수
def extract_place_id(url):
    try:
        return url.split("/")[-1]
    except Exception as e:
        print(f"[place_id 추출 오류] URL: {url} → {e}")
        return None

# ✅ 크롬 모바일 설정
options = Options()
# options.add_argument("--headless")  # 디버깅 시 주석 처리
options.add_argument("--disable-gpu")
options.add_argument("--window-size=375,812")
options.add_argument(
    "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ✅ 리뷰 크롤링 함수 (리뷰만 저장)
def crawl_reviews(place_id, place_name):
    url = f"https://m.place.naver.com/restaurant/{place_id}/review/visitor"
    driver.get(url)
    time.sleep(2)

    for _ in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.2)
        try:
            more_btn = driver.find_element(By.CLASS_NAME, "fvwqf")
            driver.execute_script("arguments[0].click();", more_btn)
            time.sleep(1)
        except:
            break

    try:
        review_elements = driver.find_elements(By.CSS_SELECTOR, ".pui__vn15t2 a")
        reviews = [e.text.strip() for e in review_elements if e.text.strip()]

        safe_name = re.sub(r"[^\w가-힣]", "_", place_name)
        df = pd.DataFrame({"review": reviews})
        output_path = os.path.join(output_dir, f"reviews_{safe_name}_{place_id}.csv")
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✔ {place_name} ({place_id}) 리뷰 {len(df)}개 저장 완료 → {output_path}")

    except Exception as e:
        raise RuntimeError(f"요소 수집 실패: {e}")

# ✅ 입력 데이터 불러오기 및 중복 제거
df = pd.read_csv(input_csv)
df = df.drop_duplicates(subset=["place_name", "url"])

try:
    for idx, row in df.iterrows():
        place_name = str(row["place_name"])
        url = str(row["url"])
        place_id = extract_place_id(url)

        if not place_id:
            print(f"⚠️ {place_name}의 place_id 추출 실패 → {url}")
            continue

        safe_name = re.sub(r"[^\w가-힣]", "_", place_name)
        output_file = os.path.join(output_dir, f"reviews_{safe_name}_{place_id}.csv")
        if os.path.exists(output_file):
            print(f"⏩ {place_name} ({place_id}) 이미 수집됨. 건너뜀.")
            continue

        try:
            crawl_reviews(place_id, place_name)
        except Exception as e:
            print(f"❌ {place_name} ({place_id}) 리뷰 수집 실패: {e}")
finally:
    driver.quit()
