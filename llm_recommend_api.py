from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import SessionLocal
from models import User
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import asyncio

load_dotenv()

router = APIRouter()

# Vector DB
menu_db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=OpenAIEmbeddings()
)
situation_db = Chroma(
    persist_directory="./chroma_situation_db",
    embedding_function=OpenAIEmbeddings()
)

# DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/llm-recommend-stream")
async def llm_recommend_stream(user_id: int, weather: str, situation: str, db: Session = Depends(get_db)):
    # 1. 사용자 정보 조회 및 프로필 구성
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return EventSourceResponse(iter(["data: 사용자 정보를 찾을 수 없습니다.\n\ndata: [END]\n\n"]))

    allergies = [a.allergy for a in user.allergies]
    diseases = [d.disease for d in user.diseases]

    user_profile = f"""
    [사용자 정보]
    - 지병: {', '.join(diseases) if diseases else '없음'}
    - 알레르기: {', '.join(allergies) if allergies else '없음'}
    """.strip()

    # 2. 상황 기반 DB 선택 및 입력 구성
    if situation in ["비오는 날", "추운 날", "더운 날", "스트레스 받을 때", "피곤할 때"]:
        retriever = situation_db.as_retriever(search_kwargs={"k": 3})
        context_input = (
            f"Situation: {situation}\n"
            f"{user_profile}\n"
            "Please recommend appropriate menus and explain why."
        )
    else:
        retriever = menu_db.as_retriever(search_kwargs={"k": 3})
        context_input = (
            f"{user_profile}\n"
            f"Weather: {weather}\n"
            f"Situation: {situation}\n\n"
            "Exclude allergens if mentioned. Recommend 2–3 menu items and explain each in 1–2 short sentences."
        )

    # 3. LLM 연결
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", streaming=True)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a concise and friendly AI assistant for the 'Today's Menu' app. "
         "Respond only to food-related questions or menu recommendations. "
         "If the input is unrelated (e.g., 'hello', 'I'm bored'), reply with: 'This service is only for menu recommendations.' "
         "Keep your answers within 3 sentences and use bullet points if possible."),
        ("user", "{input}")
    ])

    chain = prompt | llm

    # 4. SSE Generator
    async def event_generator():
        try:
            docs = await retriever.ainvoke(context_input)
            context = "\n".join([doc.page_content for doc in docs])
            full_input = f"{context_input}\n\n참고 정보:\n{context}"

            result = await llm.ainvoke(full_input)
            yield f"data: {result.content}\n\n"

        except Exception as e:
            yield f"data: 오류가 발생했습니다: {str(e)}\n\n"
        finally:
            yield "data: [END]\n\n"

    return EventSourceResponse(event_generator())
