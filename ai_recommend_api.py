from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import User, SessionLocal
from pydantic import BaseModel
import torch
import torch.nn as nn

router = APIRouter()

# AI 모델
class MenuRecommender(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(MenuRecommender, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return self.softmax(x)

INPUT_DIM = 20
OUTPUT_DIM = 50

model = MenuRecommender(INPUT_DIM, 64, OUTPUT_DIM)
model.load_state_dict(torch.load("./ai/menu_model.pth"))
model.eval()

menu_list = [f"메뉴{i}" for i in range(OUTPUT_DIM)]

class AIRecommendRequest(BaseModel):
    username: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/ai_recommend")
def ai_recommend(request: AIRecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()

    allergies = [a.allergy for a in user.allergies]
    diseases = [d.disease for d in user.diseases]
    prefers = [p.menu_name for p in user.preferences if p.preference_type == "선호"]
    dislikes = [p.menu_name for p in user.preferences if p.preference_type == "비선호"]

    # 사용자 데이터 → 숫자 벡터 (예시로 단순화)
    user_data = [len(allergies), len(diseases), len(prefers), len(dislikes)] + [0] * (INPUT_DIM - 4)

    user_tensor = torch.tensor([user_data], dtype=torch.float32)

    with torch.no_grad():
        prediction = model(user_tensor)
        top_menu_index = torch.argmax(prediction).item()

    recommended_menu = menu_list[top_menu_index]

    return {"recommended_menu": recommended_menu}
