from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 각 API import
from register import router as register_router
from ai.improved_ai_model import router as improved_ai_router
from ai.chatbot_integration import router as chatbot_router
from ai.langchain_recommender import router as langchain_recommend_router
from recommend_api import router as rule_recommend_router
from menu_recommend_api import router as menu_recommend_router
from review_api import router as review_router  # 선택적
from mypage_api import mypage_router  # 선택적
from llm_recommend_api import router as llm_recommend_router  # 쫩쫩이 LLM Streaming 추천

app = FastAPI(
    title="오늘의 먹방은 API",
    description="Frontend 연동용 API 서버",
    version="1.0.0"
)

# CORS 설정 (React 개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 프론트엔드 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📌 Router 등록
app.include_router(register_router, tags=["auth"])                   # 회원가입/로그인
app.include_router(improved_ai_router, tags=["ai-recommend"])        # 개선된 AI 추천
app.include_router(chatbot_router, tags=["chatbot"])                 # 챗봇 기반 대화
app.include_router(langchain_recommend_router, tags=["llm-recommend"]) # LangChain 기반 LLM 추천
app.include_router(rule_recommend_router, tags=["rule-recommend"])   # 룰기반 추천
app.include_router(menu_recommend_router, prefix="/api", tags=["menu-recommend"])  # 메뉴 추천 (일반)
app.include_router(review_router, tags=["review"])                   # 리뷰 관리 (선택)
app.include_router(mypage_router, tags=["mypage"])                   # 마이페이지 (선택)
app.include_router(llm_recommend_router, prefix="/api", tags=["llm-streaming"])    # 쫩쫩이 스트리밍 기반 추천

# 헬스 체크용 기본 라우트
@app.get("/")
def read_root():
    return {"message": "오늘의 먹방은 백엔드 정상 동작 중 🚀"}
