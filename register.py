from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, UserAllergy, UserDisease, UserPreference, SessionLocal
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 회원가입
class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: str
    allergies: Optional[str] = None  # "달걀,우유"
    diseases: Optional[str] = None   # "고혈압,당뇨"
    preferred_menu: Optional[str] = None  # "고기,버섯"
    disliked_menu: Optional[str] = None  # "버섯,굴"

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = pwd_context.hash(user.password)

    new_user = User(
        username=user.username,
        password=hashed_password,
        name=user.name,
        phone=user.phone,
        email=user.email
    )

    db.add(new_user)
    db.commit()

    return {"msg": "User registered"}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return {"username": db_user.username}

@router.get("/user/{username}")
def get_user(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allergies = [a.allergy for a in user.allergies]
    diseases = [d.disease for d in user.diseases]
    preferred_menu = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    disliked_menu = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]

    return {
        "username": user.username,
        "name": user.name,
        "phone": user.phone,
        "email": user.email,
        "allergies": allergies,
        "diseases": diseases,
        "preferred_menu": preferred_menu,
        "disliked_menu": disliked_menu
    }

@router.post("/mypage/update")
def update_user(user_data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. 알러지
    if user_data.allergies is not None:
        db.query(UserAllergy).filter(UserAllergy.user_id == user.id).delete()
        for allergy in user_data.allergies.split(","):
            db.add(UserAllergy(user_id=user.id, allergy=allergy.strip()))

    # 2. 지병
    if user_data.diseases is not None:
        db.query(UserDisease).filter(UserDisease.user_id == user.id).delete()
        for disease in user_data.diseases.split(","):
            db.add(UserDisease(user_id=user.id, disease=disease.strip()))

    # 3. 선호, 비선호 메뉴
    if user_data.preferred_menu is not None or user_data.disliked_menu is not None:
        db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()

        if user_data.preferred_menu:
            for menu in user_data.preferred_menu.split(","):
                db.add(UserPreference(user_id=user.id, preference_type="선호", menu_name=menu.strip()))

        if user_data.disliked_menu:
            for menu in user_data.disliked_menu.split(","):
                db.add(UserPreference(user_id=user.id, preference_type="비선호", menu_name=menu.strip()))

    db.commit()

    return {"msg": "User info updated"}
