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
            streaming=True  # 스트리밍 활성화
        )
        self.conversation_stores = {}
        
        # 프롬프트 템플릿 수정: 변수 이름 통일
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """당신은 음식 추천 전문가입니다. 사용자의 상황과 정보를 고려하여 최적의 메뉴를 추천해주세요.

사용자 정보: {user_profile}
현재 날씨: {weather}

추천 규칙:
1. 날씨와 상황에 맞는 음식 추천
2. 예산과 인원수 고려
3. 혼밥에 적합한 음식 추천
4. 비오는 날에는 따뜻하고 포근한 음식 위주로 추천
5. 추천 메뉴는 구체적이고 실제 주문 가능한 메뉴로 제시

형식: 추천 메뉴들을 자연스러운 대화체로 설명해주세요.
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
                # situation을 input으로 전달
                response_generator = conversation.astream(
                    {
                        "input": situation,  # situation이 input으로 들어가야 함
                        "user_profile": user_profile,
                        "weather": weather
                    },
                    config={"configurable": {"session_id": "streaming_session"}}
                )
                
                # 응답 스트리밍
                async for chunk in response_generator:
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                    else:
                        content = str(chunk)
                    
                    # 청크 전송
                    yield f"data: {content}\n\n"
                
                # 종료 신호
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