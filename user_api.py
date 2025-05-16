from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, UserAllergy, UserDisease, UserPreference, SessionLocal
from pydantic import BaseModel

# FastAPI Router 설정
router = APIRouter()

# DB 세션 생성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 전체 사용자 간단 정보 응답 모델
class UserSimple(BaseModel):
    id: int
    name: str
    username: str

    class Config:
        orm_mode = True

# 전체 사용자 목록 조회 API
@router.get("/users/all", response_model=list[UserSimple])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

# 개별 사용자 상세 정보 조회 API
@router.get("/user/{username}")
def get_user_info(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allergies = [a.allergy for a in user.allergies]
    diseases = [d.disease for d in user.diseases]
    prefers = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    dislikes = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]

    return {
        "username": user.username,
        "allergies": allergies,
        "diseases": diseases,
        "prefers": prefers,
        "dislikes": dislikes,
    }
