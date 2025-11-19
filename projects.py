from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func, case, and_, or_
from marshmallow import Schema, fields, validate, ValidationError
from models import db, Project, ProjectMember, User, ActivityLog, Tag, Task
from auth import get_current_user
from datetime import datetime
import logging

projects_bp = Blueprint('projects', __name__)
logger = logging.getLogger(__name__)

# ============================================
# Input Validation Schemas
# ============================================

class CreateProjectSchema(Schema):
    """建立專案驗證"""
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={'required': 'Project name is required'}
    )
    description = fields.Str(validate=validate.Length(max=2000))
    start_date = fields.DateTime(allow_none=True)
    end_date = fields.DateTime(allow_none=True)

class UpdateProjectSchema(Schema):
    """更新專案驗證"""
    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(validate=validate.Length(max=2000))
    status = fields.Str(validate=validate.OneOf(['active', 'archived', 'completed']))

# ============================================
# 輔助函數 (改進版)
# ============================================

def check_project_access(project_id, user_id):
    """
    檢查使用者是否有權限訪問專案
    
    改進點:
    1. 加上 project 存在性檢查
    2. 使用單一查詢減少 DB 訪問
    3. 加上錯誤處理
    
    Returns:
        tuple: (has_access: bool, project: Project|None, role: str|None)
    """
    try:
        # 使用 joinedload 一次查詢拿到 project 和 member 資訊
        project = Project.query.options(
            joinedload(Project.owner)
        ).get(project_id)
        
        if not project:
            return False, None, None
        
        # 檢查是否為 owner
        if project.owner_id == user_id:
            return True, project, 'owner'
        
        # 檢查是否為 member
        member = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()
        
        if member:
            return True, project, member.role
        
        return False, None, None
        
    except Exception as e:
        logger.error(f"Error checking project access: {str(e)}", exc_info=True)
        return False, None, None

def check_project_admin(project_id, user_id):
    """
    檢查使用者是否為專案管理員
    
    改進點:加上錯誤處理和 project 存在性檢查
    """
    # try:
    #     project = Project.query.get(project_id)
        
    #     if not project:
    #         return False
        
    #     # Owner 視為 admin
    #     if project.owner_id == user_id:
    #         return True
        
    #     # 檢查 member role
    #     member = ProjectMember.query.filter_by(
    #         project_id=project_id,
    #         user_id=user_id,
    #         role='admin'
    #     ).first()
        
    #     return member is not None
        
    # except Exception as e:
    #     logger.error(f"Error checking project admin: {str(e)}", exc_info=True)
    #     return False
    try:
        project = Project.query.options(joinedload(Project.owner)).get(project_id)
        if not project:
            return False, None, None
        
        # 修正：Owner 視為 Admin 權限
        if project.owner_id == user_id:
            return True, project, 'admin'  # 這裡改成 admin 以配合前端邏輯
        
        member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
        if member:
            return True, project, member.role
        
        return False, None, None
    except Exception as e:
        logger.error(f"Error checking project access: {str(e)}", exc_info=True)
        return False, None, None

def validate_request_data(schema_class, data):
    """統一的輸入驗證"""
    schema = schema_class()
    try:
        validated_data = schema.load(data)
        return True, validated_data
    except ValidationError as err:
        return False, err.messages

# ============================================
# 建立專案 (改進版)
# ============================================

