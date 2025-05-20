# --- FastAPI 기반 상황 기반 메뉴 추천 API (정교화된 버전) ---

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import SessionLocal, User, Feedback
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from dotenv import load_dotenv
import pandas as pd
import traceback
from collections import Counter
import os

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")

# 라우터 생성
router = APIRouter(prefix="/api")

# DB 세션 생성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CSV 로드 및 파싱
menu_df = pd.read_csv("./data/final_menu_data_with_emotion.csv")
menu_df["disease"] = menu_df["disease"].apply(eval)

# 상황 키워드 -> 감성 태그 매핑
def extract_situation_tags(situation: str) -> list[str]:
    mapping = {
        "매콤": ["매움"],
        "해장": ["속풀이"],
        "꿀꿀": ["단맛", "중독성"],
        "가볍": ["가성비", "양많음"],
        "친구": ["분위기좋음", "특별함"],
        "추워": ["속풀이"],
        "덥": ["가성비"],
        "달달": ["단맛"],
        "배고": ["양많음"],
        "야식": ["야식"]
    }
    tags = set()
    for keyword, tag_list in mapping.items():
        if keyword in situation:
            tags.update(tag_list)
    return list(tags)

# 위험한 메뉴 제외 함수
def filter_menu_by_disease(df: pd.DataFrame, diseases: list[str]) -> pd.DataFrame:
    return df[~df['disease'].apply(lambda risks: any(d in risks for d in diseases))]

# 피드백 점수 계산 함수
def apply_feedback_weights(df: pd.DataFrame, db: Session) -> pd.DataFrame:
    feedbacks = db.query(Feedback).all()
    good_counts = Counter((f.place_name, f.menu_name) for f in feedbacks if f.feedback == "good")
    bad_counts = Counter((f.place_name, f.menu_name) for f in feedbacks if f.feedback == "bad")

    def compute_score(row):
        key = (row["place_name"], row["menu_name"])
        return good_counts[key] - bad_counts[key]

    df = df.copy()
    df["feedback_score"] = df.apply(compute_score, axis=1)
    return df.sort_values(by="feedback_score", ascending=False)

# GPT 추천 시스템
class MenuRecommendationSystem:
    def __init__(self, api_key, menu_list):
        self.menu_list = menu_list
        self.llm = ChatOpenAI(
            model_name="gpt-4o",
            temperature=0.7,
            api_key=api_key,
            streaming=True
        )
        self.conversation_stores = {}

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"""
You are the AI chatbot for the Korean food recommendation app \"Today's Menu\".

[Instructions]
- Always respond **in Korean only**. No English allowed.
- Recommend only from the list below. Do not hallucinate new items.
- If recommending a dish, provide a short emotional reason (based on 감성 키워드).

[Allowed Menu and Restaurant List]
{self.menu_list}

[Input Info]
User Profile: {{user_profile}}
Weather: {{weather}}
User Message: {{input}}
"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

    def get_session_history(self, session_id: str):
        if session_id not in self.conversation_stores:
            self.conversation_stores[session_id] = InMemoryChatMessageHistory()
        return self.conversation_stores[session_id]

    def create_conversation_chain(self):
        chain = self.prompt_template | self.llm
        return RunnableWithMessageHistory(
            chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

# 추천 API
@router.get("/llm-recommend-stream")
async def llm_recommend_stream(
    user_id: int,
    weather: str,
    situation: str,
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("존재하지 않는 사용자입니다.")

        allergies = [a.allergy for a in user.allergies]
        likes = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
        dislikes = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]
        user_diseases = [d.disease for d in user.diseases]

        user_profile = f"알레르기: {', '.join(allergies) if allergies else '없음'} / 선호 재료: {', '.join(likes) if likes else '없음'} / 비선호 재료: {', '.join(dislikes) if dislikes else '없음'} / 질병: {', '.join(user_diseases) if user_diseases else '없음'}"

        safe_menu_df = filter_menu_by_disease(menu_df, user_diseases)
        scored_menu_df = apply_feedback_weights(safe_menu_df, db)

        situation_tags = extract_situation_tags(situation)
        relevant_menu_df = scored_menu_df[
            scored_menu_df["top_tags"].apply(lambda x: any(tag in str(x) for tag in situation_tags))
        ]

        fallback_df = relevant_menu_df if not relevant_menu_df.empty else scored_menu_df

        menu_list_str = "\n".join(
            f"- [{row['menu_name']} ({row['place_name']})]({row['url']}) - 감성: {row['top_tags']}"
            for _, row in fallback_df[['place_name', 'menu_name', 'url', 'top_tags']].drop_duplicates().iterrows()
        )

        recommendation_system = MenuRecommendationSystem(OPENAI_API_KEY, menu_list_str)
        conversation = recommendation_system.create_conversation_chain()

        async def generate():
            try:
                if user_diseases:
                    yield f"data: ⚠️ {', '.join(user_diseases)}에 따라 위험 메뉴를 제외하고 추천해드릴게요.\n\n"

                response_generator = conversation.astream(
                    {
                        "input": situation,
                        "user_profile": user_profile,
                        "weather": weather or "날씨 정보 없음"
                    },
                    config={"configurable": {"session_id": "streaming_session"}}
                )

                async for chunk in response_generator:
                    content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    yield f"data: {content}\n\n"

                yield f"data: [END]\n\n"
            except Exception as e:
                traceback.print_exc()
                yield f"data: 추천 중 오류가 발생했어요. 다시 시도해 주세요.\n\n"
                yield f"data: [END]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )

    except Exception as e:
        traceback.print_exc()

        async def error_response():
            yield f"data: 서버 오류가 발생했습니다.\n\n"
            yield f"data: [END]\n\n"

        return StreamingResponse(
            error_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
