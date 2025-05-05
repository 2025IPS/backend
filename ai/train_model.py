import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split

# 데이터 예시 (User 데이터 + Menu 데이터)
user_data = [
    {
        "allergies": ["달걀", "갑각류"],
        "diseases": ["고혈압"],
        "prefers": ["매운 음식"],
        "dislikes": ["기름진 음식"],
        "weather": "맑음",
        "solo": 1,
        "budget": 10000,
        "menu": "순두부"
    },
    {
        "allergies": [],
        "diseases": [],
        "prefers": ["담백한 음식"],
        "dislikes": ["짠 음식"],
        "weather": "비",
        "solo": 0,
        "budget": 8000,
        "menu": "비빔밥"
    },
]

# 메뉴 리스트
menus = ["순두부", "비빔밥", "삼계탕", "불고기백반"]

# 알러지, 지병, 선호, 비선호 가능한 것들 (모델 통일성 위해 미리 고정)
allergies_list = ["달걀", "갑각류", "밀", "땅콩/대두", "우유"]
diseases_list = ["고혈압", "저혈압", "당뇨"]
pref_menu_list = ["매운 음식", "담백한 음식", "기름진 음식", "짠 음식"]
weather_list = ["맑음", "흐림", "비", "더움"]

# 인코더 준비
mlb_allergy = MultiLabelBinarizer(classes=allergies_list)
mlb_disease = MultiLabelBinarizer(classes=diseases_list)
mlb_prefer = MultiLabelBinarizer(classes=pref_menu_list)
mlb_weather = MultiLabelBinarizer(classes=weather_list)
mlb_menu = MultiLabelBinarizer(classes=menus)

X = []
y = []

for user in user_data:
    # 인코딩
    allergy_encoded = mlb_allergy.fit_transform([user["allergies"]])[0]
    disease_encoded = mlb_disease.fit_transform([user["diseases"]])[0]
    prefer_encoded = mlb_prefer.fit_transform([user["prefers"]])[0]
    dislike_encoded = mlb_prefer.fit_transform([user["dislikes"]])[0]
    weather_encoded = mlb_weather.fit_transform([[user["weather"]]])[0]
    solo_encoded = [user["solo"]]
    budget_encoded = [user["budget"] / 10000]  # 정규화

    input_vector = list(allergy_encoded) + list(disease_encoded) + list(prefer_encoded) + list(dislike_encoded) + list(weather_encoded) + solo_encoded + budget_encoded
    X.append(input_vector)

    # 메뉴
    y.append(mlb_menu.fit_transform([[user["menu"]]])[0])

X = torch.tensor(X, dtype=torch.float32)
y = torch.tensor(y, dtype=torch.float32)

# 모델 정의
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

INPUT_DIM = X.shape[1]
OUTPUT_DIM = y.shape[1]

model = MenuRecommender(INPUT_DIM, 64, OUTPUT_DIM)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

# CrossEntropyLoss expects labels as class index → argmax 필요
y_class = torch.argmax(y, dim=1)

# 학습
for epoch in range(1000):
    model.train()
    outputs = model(X)
    loss = criterion(outputs, y_class)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if (epoch+1) % 200 == 0:
        print(f"Epoch {epoch+1}, Loss: {loss.item()}")

# 저장
torch.save(model.state_dict(), "./ai/menu_model.pth")
print("모델 저장 완료")
