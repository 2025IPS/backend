from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal
from models import Feedback as FeedbackModel, Menu
import os

# FastAPI용 라우터 객체
router = APIRouter()

print("✅ feedback_api.py 로드됨")
print("✅ feedback_api 위치:", os.path.abspath(__file__))

# 요청 모델
class FeedbackRequest(BaseModel):
    place_name: str
    menu_name: str
    feedback: str  # "good" or "bad"
    user_id: int | None = None
    menu_id: int | None = None
    restaurant_id: int | None = None

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# POST /api/feedback
@router.post("/feedback")
def receive_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
    print("📥 피드백 요청 수신:", data)

    # user_id가 없으면 에러
    if not data.user_id:
        raise HTTPException(status_code=400, detail="user_id가 누락되었습니다. 로그인 후 시도해주세요.")

    # menu_id 기준으로 메뉴 존재 여부 확인
    matched_menu = db.query(Menu).filter(Menu.id == data.menu_id).first()

    if not matched_menu:
        raise HTTPException(status_code=404, detail="해당 menu_id로 메뉴를 찾을 수 없습니다.")

    # 피드백 저장
    new_feedback = FeedbackModel(
        user_id=data.user_id,
        place_name=data.place_name,
        menu_name=data.menu_name,
        feedback=data.feedback,
        created_at=datetime.utcnow(),
        menu_id=matched_menu.id,
        restaurant_id=matched_menu.restaurant_id
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    return {
        "message": "피드백 저장 완료",
        "feedback_id": new_feedback.id
    }
