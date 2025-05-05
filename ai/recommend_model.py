import torch
import torch.nn as nn
import pandas as pd
import numpy as np

# 데이터 불러오기 (메뉴명 추출용)
menu_df = pd.read_csv("../data/menu_price.csv")
nutrient_df = pd.read_csv("../data/menu_nutrient.csv")
merged = menu_df.merge(nutrient_df, left_on="menu_name", right_on="name", how="left")
menu_list = merged["menu_name"].tolist()

input_dim = 12
output_dim = len(menu_list)

class MenuRecommender(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(MenuRecommender, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

model = MenuRecommender(input_dim, 64, output_dim)
model.load_state_dict(torch.load("./menu_model.pth"))
model.eval()

def recommend(user_input):
    user_tensor = torch.tensor([user_input], dtype=torch.float32)
    with torch.no_grad():
        prediction = model(user_tensor)
        top_idx = torch.argmax(prediction).item()
    return menu_list[top_idx]

# 테스트 예
if __name__ == "__main__":
    test_input = [300, 50, 20, 10, 2, 5, 0, 800, 200, 1, 1, 1]  # 샘플
    result = recommend(test_input)
    print("추천 메뉴:", result)
