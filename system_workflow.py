# ============================================
# 團隊任務管理系統 - 完整運作流程
# ============================================

# ============================================
# 一、使用者註冊與登入流程
# ============================================

"""
1. 使用者註冊流程:

前端(瀏覽器)                    後端(Flask)                     資料庫
    │                              │                              │
    │ POST /auth/register          │                              │
    │ {email, password, username}  │                              │
    ├─────────────────────────────>│                              │
    │                              │ 1. 驗證必填欄位                │
    │                              │ 2. 檢查 email 是否存在         │
    │                              ├─────────────────────────────>│
    │                              │<─────────────────────────────┤
    │                              │ (查詢結果:email 不存在)        │
    │                              │                              │
    │                              │ 3. 用 bcrypt 加密密碼          │
    │                              │    "123456"                  │
    │                              │    ↓                         │
    │                              │    "$2b$12$KIX..."          │
    │                              │                              │
    │                              │ 4. 建立 User 物件             │
    │                              │    db.session.add()          │
    │                              │    db.session.commit()       │
    │                              ├─────────────────────────────>│
    │                              │                              │ (儲存使用者)
    │                              │<─────────────────────────────┤
    │<─────────────────────────────┤                              │
    │ 回傳: {message, user}         │                              │
    │                              │                              │

2. 使用者登入流程:

前端(瀏覽器)                    後端(Flask)                     資料庫
    │                              │                              │
    │ POST /auth/login             │                              │
    │ {email, password}            │                              │
    ├─────────────────────────────>│                              │
    │                              │ 1. 根據 email 查詢使用者       │
    │                              ├─────────────────────────────>│
    │                              │<─────────────────────────────┤
    │                              │ (取得 User 物件)              │
    │                              │                              │
    │                              │ 2. 驗證密碼                   │
    │                              │    bcrypt.check_password_hash()
    │                              │    資料庫: "$2b$12$KIX..."   │
    │                              │    使用者輸入: "123456"       │
    │                              │    ↓                         │
    │                              │    加密後比對                 │
    │                              │    ↓                         │
    │                              │    (密碼正確)                 │
    │                              │                              │
    │                              │ 3. 產生 JWT Token             │
    │                              │    create_access_token()     │
    │                              │    identity = user.id        │
    │                              │    ↓                         │
    │                              │    "eyJhbGciOiJIUzI1..."     │
    │<─────────────────────────────┤                              │
    │ 回傳: {token, user}           │                              │
    │                              │                              │
    │ 儲存 token 到 localStorage    │                              │
    │                              │                              │

3. 使用 Token 訪問受保護的路由:

前端(瀏覽器)                    後端(Flask)                     資料庫
    │                              │                              │
    │ GET /projects                │                              │
    │ Header:                      │                              │
    │ Authorization: Bearer token  │                              │
    ├─────────────────────────────>│                              │
    │                              │ @jwt_required() 裝飾器        │
    │                              │ 1. 檢查 Header 中的 token     │
    │                              │ 2. 驗證 token 簽章            │
    │                              │ 3. 檢查是否過期               │
    │                              │ 4. 解析出 user.id            │
    │                              │    get_jwt_identity()        │
    │                              │    ↓                         │
    │                              │    user_id = "5"             │
    │                              │                              │
    │                              │ 5. 執行業務邏輯               │
    │                              ├─────────────────────────────>│
    │                              │<─────────────────────────────┤
    │<─────────────────────────────┤                              │
    │ 回傳資料                       │                              │
    │                              │                              │
"""

# ============================================
# 二、專案管理流程
# ============================================

