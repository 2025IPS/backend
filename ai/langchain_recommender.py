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
from models import User, SessionLocal

router = APIRouter(prefix="/menu")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")

MENU_DB_PATH = "./chroma_db/menu_db"

llm = ChatOpenAI(model_name="gpt-4o", temperature=0.7, api_key=OPENAI_API_KEY)

class MenuRecommendation(BaseModel):
    recommended_menu: str = Field(description="추천된 메뉴")
    recommendation_reason: str = Field(description="추천 이유")
    alternative_options: List[str] = Field(description="대체 옵션")

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def initialize_menu_db():
    sample_menus = [
        {"name": "김치찌개", "ingredients": ["김치", "돼지고기"], "type": "한식", "price_range": "중간"},
        {"name": "비빔밥", "ingredients": ["쌀", "나물"], "type": "한식", "price_range": "중간"},
        {"name": "스테이크", "ingredients": ["소고기"], "type": "양식", "price_range": "높음"},
    ]

    documents = []
    for menu in sample_menus:
        content = f"이름: {menu['name']}\n종류: {menu['type']}\n재료: {', '.join(menu['ingredients'])}\n가격대: {menu['price_range']}"
        doc = Document(page_content=content, metadata=menu)
        documents.append(doc)

    embedding_function = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    db = Chroma.from_documents(documents, embedding_function, persist_directory=MENU_DB_PATH)
    db.persist()
    return db

try:
    menu_db = Chroma(persist_directory=MENU_DB_PATH, embedding_function=OpenAIEmbeddings(api_key=OPENAI_API_KEY))
    menu_retriever = menu_db.as_retriever(search_kwargs={"k": 5})
except:
    menu_db = initialize_menu_db()
    menu_retriever = menu_db.as_retriever(search_kwargs={"k": 5})

@router.post("/llm-recommend")
def llm_recommend(input_data: LLMRecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == input_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 음식과 무관한 기분 입력 차단
    irrelevant_keywords = ["심심", "뭐해", "ㅎㅇ", "하이", "안녕", "노잼", "ㅋㅋ", "ㅎㅎ", "hi", "hello", "bored"]
    if input_data.mood and any(k in input_data.mood.lower() for k in irrelevant_keywords):
        return {
            "recommended_menu": "추천 불가",
            "recommendation_reason": "저는 음식 추천만 도와드릴 수 있어요. 음식 관련 요청을 해주세요 :)",
            "alternative_options": []
        }
    
    input_data.allergies = input_data.allergies or [a.allergy for a in user.allergies]
    input_data.diseases = input_data.diseases or [d.disease for d in user.diseases]
    input_data.preferences = input_data.preferences or [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    input_data.dislikes = input_data.dislikes or [p.menu_name for p in user.preferences if p.preference_type == "비선호"]

    search_query = f"예산: {input_data.budget} 날씨: {input_data.weather} 선호: {', '.join(input_data.preferences)}"
    relevant_menus = menu_retriever.get_relevant_documents(search_query)
    
    menu_context = "\n".join([f"메뉴 {i+1}: {doc.page_content}" for i, doc in enumerate(relevant_menus)])

    parser = PydanticOutputParser(pydantic_object=MenuRecommendation)

    prompt_template = ChatPromptTemplate.from_template("""
You are a helpful AI that recommends meals considering health conditions, allergies, preferences, mood, and weather.

[User Information]
- Username: {username}
- Allergies: {allergies}
- Diseases: {diseases}
- Preferences: {preferences}
- Dislikes: {dislikes}
- Weather: {weather}
- Eating Alone: {alone}
- Budget: {budget}
- Mood: {mood}
- Previous Recommendations: {previous_recommendations}

[Relevant Menu Data]
{menu_context}

[Instructions]
1. Avoid allergens and inappropriate ingredients for the user's health conditions.
2. Consider their preferences, mood, budget, and weather.
3. Do not recommend previous menus again.
4. Recommend **one main menu** with a brief explanation (1–2 sentences).
5. Also suggest **2–3 alternative options**.
6. Follow the output format exactly as described below.

{format_instructions}
""")

    prompt = prompt_template.format(
        username=input_data.username,
        allergies=", ".join(input_data.allergies),
        diseases=", ".join(input_data.diseases),
        preferences=", ".join(input_data.preferences),
        dislikes=", ".join(input_data.dislikes),
        weather=input_data.weather,
        alone=input_data.alone,
        budget=input_data.budget,
        mood=input_data.mood or "정보 없음",
        previous_recommendations=", ".join(input_data.previous_recommendations),
        menu_context=menu_context,
        format_instructions=parser.get_format_instructions()
    )

    try:
        response = llm.invoke(prompt)
        parsed = parser.parse(response.content)
        return parsed.dict()
    except Exception as e:
        return {
            "recommended_menu": "추천 실패",
            "recommendation_reason": f"오류 발생: {str(e)}",
            "alternative_options": []
        }
