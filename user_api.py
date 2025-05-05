from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, UserAllergy, UserDisease, UserPreference, SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
