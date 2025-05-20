from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Feedback, Review, RecommendationHistory
from typing import List

router = APIRouter()

# -----------------------
# DB 세션 주입 함수
# -----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------
# 히스토리 API: 추천받은 기록 + 피드백 + 리뷰 여부 포함
# -----------------------
@router.get("/history/{user_id}")
def get_recommendation_history(user_id: int, db: Session = Depends(get_db)):
    # 1. 내가 추천받은 모든 메뉴 (recommendation 기록 기준)
    recs = db.query(RecommendationHistory).filter(
        RecommendationHistory.user_id == user_id
    ).order_by(RecommendationHistory.created_at.desc()).all()

    result = []
    for rec in recs:
        # 2. 피드백 조회
        feedback_obj = db.query(Feedback).filter_by(
            user_id=user_id,
            menu_id=rec.menu_id,
            restaurant_id=rec.restaurant_id
        ).first()

        # 3. 싫어요 누른 경우는 제외
        if feedback_obj and feedback_obj.feedback == "bad":
            continue

        # 4. 리뷰 여부 확인
        is_reviewed = db.query(Review).filter_by(
            user_id=user_id,
            menu_id=rec.menu_id,
            restaurant_id=rec.restaurant_id
        ).first() is not None

        result.append({
            "place_name": rec.place_name,
            "menu_name": rec.menu_name,
            "menu_id": rec.menu_id,
            "restaurant_id": rec.restaurant_id,
            "created_at": rec.created_at,
            "feedback": feedback_obj.feedback if feedback_obj else None,
            "is_reviewed": is_reviewed
        })

    return result
