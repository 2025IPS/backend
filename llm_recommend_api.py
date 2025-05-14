from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import asyncio

load_dotenv()

router = APIRouter()

#  VectorDB 불러오기
menu_db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=OpenAIEmbeddings()
)
situation_db = Chroma(
    persist_directory="./chroma_situation_db",
    embedding_function=OpenAIEmbeddings()
)

@router.get("/llm-recommend-stream")
async def llm_recommend_stream(user_profile: str, weather: str, situation: str):
    # 상황 기반 DB 선택 및 입력 구성
    if situation in ["비오는 날", "추운 날", "더운 날", "스트레스 받을 때", "피곤할 때"]:
        retriever = situation_db.as_retriever(search_kwargs={"k": 3})
        context_input = (
            f"Situation: {situation}\n"
            f"User Profile: {user_profile}\n"
            "Please recommend appropriate menus and explain why."
        )
    else:
        retriever = menu_db.as_retriever(search_kwargs={"k": 3})
        context_input = (
            f"User Profile: {user_profile}\n"
            f"Weather: {weather}\n"
            f"Situation: {situation}\n\n"
            "Exclude allergens if mentioned. Recommend 2–3 menu items and explain each in 1–2 short sentences."
        )

    # GPT-3.5-turbo LLM with Streaming
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        streaming=True
    )

    # 영어 프롬프트 + 필터링 지침 포함
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a concise and friendly AI assistant for the 'Today's Menu' app. "
            "Respond only to food-related questions or menu recommendations. "
            "If the input is unrelated (e.g., 'hello', 'I'm bored'), reply with: 'This service is only for menu recommendations.' "
            "Keep your answers within 3 sentences and use bullet points if possible."
        ),
        (
            "user",
            "{input}"
        )
    ])

    chain = prompt | llm

    # SSE Event Generator
    async def event_generator():
        try:
            docs = await retriever.ainvoke(context_input)
            retrieved_context = "\n".join([doc.page_content for doc in docs])

            full_input = (
                f"{context_input}\n\n"
                f"Additional context:\n{retrieved_context}"
            )

            result = await llm.ainvoke(full_input)

            yield f"data: {result.content}\n\n"

        except Exception as e:
            yield f"data: An error occurred during recommendation. Please try again.\n\n"

        finally:
            yield "data: [END]\n\n"

    return EventSourceResponse(event_generator())
