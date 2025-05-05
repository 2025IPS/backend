from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import SessionLocal, Review, User, Menu, Restaurant
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# 리뷰 작성 요청 모델
class ReviewRequest(BaseModel):
    username: str
    restaurant_id: int
    menu_id: int
    rating: int
    tags: list[str]  # 예: ["좋아요", "가성비 좋아요"]
    comment: str

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 리뷰 작성 API
@router.post("/review")
def create_review(review: ReviewRequest, db: Session = Depends(get_db)):
    # 사용자 존재 확인
    user = db.query(User).filter(User.username == review.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 음식점 존재 확인
    restaurant = db.query(Restaurant).filter(Restaurant.id == review.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # 메뉴 존재 확인
    menu = db.query(Menu).filter(Menu.id == review.menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    # 리뷰 생성 및 저장
    new_review = Review(
        user_id=user.id,
        restaurant_id=review.restaurant_id,
        menu_id=review.menu_id,
        rating=review.rating,
        tags=",".join(review.tags),  # 리스트 → 문자열
        comment=review.comment
    )
    db.add(new_review)
    db.commit()

    return {"message": "리뷰 저장 완료!"}
