from sqlalchemy import Column, Integer, String, ForeignKey, Text, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
from sqlalchemy import DateTime  

Base = declarative_base()

# -------------------- 유저 --------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    name = Column(String)
    phone = Column(String)
    email = Column(String)

    allergies = relationship("UserAllergy", back_populates="user", cascade="all, delete-orphan")
    diseases = relationship("UserDisease", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")


# -------------------- 알레르기 --------------------
class UserAllergy(Base):
    __tablename__ = "user_allergy"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    allergy = Column(String)

    user = relationship("User", back_populates="allergies")


# -------------------- 지병 --------------------
class UserDisease(Base):
    __tablename__ = "user_disease"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    disease = Column(String)

    user = relationship("User", back_populates="diseases")


# -------------------- 음식 취향 --------------------
class UserPreference(Base):
    __tablename__ = "user_preference"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    preference_type = Column(String)  # 좋아요 / 싫어요
    menu_name = Column(String)

    user = relationship("User", back_populates="preferences")


# -------------------- 메뉴 --------------------
class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    place_name = Column(String)
    menu_name = Column(String)
    price = Column(Integer)
    category = Column(String)
    weather = Column(String)
    allergy = Column(String)

    reviews = relationship("Review", back_populates="menu", cascade="all, delete-orphan")


# -------------------- 음식점 --------------------
class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    phone = Column(String)
    image_url = Column(String)

    reviews = relationship("Review", back_populates="restaurant", cascade="all, delete-orphan")


# -------------------- 리뷰 --------------------
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    menu_id = Column(Integer, ForeignKey("menus.id"))
    rating = Column(Integer)
    tags = Column(String)  # "가성비, 빨리 나와요" 등 문자열로 저장
    comment = Column(Text)

    user = relationship("User", back_populates="reviews")
    restaurant = relationship("Restaurant", back_populates="reviews")
    menu = relationship("Menu", back_populates="reviews")

# -------------------- 피드백 --------------------
class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    place_name = Column(String, nullable=False)
    menu_name = Column(String, nullable=False)
    feedback = Column(String, nullable=False)  # "good" or "bad"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="feedbacks")


# -------------------- DB 연결 설정 --------------------
DATABASE_URL = "sqlite:///./test.db"  # SQLite

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 테이블 생성
Base.metadata.create_all(bind=engine)

