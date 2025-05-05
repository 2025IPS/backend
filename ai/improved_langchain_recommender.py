from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import Document
import os
import json
from typing import List, Optional

# 모델과 세션 관련 임포트
from models import User, SessionLocal

from dotenv import load_dotenv
import os

# FastAPI Router
router = APIRouter(prefix="/menu")

load_dotenv()

# API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

# Vector DB 경로
MENU_DB_PATH = "./chroma_db/menu_db"

# LLM 설정
llm = ChatOpenAI(
    model_name="gpt-4o",
    temperature=0.7,
    openai_api_key=OPENAI_API_KEY
)

# 응답 모델
class MenuRecommendation(BaseModel):
    recommended_menu: str
    recommendation_reason: str
    alternative_options: List[str]

# 요청 모델
class LLMRecommendRequest(BaseModel):
    username: str
    allergies: List[str] = []
    diseases: List[str] = []
    preferences: List[str] = []
    dislikes: List[str] = []
    weather: str
    alone: str
    budget: str
    mood: Optional[str] = None
    previous_recommendations: List[str] = []

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 메뉴 DB 초기화
def initialize_menu_db():
    sample_menus = [
        {"name": "김치찌개", "ingredients": ["김치", "돼지고기", "두부"], "type": "한식", "price_range": "중간"},
        {"name": "비빔밥", "ingredients": ["쌀", "나물", "계란", "고추장"], "type": "한식", "price_range": "중간"},
        {"name": "파스타", "ingredients": ["면", "소스", "올리브유"], "type": "양식", "price_range": "중간"},
        {"name": "스테이크", "ingredients": ["소고기", "감자", "샐러드"], "type": "양식", "price_range": "높음"},
        {"name": "라멘", "ingredients": ["면", "돼지고기", "계란", "국물"], "type": "일식", "price_range": "중간"},
        {"name": "초밥", "ingredients": ["쌀", "생선", "와사비"], "type": "일식", "price_range": "높음"},
    ]
    documents = []
    for menu in sample_menus:
        content = f"이름: {menu['name']}\n종류: {menu['type']}\n주요 재료: {', '.join(menu['ingredients'])}\n가격대: {menu['price_range']}"
        doc = Document(page_content=content, metadata=menu)
        documents.append(doc)

    embedding_function = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    db = Chroma.from_documents(documents=documents, embedding=embedding_function, persist_directory=MENU_DB_PATH)
    db.persist()
    return db

# Vector DB 로드
try:
    menu_db = Chroma(persist_directory=MENU_DB_PATH, embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY))
except:
    menu_db = initialize_menu_db()

menu_retriever = menu_db.as_retriever(search_kwargs={"k": 5})

@router.post("/llm-recommend")
def llm_recommend(input_data: LLMRecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == input_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if not input_data.allergies:
        input_data.allergies = [a.allergy for a in user.allergies]
    if not input_data.diseases:
        input_data.diseases = [d.disease for d in user.diseases]
    if not input_data.preferences:
        input_data.preferences = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    if not input_data.dislikes:
        input_data.dislikes = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]

    valid_budget = ["낮음", "중간", "높음"]
    if input_data.budget not in valid_budget:
        raise HTTPException(status_code=400, detail=f"예산은 {valid_budget} 중 하나여야 합니다.")

    search_query = f"예산: {input_data.budget} 날씨: {input_data.weather} 선호: {', '.join(input_data.preferences)}"
    relevant_menus = menu_retriever.get_relevant_documents(search_query)

    menu_context = "\n".join([f"메뉴 {i+1}: {doc.page_content}" for i, doc in enumerate(relevant_menus)])
    parser = PydanticOutputParser(pydantic_object=MenuRecommendation)

    prompt_template = ChatPromptTemplate.from_template("""
당신은 사용자의 상황과 건강 정보를 고려하여 최적의 메뉴를 추천하는 AI입니다.

[사용자 정보]
사용자명: {username}
알레르기: {allergies}
질병: {diseases}
선호 메뉴: {preferences}
비선호 메뉴: {dislikes}
날씨: {weather}
혼밥 여부: {alone}
예산: {budget}
기분: {mood}
이전 추천 메뉴: {previous_recommendations}

[관련 메뉴 정보]
{menu_context}

{format_instructions}
""")

    prompt = prompt_template.format(
        username=input_data.username,
        allergies=", ".join(input_data.allergies) or "없음",
        diseases=", ".join(input_data.diseases) or "없음",
        preferences=", ".join(input_data.preferences) or "없음",
        dislikes=", ".join(input_data.dislikes) or "없음",
        weather=input_data.weather,
        alone=input_data.alone,
        budget=input_data.budget,
        mood=input_data.mood or "정보 없음",
        previous_recommendations=", ".join(input_data.previous_recommendations) or "없음",
        menu_context=menu_context,
        format_instructions=parser.get_format_instructions()
    )

    try:
        response = llm.invoke(prompt)

        if not response.content.strip():
            return {"recommended_menu": "추천 실패", "recommendation_reason": "AI 응답이 비어있습니다.", "alternative_options": []}

        parsed_response = parser.parse(response.content)
        return parsed_response.dict()

    except Exception as e:
        result_text = getattr(response, "content", "").strip() if 'response' in locals() else ""

        return {
            "recommended_menu": "추천 처리 중 오류 발생",
            "recommendation_reason": f"오류: {str(e)} | 응답 내용: {result_text}",
            "alternative_options": []
        }

@router.post("/user-feedback")
def record_user_feedback(feedback_data: dict, db: Session = Depends(get_db)):
    username = feedback_data.get("username")
    menu_name = feedback_data.get("menu_name")
    rating = feedback_data.get("rating")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return {"status": "success", "message": "피드백이 성공적으로 저장되었습니다."}

@router.post("/chat")
def chat_with_menu_assistant(chat_data: dict):
    message = chat_data.get("message", "")
    chat_history = chat_data.get("history", [])

    context = "\n".join([f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history[-5:]])

    chat_prompt = ChatPromptTemplate.from_template("""
당신은 '오늘의 메뉴' 앱의 친절한 AI 비서입니다.

[이전 대화]
{context}

[사용자 메시지]
{message}

[지침]
1. 음식 관련 질문에 친절하게 응답하세요.
2. 메뉴 추천 요청 시 필요한 정보를 물어본 뒤 추천하세요.
3. 건강과 기분을 고려하세요.
""")

    prompt = chat_prompt.format(context=context, message=message)
    response = llm.invoke(prompt)

    return {"response": response.content}
