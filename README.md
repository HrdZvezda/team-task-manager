# Team Task Manager

一個團隊協作的任務管理系統,支援專案管理、成員邀請、任務指派與狀態追蹤。

![專案截圖](screenshots/dashboard.png)

## 🚀 功能特色

### 使用者系統
- 使用者註冊與登入
- JWT Token 認證
- 密碼加密儲存 (bcrypt)

### 專案管理
- 建立、編輯、刪除專案
- 查看專案列表
- 專案描述與資訊管理

### 成員管理
- 邀請成員加入專案
- 角色權限管理 (管理員 / 一般成員)
- 移除成員功能

### 任務管理
- 在專案中建立任務
- 指派任務給成員
- 任務狀態追蹤 (待處理 / 進行中 / 已完成)
- 優先級設定 (低 / 中 / 高)
- 截止日期設定
- 任務篩選功能
- 自動記錄完成時間

### 權限控制
- 專案擁有者擁有完整權限
- 管理員可以管理成員和任務
- 一般成員只能查看和編輯任務
- 非成員無法訪問專案

## 🛠️ 技術棧

### 後端
- **框架:** Flask 3.1.2
- **資料庫:** SQLite (開發環境) / PostgreSQL (正式環境)
- **ORM:** SQLAlchemy 2.0.44
- **認證:** Flask-JWT-Extended 4.7.1
- **密碼加密:** Flask-Bcrypt 1.0.1
- **CORS:** Flask-CORS 6.0.1

### 前端
- **HTML5 + CSS3**
- **Vanilla JavaScript (無框架)**
- **Responsive Design**

### 開發工具
- Python 3.x
- Git & GitHub

## 📁 專案結構
```
team-task-manager/
├── app.py              # 主應用程式
├── models.py           # 資料庫模型
├── config.py           # 設定檔
├── auth.py             # 認證相關 API
├── projects.py         # 專案管理 API
├── tasks.py            # 任務管理 API
├── requirements.txt    # Python 套件依賴
├── view/              # 前端檔案
│   ├── html/
│   │   ├── index.html      # 登入/註冊頁
│   │   ├── dashboard.html  # 專案列表
│   │   └── project.html    # 專案詳情
│   └── style/
│       └── style.css       # 樣式檔
└── README.md
```

## 🚀 快速開始

### 環境需求
- Python 3.8 或以上
- pip

### 安裝步驟

1. **Clone 專案**
```bash
git clone https://github.com/你的帳號/team-task-manager.git
cd team-task-manager
```

2. **安裝依賴套件**
```bash
pip install -r requirements.txt
```

3. **啟動後端伺服器**
```bash
python app.py
```
後端會在 `http://127.0.0.1:8888` 運行

4. **啟動前端**

使用 VS Code Live Server:
- 右鍵點擊 `view/html/index.html`
- 選擇 "Open with Live Server"

或使用 Python HTTP Server:
```bash
cd view/html
python -m http.server 5500
```
前端會在 `http://127.0.0.1:5500` 運行

5. **開始使用**
- 打開瀏覽器,前往 `http://127.0.0.1:5500/index.html`
- 註冊新帳號
- 開始建立專案和任務!

## 📸 Screenshots

### 登入頁面
![登入頁面](screenshots/login.png)

### 專案列表
![專案列表](screenshots/dashboard.png)

### 專案詳情
![專案詳情](screenshots/project.png)

### 任務管理
![任務管理](screenshots/tasks.png)

## 📚 API 文件

### 認證 API

#### 註冊
```http
POST /auth/register
Content-Type: application/json

{
  "username": "John",
  "email": "john@example.com",
  "password": "password123"
}
```

#### 登入
```http
POST /auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "password123"
}

Response:
{
  "token": "eyJhbGc...",
  "user": { "id": 1, "username": "John", "email": "john@example.com" }
}
```

### 專案 API

#### 建立專案
```http
POST /projects
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Website Redesign",
  "description": "Redesign company website"
}
```

#### 查詢專案列表
```http
GET /projects
Authorization: Bearer {token}
```

#### 邀請成員
```http
POST /projects/{project_id}/members
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_email": "member@example.com",
  "role": "member"
}
```

### 任務 API

#### 建立任務
```http
POST /projects/{project_id}/tasks
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Design homepage",
  "description": "Create mockup using Figma",
  "assigned_to": 2,
  "priority": "high",
  "due_date": "2025-02-01"
}
```

#### 更新任務狀態
```http
PATCH /tasks/{task_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "in_progress"
}
```

完整 API 文件請參考:[API.md](API.md)

## 🔒 安全性

- 密碼使用 bcrypt 加密儲存
- JWT Token 認證機制
- CORS 保護
- SQL Injection 防護 (使用 SQLAlchemy ORM)
- XSS 防護 (前端輸入驗證)

## 🎯 未來改進方向

- [ ] 部署到雲端平台 (Render / Railway)
- [ ] 新增即時通知功能
- [ ] 任務評論功能
- [ ] 檔案上傳功能
- [ ] 任務標籤系統
- [ ] Email 通知
- [ ] 移動端 App (React Native)
- [ ] 完整的測試覆蓋率

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request!

## 📝 License

MIT License

## 👤 作者

**你的名字**
- GitHub: [@你的帳號](https://github.com/你的帳號)
- Email: HrdZvezda@gmail.com

## 🙏 致謝

感謝所有使用和支持這個專案的人!

---

⭐ 如果這個專案對你有幫助,請給個 Star!