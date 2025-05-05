from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import SessionLocal, Review, User, Menu, Restaurant
from pydantic import BaseModel

router = APIRouter()

class ReviewRequest(BaseModel):
    username: str
    restaurant_id: int
    menu_id: int
    rating: int
    tags: str
    comment: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/review")
def create_review(review: ReviewRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == review.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_review = Review(
        user_id=user.id,
        restaurant_id=review.restaurant_id,
        menu_id=review.menu_id,
        rating=review.rating,
        tags=review.tags,
        comment=review.comment
    )
    db.add(new_review)
    db.commit()

    return {"msg": "리뷰 저장 완료!"}
