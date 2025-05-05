from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import Document
from models import User, UserAllergy, UserDisease, UserPreference, Menu, SessionLocal
import os
import json
from typing import List, Optional

router = APIRouter(prefix="/ai")

from dotenv import load_dotenv
import os


load_dotenv()
# 환경 변수
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

# LLM 세팅
llm = ChatOpenAI(model_name="gpt-4o", temperature=0.7, api_key=OPENAI_API_KEY)

# VectorDB 설정
MENU_DB_PATH = "./chroma_db/menu_db"

try:
    menu_db = Chroma(persist_directory=MENU_DB_PATH, embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY))
    menu_retriever = menu_db.as_retriever(search_kwargs={"k": 5})
except:
    menu_db = None
    menu_retriever = None

class MenuRecommendation(BaseModel):
    recommended_menu: str = Field(description="추천 메뉴")
    recommendation_reason: str = Field(description="추천 이유")
    alternative_options: List[str] = Field(description="대체 옵션")

class RecommendRequest(BaseModel):
    username: str
    weather: str
    alone: str
    budget: str
    mood: Optional[str] = None
    previous_recommendations: List[str] = []

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/recommend")
def recommend_menu(req: RecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    allergies = [a.allergy for a in user.allergies]
    diseases = [d.disease for d in user.diseases]
    preferences = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    dislikes = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]

    allergies_text = ", ".join(allergies) if allergies else "없음"
    diseases_text = ", ".join(diseases) if diseases else "없음"
    preferences_text = ", ".join(preferences) if preferences else "없음"
    dislikes_text = ", ".join(dislikes) if dislikes else "없음"
    previous_text = ", ".join(req.previous_recommendations) if req.previous_recommendations else "없음"

    if req.budget not in ["낮음", "중간", "높음"]:
        raise HTTPException(status_code=400, detail="예산은 낮음/중간/높음 중 하나여야 합니다.")

    if menu_retriever:
        search_query = f"예산: {req.budget} 날씨: {req.weather} 선호: {preferences_text}"
        relevant_menus = menu_retriever.get_relevant_documents(search_query)
        menu_context = "\n".join([f"메뉴 {i+1}: {doc.page_content}" for i, doc in enumerate(relevant_menus)])
    else:
        menu_context = "관련 메뉴 정보 없음"

    parser = PydanticOutputParser(pydantic_object=MenuRecommendation)

    prompt = ChatPromptTemplate.from_template("""
[사용자 정보]
- 사용자명: {username}
- 알레르기: {allergies}
- 질병: {diseases}
- 선호 메뉴: {preferences}
- 비선호 메뉴: {dislikes}
- 날씨: {weather}
- 혼밥 여부: {alone}
- 예산: {budget}
- 기분: {mood}
- 이전 추천 메뉴: {previous_recommendations}

[관련 메뉴 정보]
{menu_context}

[지침]
알레르기와 건강상태를 최우선으로 고려하고 날씨, 혼밥 여부, 예산 등을 종합해 메뉴를 추천하세요.

{format_instructions}
""")

    formatted_prompt = prompt.format(
        username=req.username,
        allergies=allergies_text,
        diseases=diseases_text,
        preferences=preferences_text,
        dislikes=dislikes_text,
        weather=req.weather,
        alone=req.alone,
        budget=req.budget,
        mood=req.mood or "정보 없음",
        previous_recommendations=previous_text,
        menu_context=menu_context,
        format_instructions=parser.get_format_instructions()
    )

    try:
        response = llm.invoke(formatted_prompt)
        result = parser.parse(response.content)
        return result.dict()
    except Exception as e:
        return {"recommended_menu": "추천 실패", "recommendation_reason": str(e), "alternative_options": []}