"""
1. 建立專案流程:

步驟 1:前端發送請求
    POST /projects
    Header: Authorization: Bearer <token>
    Body: {
        "name": "網站改版專案",
        "description": "公司官網全面改版"
    }

步驟 2:後端驗證 token,取得 current_user

步驟 3:建立 Project 物件
    project = Project(
        name="網站改版專案",
        description="公司官網全面改版",
        owner_id=current_user.id
    )
    db.session.add(project)
    db.session.commit()
    → 資料庫會自動產生 project.id = 1

步驟 4:自動將 owner 加為 admin 成員
    member = ProjectMember(
        project_id=1,
        user_id=current_user.id,
        role='admin'
    )
    db.session.add(member)
    db.session.commit()

步驟 5:回傳專案資訊
    {
        "message": "Project created successfully",
        "project": {
            "id": 1,
            "name": "網站改版專案",
            ...
        }
    }

2. 查詢我的專案流程:

步驟 1:前端發送請求
    GET /projects
    Header: Authorization: Bearer <token>

步驟 2:後端查詢 ProjectMember 表
    memberships = ProjectMember.query.filter_by(user_id=current_user.id).all()
    
    查詢結果(舉例):
    [
        {id: 1, user_id: 5, project_id: 1, role: 'admin'},
        {id: 2, user_id: 5, project_id: 3, role: 'member'}
    ]

步驟 3:透過 relationship 取得相關資料
    for membership in memberships:
        project = membership.project  ← 自動關聯到 Project 表
        
        # 因為在 models.py 中定義了:
        # ProjectMember.project = db.relationship('Project', backref='project')
        # 所以可以直接用 membership.project 取得專案物件

步驟 4:統計任務數量
    total_tasks = len(project.tasks)  ← 透過 relationship 取得所有任務
    completed_tasks = sum(1 for t in project.tasks if t.status == 'done')

步驟 5:回傳專案列表
"""

# ============================================
# 三、權限檢查機制
# ============================================

"""
權限檢查函數:check_project_access(project_id, user_id)

執行邏輯:
    1. 查詢專案
       project = Project.query.get(project_id)
    
    2. 檢查是否是 owner
       if project.owner_id == user_id:
           return True, project, 'admin'
    
    3. 檢查是否是成員
       member = ProjectMember.query.filter_by(
           project_id=project_id,
           user_id=user_id
       ).first()
       
       if member:
           return True, project, member.role
    
    4. 都不是
       return False, None, None

使用範例:
    has_access, project, role = check_project_access(5, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    # 繼續執行業務邏輯...
"""

# ============================================
# 四、任務管理流程
# ============================================

"""
1. 建立任務流程:

步驟 1:前端發送請求
    POST /projects/1/tasks
    Header: Authorization: Bearer <token>
    Body: {
        "title": "設計首頁",
        "description": "設計新版首頁的 UI",
        "assigned_to": 3,
        "priority": "high",
        "due_date": "2024-01-20T18:00:00"
    }

步驟 2:檢查專案權限
    has_access, project, role = check_project_access(1, current_user.id)

步驟 3:驗證 assigned_to 是專案成員
    is_member = ProjectMember.query.filter_by(
        project_id=1,
        user_id=3
    ).first()

步驟 4:建立任務
    task = Task(
        title="設計首頁",
        project_id=1,
        created_by=current_user.id,  ← 建立者
        assigned_to=3,                ← 被指派的人
        ...
    )
    db.session.add(task)
    db.session.commit()

步驟 5:回傳任務資訊
    {
        "task": {
            "id": 1,
            "assigned_to": {
                "id": 3,
                "username": "Designer Alice"
            },
            "created_by": {
                "id": 5,
                "username": "PM Bob"
            }
        }
    }

2. 更新任務狀態流程:

步驟 1:前端發送請求
    PATCH /tasks/1
    Body: {"status": "done"}

步驟 2:查詢任務並更新
    task = Task.query.get(1)
    old_status = task.status  # "in_progress"
    task.status = "done"

步驟 3:自動記錄完成時間
    if old_status != 'done' and task.status == 'done':
        task.completed_at = datetime.utcnow()

步驟 4:儲存變更
    db.session.commit()
"""

# ============================================
# 五、資料庫關聯的運作原理
# ============================================

"""
SQLAlchemy 的 relationship 如何運作?

1. 定義關聯(在 models.py 中):

    class User(db.Model):
        tasks_assigned = db.relationship('Task', 
                                       foreign_keys='Task.assigned_to',
                                       backref='assignee')
    
    class Task(db.Model):
        assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))

2. 實際使用:

    # 取得使用者
    user = User.query.get(5)
    
    # 自動查詢所有指派給這個使用者的任務
    user.tasks_assigned
    → SQLAlchemy 自動執行:
      SELECT * FROM task WHERE assigned_to = 5
    
    # 取得任務
    task = Task.query.get(1)
    
    # 自動查詢被指派的使用者
    task.assignee
    → SQLAlchemy 自動執行:
      SELECT * FROM user WHERE id = <task.assigned_to>

3. backref 的作用:

    backref='assignee' 表示:
    - 在 User 中定義 tasks_assigned
    - 自動在 Task 中建立 assignee 屬性
    - 形成「雙向關聯」

    正向:user.tasks_assigned → 取得使用者的所有任務
    反向:task.assignee → 取得任務的被指派者
"""

