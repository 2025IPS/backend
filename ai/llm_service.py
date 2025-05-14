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

# DB 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 요청 목록
class ChatRequest(BaseModel):
    username: str
    message: str
    conversation_id: Optional[str] = None

# 응답 목록
class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    suggested_actions: List[str] = []

# 대화 메모리
conversation_memories = {}

# 챗봇 클래스
class TodayMenuChatbot:
    def __init__(self, openai_api_key):
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            api_key=openai_api_key
        )
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)

        self.prompt_template = PromptTemplate.from_template("""
The following is a conversation between a user and 'Today's Menu' AI assistant.
You are friendly, concise (within 3 sentences), and specialize in food, nutrition, and personalized meal recommendations.

[User Profile]
{user_info}

[System Instructions]
- Respond only to food-related questions or meal recommendation scenarios.
- If the user's message is irrelevant (e.g. greetings like "hi" or "I'm bored"), reply with: "I'm here to help with meal recommendations. Please ask a food-related question."
- Keep responses short (under 3 sentences).
- Be friendly and conversational.

[Previous Conversation]
{chat_history}

User: {input}
AI Assistant:
""")

    def create_conversation_chain(self, user_info):
        memory = ConversationBufferMemory(ai_prefix="AI Assistant", human_prefix="User")
        prompt = self.prompt_template.partial(user_info=user_info)
        return ConversationChain(llm=self.llm, memory=memory, prompt=prompt, verbose=True)

    def get_suggested_actions(self, user_message, ai_response):
        suggestions = []
        combined = user_message.lower() + " " + ai_response.lower()

        if any(x in combined for x in ["recommend", "menu", "eat"]):
            suggestions.append("Get a menu recommendation")
        if any(x in combined for x in ["preference", "like", "dislike"]):
            suggestions.append("Update taste preferences")
        if any(x in combined for x in ["plan", "week", "meal"]):
            suggestions.append("Plan weekly meals")
        if any(x in combined for x in ["allergy", "health", "disease"]):
            suggestions.append("Update health info")

        return suggestions[:3]

chatbot = TodayMenuChatbot(OPENAI_API_KEY)

@router.post("/chat", response_model=ChatResponse)
def chat_with_bot(request: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allergies = [a.allergy for a in user.allergies]
    diseases = [d.disease for d in user.diseases]
    preferences = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    dislikes = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]

    user_info = f"""
Username: {user.username}
Allergies: {', '.join(allergies) if allergies else 'None'}
Diseases: {', '.join(diseases) if diseases else 'None'}
Preferred Menus: {', '.join(preferences) if preferences else 'None'}
Disliked Menus: {', '.join(dislikes) if dislikes else 'None'}
"""

    irrelevant_keywords = ["심심", "뭐해", "ㅎㅇ", "하이", "안녕", "노잼", "ㅋㅋ", "ㅎㅎ", "hi", "hello", "bored"]
    if any(keyword in request.message.lower() for keyword in irrelevant_keywords):
        return ChatResponse(
            response="I'm here to help with meal recommendations. Please ask a food-related question.",
            conversation_id=request.conversation_id or f"conv_{request.username}_manual",
            suggested_actions=[]
        )

    if not request.conversation_id or request.conversation_id not in conversation_memories:
        conversation_id = f"conv_{user.username}_{len(conversation_memories) + 1}"
        conversation = chatbot.create_conversation_chain(user_info)
        conversation_memories[conversation_id] = conversation
    else:
        conversation_id = request.conversation_id
        conversation = conversation_memories[conversation_id]

    response = conversation.predict(input=request.message)
    suggestions = chatbot.get_suggested_actions(request.message, response)

    return ChatResponse(
        response=response,
        conversation_id=conversation_id,
        suggested_actions=suggestions
    )

@router.delete("/conversation/{conversation_id}")
def end_conversation(conversation_id: str):
    if conversation_id in conversation_memories:
        del conversation_memories[conversation_id]
        return {"status": "success", "message": "Conversation ended."}
    raise HTTPException(status_code=404, detail="Conversation not found")