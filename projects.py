from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, ProjectMember, User
from auth import get_current_user

projects_bp = Blueprint('projects', __name__)


# ============ 輔助函數 ============
def check_project_access(project_id, user_id):

  """檢查使用者是否有權限訪問專案"""
  project = Project.query.get(project_id)
  
  # check is owner
  if project.owner_id == user_id:
    return True, project, 'admin'
  
  # check is member
  member = ProjectMember.query.filter_by(
    project_id = project_id,
    user_id = user_id
  ).first()

  if member:
    return True, project, member.role
  
  return False, None, None

def check_project_admin(project_id, user_id):
  
  """檢查使用者是否為專案管理員"""
  project = Project.query.get(project_id)

  # owner must be admin
  if project.owner_id == user_id:
    return True
  
  # check member role
  member = ProjectMember.query.filter_by(
      project_id=project_id,
      user_id=user_id
  ).first()
  
  return member and member.role == 'admin'


# ============ 建立專案 ============

@projects_bp.route('', methods=['POST'])
@jwt_required()
def create_project():
    """建立新專案"""
    current_user = get_current_user()
    data = request.json
    
    # 驗證必填欄位
    if not data.get('name') or not data['name'].strip():
        return jsonify({'error': 'Project name is required'}), 400
    
    # 建立專案
    project = Project(
        name=data['name'].strip(),
        description=data.get('description', '').strip() or None,
        owner_id=current_user.id
    )
    
    try:
        db.session.add(project)
        db.session.commit()
        
        # 自動將 owner 加為 admin 成員
        member = ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role='admin'
        )
        db.session.add(member)
        db.session.commit()
        
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
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============ 查詢我的所有專案 ============

@projects_bp.route('', methods=['GET'])
@jwt_required()
def get_my_projects():
    """查詢我擁有或參與的所有專案"""
    current_user = get_current_user()
    
    # 查詢我參與的所有專案 (透過 ProjectMember)
    memberships = ProjectMember.query.filter_by(user_id=current_user.id).all()
    
    projects_list = []
    for membership in memberships:
        project = membership.project
        
        # 統計任務數量
        total_tasks = len(project.tasks)
        completed_tasks = sum(1 for t in project.tasks if t.status == 'done')
        
        # 統計成員數量
        member_count = len(project.members)
        
        projects_list.append({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'owner': {
                'id': project.owner.id,
                'username': project.owner.username
            },
            'my_role': membership.role,
            'member_count': member_count,
            'task_count': total_tasks,
            'completed_task_count': completed_tasks,
            'created_at': project.created_at.isoformat()
        })
    
    return jsonify({
        'projects': projects_list,
        'total': len(projects_list)
    }), 200

# ============ 查詢單一專案 ============

@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """查詢專案詳細資訊"""
    current_user = get_current_user()
    
    # 檢查權限
    has_access, project, role = check_project_access(project_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    # 取得成員列表
    members = []
    for membership in project.members:
        members.append({
            'id': membership.user.id,
            'username': membership.user.username,
            'email': membership.user.email,
            'role': membership.role,
            'joined_at': membership.joined_at.isoformat()
        })
    
    # 取得任務列表
    tasks = []
    for task in project.tasks:
        task_data = {
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
            }
        }
        
        # 如果有指派對象
        if task.assigned_to:
            task_data['assigned_to'] = {
                'id': task.assignee.id,
                'username': task.assignee.username
            }
        else:
            task_data['assigned_to'] = None
            
        tasks.append(task_data)
    
    return jsonify({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'owner': {
            'id': project.owner.id,
            'username': project.owner.username
        },
        'my_role': role,
        'members': members,
        'tasks': tasks,
        'created_at': project.created_at.isoformat()
    }), 200

# ============ 更新專案 ============