@projects_bp.route('', methods=['POST'])
@jwt_required()
def create_project():
    """
    建立新專案
    
    改進點:
    1. 加上 input validation
    2. 修正 transaction 管理 (使用單一 commit)
    3. 移除冗餘的 owner 作為 member (owner_id 就夠了)
    4. 加上活動日誌
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(CreateProjectSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 建立專案
    project = Project(
        name=result['name'],
        description=result.get('description'),
        owner_id=current_user.id,
        start_date=result.get('start_date'),
        end_date=result.get('end_date')
    )
    
    try:
        db.session.add(project)
        db.session.flush()  # 取得 project.id 但不 commit
        
        # 建立活動日誌
        activity = ActivityLog(
            project_id=project.id,
            user_id=current_user.id,
            action='create_project',
            resource_type='project',
            resource_id=project.id,
            details={'name': project.name}
        )
        db.session.add(activity)
        
        # 一次性 commit
        db.session.commit()
        
        logger.info(f"Project created: {project.name} by user {current_user.email}")
        
        return jsonify({
            'message': 'Project created successfully',
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'owner_id': project.owner_id,
                'created_at': project.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Project creation error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Project creation failed due to server error'}), 500

# ============================================
# 查詢我的所有專案 (改進版)
# ============================================

@projects_bp.route('', methods=['GET'])
@jwt_required()
def get_my_projects():
    """
    查詢我擁有或參與的所有專案
    
    改進點:
    1. 修正 N+1 查詢問題 (使用 subquery 統計)
    2. 使用 eager loading 減少查詢次數
    3. 加上分頁
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # 分頁參數
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # 限制最大值避免性能問題
    
    try:
        # 方法1: 使用 subquery 統計任務數量 (避免 N+1)
        task_stats = db.session.query(
            Task.project_id,
            func.count(Task.id).label('total_tasks'),
            func.sum(case((Task.status == 'done', 1), else_=0)).label('completed_tasks')
        ).group_by(Task.project_id).subquery()
        
        # 方法2: 統計成員數量
        member_stats = db.session.query(
            ProjectMember.project_id,
            func.count(ProjectMember.id).label('member_count')
        ).group_by(ProjectMember.project_id).subquery()
        
        # 查詢我擁有的專案
        owned_projects = db.session.query(
            Project,
            task_stats.c.total_tasks,
            task_stats.c.completed_tasks,
            member_stats.c.member_count
        ).outerjoin(
            task_stats, Project.id == task_stats.c.project_id
        ).outerjoin(
            member_stats, Project.id == member_stats.c.project_id
        ).filter(
            Project.owner_id == current_user.id
        ).options(
            joinedload(Project.owner)
        )
        
        # 查詢我參與的專案 (不是 owner 的)
        member_project_ids = db.session.query(ProjectMember.project_id).filter(
            ProjectMember.user_id == current_user.id
        ).subquery()
        
        member_projects = db.session.query(
            Project,
            task_stats.c.total_tasks,
            task_stats.c.completed_tasks,
            member_stats.c.member_count
        ).outerjoin(
            task_stats, Project.id == task_stats.c.project_id
        ).outerjoin(
            member_stats, Project.id == member_stats.c.member_count
        ).filter(
            and_(
                Project.id.in_(member_project_ids),
                Project.owner_id != current_user.id
            )
        ).options(
            joinedload(Project.owner)
        )
        
        # 合併查詢結果
        all_projects = owned_projects.union(member_projects).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        projects_list = []
        for project, total_tasks, completed_tasks, member_count in all_projects.items:
            # 判斷我的角色
            if project.owner_id == current_user.id:
                my_role = 'admin'  # 修正：Owner 在前端顯示與邏輯上等同 Admin
            else:
                membership = ProjectMember.query.filter_by(
                    project_id=project.id,
                    user_id=current_user.id
                ).first()
                my_role = membership.role if membership else None
            
            projects_list.append({
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'owner': {
                    'id': project.owner.id,
                    'username': project.owner.username
                },
                'my_role': my_role,
                'member_count': member_count or 0,
                'task_count': total_tasks or 0,
                'completed_task_count': completed_tasks or 0,
                'created_at': project.created_at.isoformat()
            })
        
        return jsonify({
            'projects': projects_list,
            'total': all_projects.total,
            'page': page,
            'per_page': per_page,
            'total_pages': all_projects.pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching projects: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch projects'}), 500

# ============================================
# 查詢單一專案 (改進版)
# ============================================

@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """
    查詢專案詳細資訊
    
    改進點:
    1. 使用 eager loading 避免 N+1
    2. 加上分頁 (tasks 可能很多)
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # 檢查權限
    has_access, project, role = check_project_access(project_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # 使用 eager loading 一次拿到所有需要的資料
        project = Project.query.options(
            joinedload(Project.owner),
            selectinload(Project.members).joinedload(ProjectMember.user)
        ).get(project_id)
        
        # 取得成員列表
        members = [{
            'id': membership.user.id,
            'username': membership.user.username,
            'email': membership.user.email,
            'role': membership.role,
            'joined_at': membership.joined_at.isoformat()
        } for membership in project.members]
        
        # 取得任務列表 (分頁)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        tasks_query = Task.query.filter_by(project_id=project_id).options(
            joinedload(Task.creator),
            joinedload(Task.assignee)
        ).order_by(Task.created_at.desc())
        
        tasks_paginated = tasks_query.paginate(page=page, per_page=per_page, error_out=False)
        
        tasks = [{
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'created_at': task.created_at.isoformat(),
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_by': {
                'id': task.creator.id,
                'username': task.creator.username
            },
            'assigned_to': {
                'id': task.assignee.id,
                'username': task.assignee.username
            } if task.assigned_to else None
        } for task in tasks_paginated.items]
        
        return jsonify({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'start_date': project.start_date.isoformat() if project.start_date else None,
            'end_date': project.end_date.isoformat() if project.end_date else None,
            'owner': {
                'id': project.owner.id,
                'username': project.owner.username
            },
            'my_role': role,
            'members': members,
            'tasks': tasks,
            'tasks_pagination': {
                'page': page,
                'per_page': per_page,
                'total': tasks_paginated.total,
                'total_pages': tasks_paginated.pages
            },
            'created_at': project.created_at.isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch project details'}), 500

# ============================================
# 更新專案 (改進版)
# ============================================

@projects_bp.route('/<int:project_id>', methods=['PATCH'])
@jwt_required()
def update_project(project_id):
    """
    更新專案資訊
    
    改進點:
    1. 加上 input validation
    2. 加上活動日誌
    3. 記錄變更內容
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # 檢查是否是 admin 或 owner
    if not check_project_admin(project_id, current_user.id):
        return jsonify({'error': 'Only admins can update project'}), 403
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(UpdateProjectSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 記錄變更
    changes = {}
    
    # 更新欄位
    for field in ['name', 'description', 'status']:
        if field in result:
            old_value = getattr(project, field)
            new_value = result[field]
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}
                setattr(project, field, new_value)
    
    if not changes:
        return jsonify({'message': 'No changes to update'}), 200
    
    try:
        # 建立活動日誌
        activity = ActivityLog(
            project_id=project_id,
            user_id=current_user.id,
            action='update_project',
            resource_type='project',
            resource_id=project_id,
            details={'changes': changes}
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Project {project_id} updated by user {current_user.email}")
        
        return jsonify({
            'message': 'Project updated successfully',
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status
            },
            'changes': changes
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Project update error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Project update failed due to server error'}), 500

# ============================================
# 刪除專案 (改進版)
# ============================================

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """
    刪除專案 (只有 owner 可以)
    
    改進點:
    1. 加上軟刪除選項 (可選)
    2. 記錄刪除日誌
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    # 只有 owner 能刪除
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Only project owner can delete the project'}), 403
    
    try:
        project_name = project.name
        
        # 刪除專案 (cascade 會自動刪除相關資料)
        db.session.delete(project)
        db.session.commit()
        
        logger.info(f"Project deleted: {project_name} by user {current_user.email}")
        
        return jsonify({
            'message': 'Project deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Project deletion error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Project deletion failed due to server error'}), 500

# ============================================
# 專案成員管理 (改進版)
# ============================================

class AddMemberSchema(Schema):
    """新增成員驗證"""
    user_id = fields.Int(required=True)
    role = fields.Str(validate=validate.OneOf(['admin', 'member']), missing='member')

@projects_bp.route('/<int:project_id>/members', methods=['GET'])
@jwt_required()
def get_project_members(project_id):
    """取得專案成員列表"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    has_access, project, role = check_project_access(project_id, current_user.id)
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # 使用 eager loading
        members = ProjectMember.query.filter_by(project_id=project_id).options(
            joinedload(ProjectMember.user)
        ).all()
        
        return jsonify({
            'members': [{
                'id': m.user.id,
                'username': m.user.username,
                'email': m.user.email,
                'role': m.role,
                'joined_at': m.joined_at.isoformat()
            } for m in members],
            'total': len(members)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching members: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch members'}), 500

@projects_bp.route('/<int:project_id>/members', methods=['POST'])
@jwt_required()
def add_project_member(project_id):
    """
    新增專案成員
    
    改進點:
    1. 加上 validation
    2. 建立通知
    3. 記錄活動
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    if not check_project_admin(project_id, current_user.id):
        return jsonify({'error': 'Only admins can add members'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(AddMemberSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 檢查使用者是否存在
    user = User.query.get(result['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # 檢查是否已是成員
    existing = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=result['user_id']
    ).first()
    
    if existing:
        return jsonify({'error': 'User is already a member'}), 409
    
    try:
        # 新增成員
        member = ProjectMember(
            project_id=project_id,
            user_id=result['user_id'],
            role=result['role']
        )
        db.session.add(member)
        db.session.flush()
        
        # 建立通知
        from models import Notification
        notification = Notification(
            user_id=result['user_id'],
            type='member_added',
            title=f'You were added to project',
            content=f'{current_user.username} added you to the project',
            related_project_id=project_id
        )
        db.session.add(notification)
        
        # 建立活動日誌
        activity = ActivityLog(
            project_id=project_id,
            user_id=current_user.id,
            action='add_member',
            resource_type='member',
            resource_id=result['user_id'],
            details={'username': user.username, 'role': result['role']}
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Member added to project {project_id}: user {user.email}")
        
        return jsonify({
            'message': 'Member added successfully',
            'member': {
                'id': user.id,
                'username': user.username,
                'role': member.role
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding member: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to add member due to server error'}), 500

# ============================================
# 專案統計 (新增)
# ============================================

@projects_bp.route('/<int:project_id>/stats', methods=['GET'])
@jwt_required()
def get_project_stats(project_id):
    """
    取得專案統計資訊
    
    使用高效的聚合查詢避免 N+1 問題
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    has_access, project, role = check_project_access(project_id, current_user.id)
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # 任務統計
        task_stats = db.session.query(
            func.count(Task.id).label('total'),
            func.sum(case((Task.status == 'todo', 1), else_=0)).label('todo'),
            func.sum(case((Task.status == 'in_progress', 1), else_=0)).label('in_progress'),
            func.sum(case((Task.status == 'done', 1), else_=0)).label('done'),
            func.sum(case((and_(Task.due_date < datetime.utcnow(), Task.status != 'done'), 1), else_=0)).label('overdue')
        ).filter(Task.project_id == project_id).first()
        
        # 成員數
        member_count = ProjectMember.query.filter_by(project_id=project_id).count()
        
        return jsonify({
            'tasks': {
                'total': task_stats.total or 0,
                'todo': task_stats.todo or 0,
                'in_progress': task_stats.in_progress or 0,
                'done': task_stats.done or 0,
                'overdue': task_stats.overdue or 0
            },
            'members': member_count,
            'completion_rate': round((task_stats.done or 0) / (task_stats.total or 1) * 100, 2)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch statistics'}), 500