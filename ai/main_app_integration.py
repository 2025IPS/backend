from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 라우터 임포트
from ai.llm_service import router as llm_router
from ai.langchain_recommender import router as langchain_router
from ai.improved_ai_model import router as ai_model_router
from ai.chatbot_integration import router as chatbot_router

# API 키 검증
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("경고: OPENAI_API_KEY가 설정되지 않았습니다.")

# FastAPI 앱 생성
app = FastAPI(title="오늘의 메뉴 API", version="1.0.0")

# CORS 설정
origins = [
    "http://localhost",
    "http://localhost:3000",  # React 프론트엔드
    "http://localhost:8080",  # Vue 프론트엔드
    "https://todaymenu.example.com",  # 프로덕션 URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(llm_router)
app.include_router(langchain_router)
app.include_router(ai_model_router)
app.include_router(chatbot_router)

@app.get("/")
async def root():
    return {
        "message": "오늘의 메뉴 API에 오신 것을 환영합니다!",
        "documentation": "/docs",
        "status": "운영 중"
    }

@app.get("/health")
async def health_check():
    """시스템 상태 확인 엔드포인트"""
    # 필요한 리소스 체크 로직 구현 가능
    return {
        "status": "healthy",
        "api_services": {
            "llm_service": "active",
            "langchain_recommender": "active",
            "ai_model": "active",
            "chatbot": "active"
        },
        "openai_api": "available" if OPENAI_API_KEY else "unavailable"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)