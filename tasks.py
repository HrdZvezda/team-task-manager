from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, Task, Project, ProjectMember
from auth import get_current_user
from projects import check_project_access
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__)

# ============ 輔助函數 ============

def check_task_access(task_id, user_id):
    """檢查使用者是否有權限訪問任務"""
    task = Task.query.get(task_id)
    
    if not task:
        return False, None
    
    # 檢查是否有專案訪問權限
    has_access, project, role = check_project_access(task.project_id, user_id)
    
    return has_access, task

# ============ 建立任務 ============

@tasks_bp.route('/projects/<int:project_id>/tasks', methods=['POST'])
@jwt_required()
def create_task(project_id):
    """在專案中建立任務"""
    current_user = get_current_user()
    
    # 檢查專案訪問權限
    has_access, project, role = check_project_access(project_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # 驗證必填欄位
    if not data.get('title') or not data['title'].strip():
        return jsonify({'error': 'Task title is required'}), 400
    
    # 建立任務
    task = Task(
        title=data['title'].strip(),
        description=data.get('description', '').strip() or None,
        project_id=project_id,
        created_by=current_user.id,
        assigned_to=data.get('assigned_to'),  # 可選:指派給某人
        status=data.get('status', 'todo'),  # 預設是 todo
        priority=data.get('priority', 'medium')  # 預設是 medium
    )
    
    # 如果有 due_date,轉換格式
    if data.get('due_date'):
        try:
            task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid due_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'}), 400
    
    # 驗證 assigned_to 是否是專案成員
    if task.assigned_to:
        is_member = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=task.assigned_to
        ).first()
        
        if not is_member:
            return jsonify({'error': 'Assigned user is not a member of this project'}), 400
    
    try:
        db.session.add(task)
        db.session.commit()
        
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
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============ 查詢專案的所有任務 ============

@tasks_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def get_project_tasks(project_id):
    """查詢專案的任務列表 (支援篩選)"""
    current_user = get_current_user()
    
    # 檢查專案訪問權限
    has_access, project, role = check_project_access(project_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    # 基本查詢
    query = Task.query.filter_by(project_id=project_id)
    
    # 篩選:按狀態
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    # 篩選:按負責人
    assigned_to = request.args.get('assigned_to')
    if assigned_to:
        query = query.filter_by(assigned_to=int(assigned_to))
    
    # 篩選:按優先級
    priority = request.args.get('priority')
    if priority:
        query = query.filter_by(priority=priority)
    
    # 排序:預設按建立時間降序
    tasks = query.order_by(Task.created_at.desc()).all()
    
    tasks_list = []
    for task in tasks:
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
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
        }
        tasks_list.append(task_data)
    
    return jsonify({
        'tasks': tasks_list,
        'total': len(tasks_list)
    }), 200

# ============ 查詢我的所有任務 ============

@tasks_bp.route('/tasks/my', methods=['GET'])
@jwt_required()
def get_my_tasks():
    """查詢我負責的所有任務 (跨專案)"""
    current_user = get_current_user()
    
    # 查詢指派給我的任務
    tasks = Task.query.filter_by(assigned_to=current_user.id).order_by(Task.created_at.desc()).all()
    
    tasks_list = []
    for task in tasks:
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'project': {
                'id': task.project.id,
                'name': task.project.name
            },
            'created_by': {
                'id': task.creator.id,
                'username': task.creator.username
            },
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat()
        }
        tasks_list.append(task_data)
    
    return jsonify({
        'tasks': tasks_list,
        'total': len(tasks_list)
    }), 200

# ============ 查詢單一任務 ============

@tasks_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """查詢任務詳細資訊"""
    current_user = get_current_user()
    
    # 檢查權限
    has_access, task = check_task_access(task_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied or task not found'}), 403
    
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'project': {
            'id': task.project.id,
            'name': task.project.name
        },
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
    }), 200

# ============ 更新任務 ============

@tasks_bp.route('/tasks/<int:task_id>', methods=['PATCH'])
@jwt_required()
def update_task(task_id):
    """更新任務資訊"""
    current_user = get_current_user()
    
    # 檢查權限
    has_access, task = check_task_access(task_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied or task not found'}), 403
    
    data = request.json
    
    # 更新標題
    if 'title' in data:
        if not data['title'] or not data['title'].strip():
            return jsonify({'error': 'Task title cannot be empty'}), 400
        task.title = data['title'].strip()
    
    # 更新描述
    if 'description' in data:
        task.description = data['description'].strip() or None
    
    # 更新狀態
    if 'status' in data:
        if data['status'] not in ['todo', 'in_progress', 'done']:
            return jsonify({'error': 'Invalid status. Must be "todo", "in_progress", or "done"'}), 400
        
        old_status = task.status
        task.status = data['status']
        
        # 如果改成 done,記錄完成時間
        if old_status != 'done' and data['status'] == 'done':
            task.completed_at = datetime.utcnow()
        # 如果從 done 改回其他狀態,清除完成時間
        elif old_status == 'done' and data['status'] != 'done':
            task.completed_at = None
    
    # 更新優先級
    if 'priority' in data:
        if data['priority'] not in ['low', 'medium', 'high']:
            return jsonify({'error': 'Invalid priority. Must be "low", "medium", or "high"'}), 400
        task.priority = data['priority']
    
    # 更新指派對象
    if 'assigned_to' in data:
        if data['assigned_to'] is None:
            task.assigned_to = None
        else:
            # 驗證是否是專案成員
            is_member = ProjectMember.query.filter_by(
                project_id=task.project_id,
                user_id=data['assigned_to']
            ).first()
            
            if not is_member:
                return jsonify({'error': 'Assigned user is not a member of this project'}), 400
            
            task.assigned_to = data['assigned_to']
    
    # 更新截止日期
    if 'due_date' in data:
        if data['due_date'] is None:
            task.due_date = None
        else:
            try:
                task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid due_date format'}), 400
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Task updated successfully',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'assigned_to': {
                    'id': task.assignee.id,
                    'username': task.assignee.username
                } if task.assigned_to else None,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============ 刪除任務 ============

@tasks_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """刪除任務"""
    current_user = get_current_user()
    
    # 檢查權限
    has_access, task = check_task_access(task_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied or task not found'}), 403
    
    # 只有建立者或專案管理員能刪除
    has_access, project, role = check_project_access(task.project_id, current_user.id)
    
    if task.created_by != current_user.id and role != 'admin':
        return jsonify({'error': 'Only task creator or project admin can delete task'}), 403
    
    try:
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'message': 'Task deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500