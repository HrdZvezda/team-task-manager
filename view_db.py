from flask import Flask
from models import db, User, Project, ProjectMember, Task

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///team_task.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    print("\n" + "=" * 60)
    print("資料庫內容")
    print("=" * 60)
    
    # 使用者
    users = User.query.all()
    print(f"\n【使用者】共 {len(users)} 筆:")
    for u in users:
        print(f"  ID: {u.id}, Email: {u.email}, Username: {u.username}")
    
    # 專案
    projects = Project.query.all()
    print(f"\n【專案】共 {len(projects)} 筆:")
    for p in projects:
        print(f"  ID: {p.id}, Name: {p.name}, Owner: {p.owner.username}")
    
    # 專案成員
    members = ProjectMember.query.all()
    print(f"\n【專案成員】共 {len(members)} 筆:")
    for m in members:
        print(f"  Project: {m.project.name}, User: {m.user.username}, Role: {m.role}")
    
    # 任務
    tasks = Task.query.all()
    print(f"\n【任務】共 {len(tasks)} 筆:")
    for t in tasks:
        print(f"  ID: {t.id}, Title: {t.title}, Status: {t.status}")
    
    print("\n" + "=" * 60)