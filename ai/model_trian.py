# model_train.py

import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np

num_samples = 500
input_dim = 20   # 사용자 + 날씨 + 알러지 등 feature 수
output_dim = 50  # 메뉴의 총 개수

X = torch.randn(num_samples, input_dim)
Y = torch.randint(0, output_dim, (num_samples,))

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

model = MenuRecommender(input_dim, 64, output_dim)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 학습
for epoch in range(100):
    optimizer.zero_grad()
    outputs = model(X)
    loss = criterion(outputs, Y)
    loss.backward()
    optimizer.step()
    
    if epoch % 20 == 0:
        print(f"Epoch {epoch}, Loss: {loss.item()}")

# 모델 저장
torch.save(model.state_dict(), "menu_model.pth")
print("모델 저장 완료!")
