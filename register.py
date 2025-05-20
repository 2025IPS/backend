from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, UserAllergy, UserDisease, UserPreference, SessionLocal
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------
# 데이터 모델 정의
# ----------------------

class UserCreate(BaseModel):
    username: str
    password: str
    confirm_password: str
    name: str
    phone: str = Field(..., pattern=r"^01[0-9]\d{7,8}$")  # 숫자만 허용, 예: 01012345678
    email: EmailStr

    @model_validator(mode="after")
    def check_password_match(self) -> "UserCreate":
        if self.password != self.confirm_password:
            raise ValueError("비밀번호와 비밀번호 재확인이 일치하지 않습니다.")
        return self

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: str
    allergies: Optional[str] = None
    diseases: Optional[str] = None
    preferred_menu: Optional[str] = None
    disliked_menu: Optional[str] = None

# ----------------------
# 회원가입
# ----------------------
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
    db.refresh(new_user)

    return {
        "msg": "User registered",
        "user_id": new_user.id,
        "username": new_user.username
    }

# ----------------------
# 로그인
# ----------------------
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return {
        "id": db_user.id,
        "username": db_user.username
    }

# ----------------------
# 사용자 정보 조회
# ----------------------
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

# ----------------------
# 사용자 정보 수정
# ----------------------
@router.post("/mypage/update")
def update_user(user_data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.allergies is not None:
        db.query(UserAllergy).filter(UserAllergy.user_id == user.id).delete()
        for allergy in user_data.allergies.split(","):
            db.add(UserAllergy(user_id=user.id, allergy=allergy.strip()))

    if user_data.diseases is not None:
        db.query(UserDisease).filter(UserDisease.user_id == user.id).delete()
        for disease in user_data.diseases.split(","):
            db.add(UserDisease(user_id=user.id, disease=disease.strip()))

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
