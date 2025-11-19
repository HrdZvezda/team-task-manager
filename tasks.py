from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import joinedload
from marshmallow import Schema, fields, validate, ValidationError
from models import db, Task, Project, ProjectMember, Notification, ActivityLog, TaskComment
from auth import get_current_user
from datetime import datetime
import logging

tasks_bp = Blueprint('tasks', __name__)
logger = logging.getLogger(__name__)

# ============================================
# Input Validation Schemas
# ============================================

class CreateTaskSchema(Schema):
    """建立任務驗證"""
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={'required': 'Task title is required'}
    )
    description = fields.Str(validate=validate.Length(max=5000))
    status = fields.Str(
        validate=validate.OneOf(['todo', 'in_progress', 'done']),
        missing='todo'
    )
    priority = fields.Str(
        validate=validate.OneOf(['low', 'medium', 'high']),
        missing='medium'
    )
    assigned_to = fields.Int(allow_none=True)
    due_date = fields.DateTime(allow_none=True)
    estimated_hours = fields.Float(allow_none=True)

class UpdateTaskSchema(Schema):
    """更新任務驗證"""
    title = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(validate=validate.Length(max=5000))
    status = fields.Str(validate=validate.OneOf(['todo', 'in_progress', 'done']))
    priority = fields.Str(validate=validate.OneOf(['low', 'medium', 'high']))
    assigned_to = fields.Int(allow_none=True)
    due_date = fields.DateTime(allow_none=True)
    estimated_hours = fields.Float(allow_none=True)
    actual_hours = fields.Float(allow_none=True)
    progress = fields.Int(validate=validate.Range(min=0, max=100))

# ============================================
# 輔助函數 (改進版)
# ============================================

def check_task_access(task_id, user_id):
    """
    檢查使用者是否有權限訪問任務
    
    改進點:
    1. 使用 eager loading
    2. 加上錯誤處理
    3. 回傳更多資訊
    """
    try:
        task = Task.query.options(
            joinedload(Task.project)
        ).get(task_id)
        
        if not task:
            return False, None, None
        
        # 檢查專案訪問權限
        from projects import check_project_access
        has_access, project, role = check_project_access(task.project_id, user_id)
        
        return has_access, task, role
        
    except Exception as e:
        logger.error(f"Error checking task access: {str(e)}", exc_info=True)
        return False, None, None

def validate_request_data(schema_class, data):
    """統一的輸入驗證"""
    schema = schema_class()
    try:
        validated_data = schema.load(data)
        return True, validated_data
    except ValidationError as err:
        return False, err.messages

def create_task_notification(task, action_type, actor_user, additional_users=None):
    """
    建立任務相關通知的輔助函數
    
    改進點:統一通知邏輯,避免重複代碼
    """
    notifications = []
    
    # 通知內容對應
    notification_config = {
        'assigned': {
            'type': 'task_assigned',
            'title': f'{actor_user.username} assigned a task to you',
            'content': f'Task: {task.title}'
        },
        'completed': {
            'type': 'task_completed',
            'title': f'{actor_user.username} completed a task',
            'content': f'Task: {task.title}'
        },
        'commented': {
            'type': 'comment_added',
            'title': f'{actor_user.username} commented on a task',
            'content': f'Task: {task.title}'
        }
    }
    
    config = notification_config.get(action_type)
    if not config:
        return notifications
    
    # 要通知的使用者列表
    notify_users = set()
    
    # 任務指派者
    if task.assigned_to and task.assigned_to != actor_user.id:
        notify_users.add(task.assigned_to)
    
    # 任務建立者
    if task.created_by != actor_user.id:
        notify_users.add(task.created_by)
    
    # 額外指定的使用者
    if additional_users:
        notify_users.update(additional_users)
    
    # 建立通知
    for user_id in notify_users:
        notification = Notification(
            user_id=user_id,
            type=config['type'],
            title=config['title'],
            content=config['content'],
            related_project_id=task.project_id,
            related_task_id=task.id
        )
        notifications.append(notification)
        db.session.add(notification)
    
    return notifications

# ============================================
# 建立任務 (改進版)
# ============================================

