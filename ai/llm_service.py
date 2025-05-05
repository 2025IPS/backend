from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, SessionLocal
from pydantic import BaseModel
from typing import List, Optional
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

router = APIRouter(prefix="/chatbot")

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 요청 모델
class ChatRequest(BaseModel):
    username: str
    message: str
    conversation_id: Optional[str] = None

# 응답 모델
class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    suggested_actions: List[str] = []

# 대화 메모리 저장소 (실제 구현에서는 Redis나 DB 사용 권장)
conversation_memories = {}

# 챗봇 클래스
class TodayMenuChatbot:
    def __init__(self, openai_api_key):
        # 모델 초기화
        self.llm = ChatOpenAI(
            model_name="gpt-4-turbo", 
            temperature=0.7, 
            api_key=openai_api_key
        )
        # 임베딩 모델
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        
        # 프롬프트 템플릿
        self.prompt_template = PromptTemplate.from_template("""
다음은 '오늘의 메뉴' 앱의 AI 비서와 사용자 간의 대화입니다. AI 비서는 친절하고 도움이 되며, 음식과 식사에 관한 전문 지식을 갖추고 있습니다.

[사용자 정보]
{user_info}

[시스템 정보]
- 당신은 '오늘의 메뉴' 앱의 AI 비서입니다.
- 당신의 주요 기능은 사용자의 취향, 건강 상태, 상황에 맞는 메뉴를 추천하는 것입니다.
- 메뉴 추천을 위해서는 알레르기, 선호도, 날씨, 혼밥 여부, 예산 등의 정보가 필요합니다.
- 대화를 통해 이러한 정보를 자연스럽게 수집하세요.
- 필요한 모든 정보가 수집되면 메뉴 추천 API를 호출할 수 있습니다.

[대화 지침]
1. 사용자의 요청을 정확히 파악하고 적절한 응답을 제공하세요.
2. 음식과 건강에 관한 질문에는 정확한 정보를 제공하세요.
3. 메뉴 추천을 위한 정보를 수집할 때는 자연스러운 대화 흐름을 유지하세요.
4. 사용자의 건강 상태, 알레르기, 선호도를 항상 고려하세요.
5. 응답은 친절하고 자연스러운 대화체로 작성하세요.
6. 필요한 경우, 다음과 같은 액션을 제안할 수 있습니다:
   - "메뉴 추천 받기"
   - "취향 정보 업데이트하기"
   - "오늘의 식단 계획 세우기"

[이전 대화]
{chat_history}

사용자: {input}
AI 비서:
""")
    
    def create_conversation_chain(self, user_info):
        """사용자 정보를 반영한 대화 체인 생성"""
        memory = ConversationBufferMemory(ai_prefix="AI 비서", human_prefix="사용자")
        
        prompt = self.prompt_template.partial(user_info=user_info)
        
        conversation = ConversationChain(
            llm=self.llm,
            memory=memory,
            prompt=prompt,
            verbose=True
        )
        
        return conversation
    
    def get_suggested_actions(self, user_message, ai_response):
        """컨텍스트에 기반한 추천 액션 생성"""
        # 간단한 키워드 매칭으로 추천 액션 생성
        suggested_actions = []
        
        combined_text = user_message.lower() + " " + ai_response.lower()
        
        if any(word in combined_text for word in ["추천", "메뉴", "음식", "뭐 먹"]):
            suggested_actions.append("메뉴 추천 받기")
        
        if any(word in combined_text for word in ["취향", "선호", "좋아", "싫어"]):
            suggested_actions.append("취향 정보 업데이트하기")
        
        if any(word in combined_text for word in ["식단", "계획", "일주일", "한 주"]):
            suggested_actions.append("식단 계획 세우기")
        
        if any(word in combined_text for word in ["알레르기", "병", "건강"]):
            suggested_actions.append("건강 정보 업데이트하기")
        
        return suggested_actions[:3]  # 최대 3개까지만 표시

# 챗봇 인스턴스 생성
chatbot = TodayMenuChatbot(OPENAI_API_KEY)

@router.post("/chat", response_model=ChatResponse)
def chat_with_bot(request: ChatRequest, db: Session = Depends(get_db)):
    """사용자와 챗봇 간의 대화 API"""
    # 사용자 정보 조회
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 사용자 정보 가공
    allergies = [a.allergy for a in user.allergies]
    diseases = [d.disease for d in user.diseases]
    preferences = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    dislikes = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]
    
    user_info = f"""
사용자명: {user.username}
알레르기: {', '.join(allergies) if allergies else '없음'}
질병: {', '.join(diseases) if diseases else '없음'}
선호 메뉴: {', '.join(preferences) if preferences else '없음'}
비선호 메뉴: {', '.join(dislikes) if dislikes else '없음'}
"""
    
    # 대화 ID가 없거나 메모리에 없는 경우 새 대화 시작
    if not request.conversation_id or request.conversation_id not in conversation_memories:
        conversation_id = f"conv_{user.username}_{len(conversation_memories) + 1}"
        conversation = chatbot.create_conversation_chain(user_info)
        conversation_memories[conversation_id] = conversation
    else:
        conversation_id = request.conversation_id
        conversation = conversation_memories[conversation_id]
    
    # 챗봇 응답 생성
    response = conversation.predict(input=request.message)
    
    # 추천 액션 생성
    suggested_actions = chatbot.get_suggested_actions(request.message, response)
    
    return ChatResponse(
        response=response,
        conversation_id=conversation_id,
        suggested_actions=suggested_actions
    )

@router.delete("/conversation/{conversation_id}")
def end_conversation(conversation_id: str):
    """대화 종료 및 메모리 정리"""
    if conversation_id in conversation_memories:
        del conversation_memories[conversation_id]
        return {"status": "success", "message": "대화가 종료되었습니다."}
    
    raise HTTPException(status_code=404, detail="해당 대화를 찾을 수 없습니다.")