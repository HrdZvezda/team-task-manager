
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ============================================
# 1. User 模型
# ============================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(225), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    
    # 新增欄位
    avatar_url = db.Column(db.String(500))
    bio = db.Column(db.Text)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯
    owned_projects = db.relationship('Project', backref='owner', lazy=True)
    tasks_assigned = db.relationship('Task', foreign_keys='Task.assigned_to', backref='assignee', lazy=True)
    tasks_created = db.relationship('Task', foreign_keys='Task.created_by', backref='creator', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all,delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)
    task_comments = db.relationship('TaskComment', backref='user', lazy=True)
    uploaded_files = db.relationship('Attachment', backref='uploader', lazy=True)
    created_templates = db.relationship('TaskTemplate', backref='creator', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

# ============================================
# 2. Project 模型
# ============================================
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # 新增欄位
    status = db.Column(db.String(20), default='active')  # active, archived, completed
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    budget = db.Column(db.Float)
    is_public = db.Column(db.Boolean, default=False)
    settings = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all,delete-orphan')
    members = db.relationship('ProjectMember', backref='project', lazy=True, cascade='all,delete-orphan')
    notifications = db.relationship('Notification', backref='project', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='project', lazy=True)
    attachments = db.relationship('Attachment', backref='project', lazy=True)
    tags = db.relationship('Tag', backref='project', lazy=True, cascade='all,delete-orphan')
    templates = db.relationship('TaskTemplate', backref='project', lazy=True)
    stat_snapshots = db.relationship('ProjectStatSnapshot', backref='project', lazy=True)

    # 索引
    __table_args__ = (
        db.Index('idx_project_status', 'status'),
        db.Index('idx_project_owner', 'owner_id'),
    )

# ============================================
# 3. ProjectMember 模型
# ============================================
class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # admin or member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯
    user = db.relationship('User', backref='project_memberships')

    # 唯一性約束
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='unique_project_member'),
    )

# ============================================
# 4. 多對多關聯表：任務與標籤
# ============================================
task_tags = db.Table('task_tags',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

# ============================================
# 5. Task 模型（增強版）
# ============================================
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='todo')  # todo, in_progress, done
    priority = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high
    
    # 新增欄位
    estimated_hours = db.Column(db.Float)  # 預估工時
    actual_hours = db.Column(db.Float)     # 實際工時
    progress = db.Column(db.Integer, default=0)  # 進度百分比 0-100

    # 關聯欄位
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # 時間欄位
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # 關聯
    tags = db.relationship('Tag', secondary=task_tags, backref='tasks')
    comments = db.relationship('TaskComment', backref='task', lazy=True, cascade='all,delete-orphan')
    attachments = db.relationship('Attachment', backref='task', lazy=True)
    notifications = db.relationship('Notification', backref='task', lazy=True)
    dependencies = db.relationship('TaskDependency', foreign_keys='TaskDependency.task_id', 
                                  backref='dependent_task', cascade='all,delete-orphan')

    # 索引
    __table_args__ = (
        db.Index('idx_task_project_status', 'project_id', 'status'),
        db.Index('idx_task_assigned_status', 'assigned_to', 'status'),
        db.Index('idx_task_due_date', 'due_date'),
        db.Index('idx_task_created_at', 'created_at'),
    )

# ============================================
# 6. Notification 模型（完整版）
# ============================================
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # task_assigned, comment_added, etc
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    related_project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    related_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# 7. ActivityLog 模型
# ============================================
class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# 8. TaskComment 模型
# ============================================
class TaskComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('task_comment.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_edited = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # 自我關聯（用於回覆）
    replies = db.relationship('TaskComment', backref=db.backref('parent', remote_side=[id]))

# ============================================
# 9. Attachment 模型
# ============================================
class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    file_url = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(100))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# 10. Tag 模型
# ============================================
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#667eea')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 唯一性約束
    __table_args__ = (
        db.UniqueConstraint('project_id', 'name', name='unique_project_tag'),
    )

# ============================================
# 11. TaskDependency 模型
# ============================================
class TaskDependency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    depends_on_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    dependency_type = db.Column(db.String(20), default='blocks')  # blocks, requires, relates_to
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 關聯
    depends_on = db.relationship('Task', foreign_keys=[depends_on_task_id])
    
    # 唯一性約束
    __table_args__ = (
        db.UniqueConstraint('task_id', 'depends_on_task_id', name='unique_dependency'),
    )

# ============================================
# 12. TaskTemplate 模型
# ============================================
class TaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    template_data = db.Column(db.JSON)
    is_public = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

# ============================================
# 13. AuditLog 模型
# ============================================
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    request_method = db.Column(db.String(10))
    request_path = db.Column(db.String(255))
    response_status = db.Column(db.Integer)
    details = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# 14. UserPreference 模型
# ============================================
class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # 通知設定
    email_notifications = db.Column(db.Boolean, default=True)
    push_notifications = db.Column(db.Boolean, default=True)
    notification_types = db.Column(db.JSON)
    
    # UI 設定
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='zh-TW')
    timezone = db.Column(db.String(50), default='Asia/Taipei')
    date_format = db.Column(db.String(20), default='YYYY-MM-DD')
    
    # 預設值
    default_task_view = db.Column(db.String(20), default='list')
    default_project_sort = db.Column(db.String(20), default='updated')
    
    # 其他設定
    settings = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # 關聯
    user = db.relationship('User', backref=db.backref('preference', uselist=False))

# ============================================
# 15. ProjectStatSnapshot 模型
# ============================================
class ProjectStatSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    # 統計資料
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    in_progress_tasks = db.Column(db.Integer, default=0)
    todo_tasks = db.Column(db.Integer, default=0)
    overdue_tasks = db.Column(db.Integer, default=0)
    member_count = db.Column(db.Integer, default=0)
    active_member_count = db.Column(db.Integer, default=0)
    
    # 平均值
    avg_task_completion_time = db.Column(db.Float)
    avg_tasks_per_member = db.Column(db.Float)
    
    # 詳細統計
    detailed_stats = db.Column(db.JSON)
    
    snapshot_date = db.Column(db.Date, default=datetime.utcnow().date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 唯一性約束
    __table_args__ = (
        db.UniqueConstraint('project_id', 'snapshot_date', name='unique_daily_snapshot'),
    )