@tasks_bp.route('/projects/<int:project_id>/tasks', methods=['POST'])
@jwt_required()
def create_task(project_id):
    """
    在專案中建立任務
    
    改進點:
    1. 加上 input validation
    2. 統一 transaction
    3. 自動建立通知和活動日誌
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # 檢查專案訪問權限
    from projects import check_project_access
    has_access, project, role = check_project_access(project_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(CreateTaskSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 驗證 assigned_to 是否是專案成員
    if result.get('assigned_to'):
        is_member = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=result['assigned_to']
        ).first()
        
        if not is_member:
            return jsonify({'error': 'Assigned user is not a member of this project'}), 400
    
    # 建立任務
    task = Task(
        title=result['title'],
        description=result.get('description'),
        project_id=project_id,
        created_by=current_user.id,
        assigned_to=result.get('assigned_to'),
        status=result.get('status', 'todo'),
        priority=result.get('priority', 'medium'),
        due_date=result.get('due_date'),
        estimated_hours=result.get('estimated_hours')
    )
    
    try:
        db.session.add(task)
        db.session.flush()  # 取得 task.id
        
        # 建立通知 (如果有指派對象)
        if task.assigned_to and task.assigned_to != current_user.id:
            create_task_notification(task, 'assigned', current_user)
        
        # 建立活動日誌
        activity = ActivityLog(
            project_id=project_id,
            user_id=current_user.id,
            action='create_task',
            resource_type='task',
            resource_id=task.id,
            details={
                'title': task.title,
                'assigned_to': task.assigned_to,
                'priority': task.priority
            }
        )
        db.session.add(activity)
        
        # 一次性 commit
        db.session.commit()
        
        logger.info(f"Task created: {task.title} in project {project_id} by user {current_user.email}")
        
        # 使用 eager loading 取得關聯資料
        task = Task.query.options(
            joinedload(Task.assignee),
            joinedload(Task.creator)
        ).get(task.id)
        
        return jsonify({
            'message': 'Task created successfully',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'project_id': task.project_id,
                'assigned_to': {
                    'id': task.assignee.id,
                    'username': task.assignee.username
                } if task.assigned_to else None,
                'created_by': {
                    'id': task.creator.id,
                    'username': task.creator.username
                },
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'created_at': task.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Task creation error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Task creation failed due to server error'}), 500

# ============================================
# 查詢專案的所有任務 (改進版)
# ============================================

@tasks_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def get_project_tasks(project_id):
    """
    查詢專案的任務列表
    
    改進點:
    1. 使用 eager loading 避免 N+1
    2. 加上更多篩選選項
    3. 加上分頁
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # 檢查專案訪問權限
    from projects import check_project_access
    has_access, project, role = check_project_access(project_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # 基本查詢 (使用 eager loading)
        query = Task.query.filter_by(project_id=project_id).options(
            joinedload(Task.creator),
            joinedload(Task.assignee)
        )
        
        # 篩選: 按狀態
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)
        
        # 篩選: 按負責人
        assigned_to = request.args.get('assigned_to', type=int)
        if assigned_to:
            query = query.filter_by(assigned_to=assigned_to)
        
        # 篩選: 按優先級
        priority = request.args.get('priority')
        if priority:
            query = query.filter_by(priority=priority)
        
        # 篩選: 逾期任務
        overdue = request.args.get('overdue', type=bool)
        if overdue:
            query = query.filter(
                Task.due_date < datetime.utcnow(),
                Task.status != 'done'
            )
        
        # 排序
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        if sort_by == 'due_date':
            order_column = Task.due_date
        elif sort_by == 'priority':
            order_column = Task.priority
        else:
            order_column = Task.created_at
        
        if sort_order == 'asc':
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())
        
        # 分頁
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 100)
        
        tasks_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        tasks_list = [{
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'progress': task.progress,
            'created_by': {
                'id': task.creator.id,
                'username': task.creator.username
            },
            'assigned_to': {
                'id': task.assignee.id,
                'username': task.assignee.username
            } if task.assigned_to else None,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        } for task in tasks_paginated.items]
        
        return jsonify({
            'tasks': tasks_list,
            'total': tasks_paginated.total,
            'page': page,
            'per_page': per_page,
            'total_pages': tasks_paginated.pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch tasks'}), 500

# ============================================
# 更新任務 (改進版)
# ============================================

@tasks_bp.route('/tasks/<int:task_id>', methods=['PATCH'])
@jwt_required()
def update_task(task_id):
    """
    更新任務資訊
    
    改進點:
    1. 加上 input validation
    2. 記錄變更內容
    3. 自動通知相關人員
    4. 自動更新 completed_at
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # 檢查權限
    has_access, task, role = check_task_access(task_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied or task not found'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(UpdateTaskSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 驗證 assigned_to 是否是專案成員
    if 'assigned_to' in result and result['assigned_to']:
        is_member = ProjectMember.query.filter_by(
            project_id=task.project_id,
            user_id=result['assigned_to']
        ).first()
        
        if not is_member:
            return jsonify({'error': 'Assigned user is not a member of this project'}), 400
    
    # 記錄變更
    changes = {}
    old_status = task.status
    old_assigned_to = task.assigned_to
    
    # 更新欄位
    for field in ['title', 'description', 'status', 'priority', 'due_date', 
                  'estimated_hours', 'actual_hours', 'progress']:
        if field in result:
            old_value = getattr(task, field)
            new_value = result[field]
            if old_value != new_value:
                changes[field] = {'old': str(old_value), 'new': str(new_value)}
                setattr(task, field, new_value)
    
    # 特殊處理: assigned_to
    if 'assigned_to' in result:
        if task.assigned_to != result['assigned_to']:
            changes['assigned_to'] = {'old': task.assigned_to, 'new': result['assigned_to']}
            task.assigned_to = result['assigned_to']
    
    # 特殊處理: 狀態變更時自動更新 completed_at
    if 'status' in result:
        if old_status != 'done' and result['status'] == 'done':
            task.completed_at = datetime.utcnow()
            changes['completed_at'] = {'old': None, 'new': task.completed_at.isoformat()}
        elif old_status == 'done' and result['status'] != 'done':
            task.completed_at = None
            changes['completed_at'] = {'old': 'set', 'new': None}
    
    if not changes:
        return jsonify({'message': 'No changes to update'}), 200
    
    try:
        db.session.flush()
        
        # 建立通知
        # 1. 如果狀態變為 done,通知建立者
        if 'status' in changes and changes['status']['new'] == 'done':
            create_task_notification(task, 'completed', current_user)
        
        # 2. 如果 assigned_to 改變,通知新的負責人
        if 'assigned_to' in changes and task.assigned_to:
            create_task_notification(task, 'assigned', current_user)
        
        # 建立活動日誌
        activity = ActivityLog(
            project_id=task.project_id,
            user_id=current_user.id,
            action='update_task',
            resource_type='task',
            resource_id=task_id,
            details={'changes': changes}
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Task {task_id} updated by user {current_user.email}")
        
        # 重新載入 task 取得關聯資料
        task = Task.query.options(
            joinedload(Task.assignee),
            joinedload(Task.creator)
        ).get(task_id)
        
        return jsonify({
            'message': 'Task updated successfully',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'progress': task.progress,
                'assigned_to': {
                    'id': task.assignee.id,
                    'username': task.assignee.username
                } if task.assigned_to else None,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            },
            'changes': changes
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Task update error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Task update failed due to server error'}), 500

# ============================================
# 刪除任務 (改進版)
# ============================================

@tasks_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """
    刪除任務
    
    改進點:記錄刪除日誌
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # 檢查權限
    has_access, task, role = check_task_access(task_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied or task not found'}), 403
    
    # 只有建立者或專案管理員能刪除
    from projects import check_project_admin
    is_admin = check_project_admin(task.project_id, current_user.id)
    
    if task.created_by != current_user.id and not is_admin:
        return jsonify({'error': 'Only task creator or project admin can delete task'}), 403
    
    try:
        task_title = task.title
        project_id = task.project_id
        
        # 刪除任務 (cascade 會自動刪除評論等)
        db.session.delete(task)
        db.session.commit()
        
        logger.info(f"Task deleted: {task_title} by user {current_user.email}")
        
        return jsonify({
            'message': 'Task deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Task deletion error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Task deletion failed due to server error'}), 500

# ============================================
# 任務評論 (改進版)
# ============================================

class CreateCommentSchema(Schema):
    """評論驗證"""
    content = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=2000)
    )

@tasks_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@jwt_required()
def create_task_comment(task_id):
    """
    新增任務評論
    
    改進點:
    1. 加上 validation
    2. 統一 transaction
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    has_access, task, role = check_task_access(task_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(CreateCommentSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    try:
        comment = TaskComment(
            task_id=task_id,
            user_id=current_user.id,
            content=result['content']
        )
        db.session.add(comment)
        db.session.flush()
        
        # 建立通知
        create_task_notification(task, 'commented', current_user)
        
        # 建立活動日誌
        activity = ActivityLog(
            project_id=task.project_id,
            user_id=current_user.id,
            action='add_comment',
            resource_type='comment',
            resource_id=comment.id,
            details={'task_id': task_id, 'comment_preview': result['content'][:100]}
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Comment added to task {task_id} by user {current_user.email}")
        
        return jsonify({
            'message': 'Comment added successfully',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Comment creation error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to add comment due to server error'}), 500