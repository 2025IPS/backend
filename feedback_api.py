from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal
from models import Feedback as FeedbackModel

router = APIRouter()

#  요청 바디 정의
class FeedbackRequest(BaseModel):
    place_name: str
    menu_name: str
    feedback: str  # "good" or "bad"
    user_id: int | None = None  # 로그인된 경우 전달, 아니면 생략

# DB 세션 종속성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#  피드백 저장 엔드포인트
@router.post("/feedback")
def receive_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
    new_feedback = FeedbackModel(
        user_id=data.user_id,
        place_name=data.place_name,
        menu_name=data.menu_name,
        feedback=data.feedback,
        created_at=datetime.utcnow()
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    return {
        "message": "피드백 저장 완료",
        "feedback_id": new_feedback.id
    }
