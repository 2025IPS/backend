from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import SessionLocal, User, UserAllergy, UserDisease, UserPreference
from pydantic import BaseModel

mypage_router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# 요청 받을 데이터 정의
# ---------------------------
class MypageUpdateRequest(BaseModel):
    username: str
    allergies: list[str]
    diseases: list[str]
    prefers: list[str]
    dislikes: list[str]

# ---------------------------
# 마이페이지 정보 업데이트 API
# ---------------------------
@mypage_router.post("/mypage/update")
def update_mypage(data: MypageUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 기존 데이터 삭제
    db.query(UserAllergy).filter(UserAllergy.user_id == user.id).delete()
    db.query(UserDisease).filter(UserDisease.user_id == user.id).delete()
    db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()

    # 새로 추가
    for allergy in data.allergies:
        db.add(UserAllergy(user_id=user.id, allergy=allergy))

    for disease in data.diseases:
        db.add(UserDisease(user_id=user.id, disease=disease))

    for prefer in data.prefers:
        db.add(UserPreference(user_id=user.id, preference_type="선호", menu_name=prefer))

    for dislike in data.dislikes:
        db.add(UserPreference(user_id=user.id, preference_type="비선호", menu_name=dislike))

    db.commit()

    return {"msg": "마이페이지 정보가 저장되었습니다."}

# ---------------------------
# 마이페이지 선호/비선호 정보 조회 API
# ---------------------------
@mypage_router.get("/mypage/{username}")
def get_user_preferences(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    preferences = db.query(UserPreference).filter(UserPreference.user_id == user.id).all()
    allergies = db.query(UserAllergy).filter(UserAllergy.user_id == user.id).all()
    diseases = db.query(UserDisease).filter(UserDisease.user_id == user.id).all()

    likes = [p.menu_name for p in preferences if p.preference_type == "선호"]
    dislikes = [p.menu_name for p in preferences if p.preference_type == "비선호"]
    allergy_list = [a.allergy for a in allergies]
    disease_list = [d.disease for d in diseases]

    return {
        "name": user.name,
        "preferences": {
            "likes": likes,
            "dislikes": dislikes,
            "allergies": allergy_list,
            "diseases": disease_list
        }
    }