# ============================================
# 六、前端與後端的完整互動流程
# ============================================

"""
場景:使用者登入後建立專案,再建立任務

1. 使用者打開網頁
   → 前端檢查 localStorage 中是否有 token
   → 沒有 → 跳轉到登入頁面

2. 使用者登入
   → 前端送出 POST /auth/login
   → 後端驗證密碼,回傳 token
   → 前端儲存 token 到 localStorage
   → 跳轉到 dashboard

3. 載入專案列表
   → 前端送出 GET /projects
   → Header 帶上 token
   → 後端驗證 token,查詢專案
   → 回傳專案列表
   → 前端顯示在畫面上

4. 使用者點選「新增專案」
   → 前端顯示 modal
   → 使用者輸入專案名稱、描述
   → 前端送出 POST /projects
   → 後端建立專案
   → 回傳專案資訊
   → 前端重新載入專案列表

5. 使用者點選專案
   → 跳轉到 project.html?id=1
   → 前端送出 GET /projects/1
   → 後端查詢專案詳細資訊(包含成員、任務)
   → 回傳完整資訊
   → 前端顯示專案資訊、成員列表、任務列表

6. 使用者建立任務
   → 前端顯示新增任務 modal
   → 使用者選擇指派對象(從成員列表中選)
   → 前端送出 POST /projects/1/tasks
   → 後端建立任務
   → 回傳任務資訊
   → 前端重新載入專案資訊

7. 使用者更新任務狀態
   → 前端送出 PATCH /tasks/1
   → Body: {"status": "done"}
   → 後端更新任務,自動記錄完成時間
   → 前端重新載入任務列表
"""

# ============================================
# 七、常見的程式碼模式
# ============================================

"""
1. 查詢資料:

    # 根據主鍵查詢(最快)
    user = User.query.get(user_id)
    
    # 根據條件查詢(取第一筆)
    user = User.query.filter_by(email='test@example.com').first()
    
    # 根據條件查詢(取所有)
    tasks = Task.query.filter_by(status='todo').all()
    
    # 複合條件
    tasks = Task.query.filter_by(
        project_id=1,
        status='todo'
    ).order_by(Task.created_at.desc()).all()

2. 新增資料:

    # 建立物件
    user = User(email='test@example.com', ...)
    
    # 加入 session
    db.session.add(user)
    
    # 執行寫入
    db.session.commit()

3. 更新資料:

    # 查詢物件
    user = User.query.get(user_id)
    
    # 修改屬性
    user.username = 'New Name'
    
    # 執行寫入(不需要 add)
    db.session.commit()

4. 刪除資料:

    # 查詢物件
    project = Project.query.get(project_id)
    
    # 標記為刪除
    db.session.delete(project)
    
    # 執行刪除
    db.session.commit()

5. 錯誤處理:

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        # 發生錯誤,回滾操作
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
"""

# ============================================
# 八、HTTP 狀態碼的意義
# ============================================

"""
200 OK:請求成功
201 Created:資源建立成功
400 Bad Request:請求格式錯誤(例如缺少必填欄位)
401 Unauthorized:未授權(例如 token 無效)
403 Forbidden:禁止訪問(例如沒有權限)
404 Not Found:找不到資源
409 Conflict:資源衝突(例如 email 已存在)
500 Internal Server Error:伺服器內部錯誤
"""

print("""
這個系統的核心概念總結:

1. 資料模型(models.py):定義資料結構
   - User:使用者
   - Project:專案
   - ProjectMember:專案成員關係
   - Task:任務

2. 關聯設計:
   - 一對多:User → Projects (一個使用者擁有多個專案)
   - 多對多:User ↔ Project (透過 ProjectMember 中介表)
   - 一對多:Project → Tasks (一個專案有多個任務)

3. 權限控制:
   - JWT Token:驗證身份
   - Owner/Admin/Member:角色權限
   - 權限繼承:任務權限繼承自專案

4. API 設計:
   - RESTful:使用標準 HTTP 方法(GET/POST/PATCH/DELETE)
   - Blueprint:模組化路由管理
   - 統一錯誤處理:一致的錯誤回應格式

5. 前後端分離:
   - 前端:HTML/CSS/JavaScript(純前端)
   - 後端:Flask API(只回傳 JSON)
   - Token 驗證:無狀態認證
""")