from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import User, SessionLocal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from dotenv import load_dotenv
import os
import json

load_dotenv()
router = APIRouter(prefix="/api")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MenuRecommendationSystem:
    def __init__(self, api_key):
        self.llm = ChatOpenAI(
            model_name="gpt-4o", 
            temperature=0.7, 
            api_key=api_key,
            streaming=True
        )
        self.conversation_stores = {}

        # 프롬프트 템플릿 개선
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", '''
You are the AI food recommendation assistant of the "Today's Menu" app.

[Role]
- You respond only to food- or meal-related questions.
- Consider the user's profile, weather, and mood to recommend suitable meals.
- If the input is unrelated to food (e.g., "I'm bored", "hi"), respond with: "I'm here to help with food recommendations. Please ask a food-related question."

[Response Rules]
- Recommend 2–3 specific dishes and briefly explain each (1–2 sentences per item).
- Keep your total response within 3 sentences.
- Use real, concrete food names rather than generic suggestions.

[Input]
User Profile: {user_profile}
Current Weather: {weather}
User Message: {input}
'''),
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

recommendation_system = MenuRecommendationSystem(OPENAI_API_KEY)

@router.get("/llm-recommend-stream")
async def llm_recommend_stream(
    user_profile: str,
    weather: str,
    situation: str,
    db: Session = Depends(get_db)
):
    try:
        conversation = recommendation_system.create_conversation_chain()

        async def generate():
            try:
                # 사전 필터링: 무의미한 요청 방지
                irrelevant_keywords = ["심심", "뭐해", "ㅎㅇ", "하이", "안녕", "노잼", "ㅋㅋ", "ㅎㅎ", "hi", "hello", "bored"]
                if any(k in situation.lower() for k in irrelevant_keywords):
                    yield f"data: 저는 음식 추천만 도와드릴 수 있어요. 음식 관련 질문을 해주세요 :)\n\n"
                    yield f"data: [END]\n\n"
                    return

                response_generator = conversation.astream(
                    {
                        "input": situation,
                        "user_profile": user_profile,
                        "weather": weather
                    },
                    config={"configurable": {"session_id": "streaming_session"}}
                )

                async for chunk in response_generator:
                    content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    yield f"data: {content}\n\n"

                yield f"data: [END]\n\n"

            except Exception as e:
                print(f"Streaming error: {str(e)}")
                import traceback
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
        print(f"General error: {str(e)}")
        import traceback
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
