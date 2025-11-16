from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(225), nullable=False) # 會存加密後的hash
    username = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # association
    owned_projects = db.relationship('Project', backref='owner', lazy=True )
    # 1. 'tasks' 關聯被重新命名為 'tasks_assigned'，
    #    並使用 foreign_keys 明確指向 Task.assigned_to
    tasks_assigned = db.relationship('Task', foreign_keys='Task.assigned_to', backref='assignee', lazy=True)
    
    # 2. 我們新增一個關聯，用於 'created_by'
    tasks_created = db.relationship('Task', foreign_keys='Task.created_by', backref='creator', lazy=True)

     # ... (ProjectMember 的 backref 會自動建立 user.project_memberships)

# Project
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default= datetime.utcnow)

    # association
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all,delete-orphan')
    members = db.relationship('ProjectMember', backref='project', lazy=True, cascade='all,delete-orphan')

# ProjectMembers
class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member') # admin or member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # association
    user = db.relationship('User', backref='project_memberships')

    # 唯一性約束：同一個使用這不能在同一個專案裡重複加入
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_project_member'),)

# Task
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='todo') # todo, in progress, done
    priority = db.Column(db.String(20), nullable=False, default='medium') # low, medium, high

    # association
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # time
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