@projects_bp.route('/<int:project_id>', methods=['PATCH'])
@jwt_required()
def update_project(project_id):
    """更新專案資訊"""
    current_user = get_current_user()
    
    # 檢查是否是 admin
    if not check_project_admin(project_id, current_user.id):
        return jsonify({'error': 'Only admins can update project'}), 403
    
    project = Project.query.get_or_404(project_id)
    data = request.json
    
    # 更新欄位
    if 'name' in data:
        if not data['name'] or not data['name'].strip():
            return jsonify({'error': 'Project name cannot be empty'}), 400
        project.name = data['name'].strip()
    
    if 'description' in data:
        project.description = data['description'].strip() or None
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Project updated successfully',
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============ 刪除專案 ============

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """刪除專案 (只有 owner 可以)"""
    current_user = get_current_user()
    project = Project.query.get_or_404(project_id)
    
    # 只有 owner 能刪除
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Only project owner can delete the project'}), 403
    
    try:
        # 因為有設定 cascade='all, delete-orphan'
        # 刪除專案時會自動刪除相關的 tasks 和 members
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            'message': 'Project deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============ 專案成員管理 ============

@projects_bp.route('/<int:project_id>/members', methods=['GET'])
@jwt_required()
def get_project_members(project_id):
    """查詢專案成員"""
    current_user = get_current_user()
    
    # 檢查權限
    has_access, project, _ = check_project_access(project_id, current_user.id)
    
    if not has_access:
        return jsonify({'error': 'Permission denied'}), 403
    
    members = []
    for membership in project.members:
        members.append({
            'id': membership.user.id,
            'username': membership.user.username,
            'email': membership.user.email,
            'role': membership.role,
            'joined_at': membership.joined_at.isoformat()
        })
    
    return jsonify({
        'members': members,
        'total': len(members)
    }), 200

@projects_bp.route('/<int:project_id>/members', methods=['POST'])
@jwt_required()
def add_project_member(project_id):
    """邀請成員加入專案"""
    current_user = get_current_user()
    
    # 檢查是否是 admin
    if not check_project_admin(project_id, current_user.id):
        return jsonify({'error': 'Only admins can invite members'}), 403
    
    data = request.json
    
    # 驗證必填欄位
    if not data.get('user_email'):
        return jsonify({'error': 'user_email is required'}), 400
    
    # 查詢要邀請的使用者
    invited_user = User.query.filter_by(email=data['user_email']).first()
    
    if not invited_user:
        return jsonify({'error': 'User not found'}), 404
    
    # 檢查是否已經是成員
    existing = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=invited_user.id
    ).first()
    
    if existing:
        return jsonify({'error': 'User is already a member of this project'}), 409
    
    # 加入成員
    member = ProjectMember(
        project_id=project_id,
        user_id=invited_user.id,
        role=data.get('role', 'member')  # 預設是 member
    )
    
    try:
        db.session.add(member)
        db.session.commit()
        
        return jsonify({
            'message': 'Member added successfully',
            'member': {
                'id': invited_user.id,
                'username': invited_user.username,
                'email': invited_user.email,
                'role': member.role
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@projects_bp.route('/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_project_member(project_id, user_id):
    """移除專案成員"""
    current_user = get_current_user()
    
    # 檢查是否是 admin
    if not check_project_admin(project_id, current_user.id):
        return jsonify({'error': 'Only admins can remove members'}), 403
    
    project = Project.query.get_or_404(project_id)
    
    # 不能移除 owner
    if project.owner_id == user_id:
        return jsonify({'error': 'Cannot remove project owner'}), 400
    
    # 查詢成員
    member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=user_id
    ).first()
    
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    try:
        db.session.delete(member)
        db.session.commit()
        
        return jsonify({
            'message': 'Member removed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@projects_bp.route('/<int:project_id>/members/<int:user_id>', methods=['PATCH'])
@jwt_required()
def update_member_role(project_id, user_id):
    """修改成員角色"""
    current_user = get_current_user()
    
    # 檢查是否是 admin
    if not check_project_admin(project_id, current_user.id):
        return jsonify({'error': 'Only admins can update member roles'}), 403
    
    project = Project.query.get_or_404(project_id)
    
    # 不能修改 owner 的角色
    if project.owner_id == user_id:
        return jsonify({'error': 'Cannot change owner role'}), 400
    
    member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=user_id
    ).first()
    
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    data = request.json
    
    if 'role' not in data:
        return jsonify({'error': 'role is required'}), 400
    
    if data['role'] not in ['admin', 'member']:
        return jsonify({'error': 'role must be "admin" or "member"'}), 400
    
    member.role = data['role']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Member role updated successfully',
            'member': {
                'id': member.user.id,
                'username': member.user.username,
                'role': member.role
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500