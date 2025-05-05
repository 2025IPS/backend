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

# ✅ VectorDB 불러오기
menu_db = Chroma(persist_directory="./chroma_db", embedding_function=OpenAIEmbeddings())
situation_db = Chroma(persist_directory="./chroma_situation_db", embedding_function=OpenAIEmbeddings())

@router.get("/llm-recommend-stream")
async def llm_recommend_stream(user_profile: str, weather: str, situation: str):

    # 상황에 따라 적절한 Retriever 선택 및 context 설정
    if situation in ["비오는 날", "추운 날", "더운 날", "스트레스 받을 때", "피곤할 때"]:
        retriever = situation_db.as_retriever(search_kwargs={"k": 3})
        context_input = f"상황: {situation}\n{user_profile} 사용자에게 맞는 추천 메뉴와 이유를 알려줘."
    else:
        retriever = menu_db.as_retriever(search_kwargs={"k": 3})
        context_input = f"""
사용자 프로필: {user_profile}
날씨: {weather}
상황: {situation}

알러지를 제외하고 추천 가격, 추천 메뉴, 추천 이유를 알려주세요. 
가능하면 2~3가지 메뉴를 추천하고 이유를 1~2문장으로 알려주세요.
"""

    # ✅ LLM (gpt-3.5-turbo → 안정적으로 Streaming 가능)
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", streaming=True)

    # ✅ 프롬프트 구성
    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 상황과 사용자 정보를 기반으로 최적의 메뉴를 추천하는 친절한 AI입니다."),
        ("user", "{input}")
    ])

    chain = prompt | llm


    async def event_generator():
        try:
            docs = await retriever.ainvoke(context_input)
            retrieved_context = "\n".join([doc.page_content for doc in docs])

            full_input = f"{context_input}\n\n참고할 추가 정보:\n{retrieved_context}"

            # 일반 LLM 호출
            result = await llm.ainvoke(full_input)

            yield f"data: {result.content}\n\n"

        except Exception as e:
            yield f"data: 추천 중 오류가 발생했습니다. 다시 시도해주세요.\n\n"

        finally:
            yield "data: [END]\n\n"

    return EventSourceResponse(event_generator())
