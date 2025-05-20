from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 각 API import
from register import router as register_router
from ai.improved_ai_model import router as improved_ai_router
from ai.chatbot_integration import router as chatbot_router
from ai.langchain_recommender import router as langchain_recommend_router
from menu_recommend_api import router as menu_recommend_router
from review_api import router as review_router
from mypage_api import mypage_router
from llm_recommend_api import router as llm_recommend_router
from feedback_api import router as feedback_router
from user_api import router as user_router
from history_api import router as history_router

# FastAPI 앱 생성 함수
def create_app():
    app = FastAPI(
        title="오늘의 먹방은 API",
        description="Frontend 연동용 API 서버",
        version="1.0.0"
    )

    # CORS 미들웨어 먼저 등록
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://192.168.219.105:3000",  # ← 실제 핸드폰에서 접속 중인 프론트 주소
            "http://10.101.13.21:3000",
            "http://172.30.1.97:3000",
            "http://10.101.13.89:3000",
            "http://192.168.1.226:3000",
            "http://172.20.26.206:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(register_router, tags=["auth"])
    app.include_router(improved_ai_router, tags=["ai-recommend"])
    app.include_router(chatbot_router, tags=["chatbot"])
    app.include_router(langchain_recommend_router, tags=["llm-recommend"])
    app.include_router(menu_recommend_router, prefix="/api", tags=["menu-recommend"])
    app.include_router(review_router, prefix="/api", tags=["review"])
    app.include_router(mypage_router, tags=["mypage"])
    app.include_router(llm_recommend_router, prefix="/api", tags=["llm-streaming"])
    app.include_router(feedback_router, prefix="/api", tags=["feedback"])
    app.include_router(user_router, tags=["user"])
    app.include_router(history_router)

    # 기본 라우트
    @app.get("/")
    def read_root():
        return {"message": "오늘의 먹방은 백엔드 정상 동작 중"}

    return app

# FastAPI 앱 인스턴스 생성
app = create_app()

# ✅ 앱 실행 직후 등록된 경로들 출력
print("\n📌 등록된 라우터 경로 목록:")
for route in app.routes:
    print(f"{route.path} → {route.methods}")

