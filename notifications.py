# ============================================
# 新檔案：notifications.py
# 這是一個全新的檔案，用於處理通知系統
# ============================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Notification, User
from datetime import datetime, timedelta

notifications_bp = Blueprint('notifications', __name__)

# ============================================
# 1. 取得使用者的通知
# ============================================

@notifications_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """取得當前使用者的通知"""
    user_id = get_jwt_identity()
    
    # 查詢參數
    unread_only = request.args.get('unread_only', False, type=bool)
    notification_type = request.args.get('type')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 建立查詢
    query = Notification.query.filter_by(user_id=user_id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    if notification_type:
        query = query.filter_by(type=notification_type)
    
    # 按時間排序（最新的在前）
    query = query.order_by(Notification.created_at.desc())
    
    # 分頁
    notifications = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'content': n.content,
            'is_read': n.is_read,
            'project': {
                'id': n.project.id,
                'name': n.project.name
            } if n.related_project_id else None,
            'task': {
                'id': n.task.id,
                'title': n.task.title
            } if n.related_task_id else None,
            'created_at': n.created_at.isoformat()
        } for n in notifications.items],
        'total': notifications.total,
        'unread_count': Notification.query.filter_by(user_id=user_id, is_read=False).count(),
        'page': page,
        'per_page': per_page,
        'total_pages': notifications.pages
    }), 200

# ============================================
# 2. 標記通知為已讀
# ============================================

@notifications_bp.route('/notifications/<int:notification_id>/read', methods=['PATCH'])
@jwt_required()
def mark_notification_read(notification_id):
    """標記單個通知為已讀"""
    user_id = get_jwt_identity()
    
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    notification.is_read = True
    
    try:
        db.session.commit()
        return jsonify({'message': 'Notification marked as read'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@notifications_bp.route('/notifications/read-all', methods=['PATCH'])
@jwt_required()
def mark_all_notifications_read():
    """標記所有通知為已讀"""
    user_id = get_jwt_identity()
    
    try:
        Notification.query.filter_by(user_id=user_id, is_read=False)\
            .update({'is_read': True})
        db.session.commit()
        
        return jsonify({'message': 'All notifications marked as read'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============================================
# 3. 刪除通知
# ============================================

@notifications_bp.route('/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    """刪除單個通知"""
    user_id = get_jwt_identity()
    
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    try:
        db.session.delete(notification)
        db.session.commit()
        return jsonify({'message': 'Notification deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@notifications_bp.route('/notifications/clear', methods=['DELETE'])
@jwt_required()
def clear_notifications():
    """清除所有已讀通知"""
    user_id = get_jwt_identity()
    
    # 只刪除已讀的通知
    notifications = Notification.query.filter_by(user_id=user_id, is_read=True).all()
    
    try:
        for notification in notifications:
            db.session.delete(notification)
        db.session.commit()
        
        return jsonify({
            'message': f'Cleared {len(notifications)} read notifications'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============================================
# 4. 通知設定
# ============================================

@notifications_bp.route('/notifications/settings', methods=['GET'])
@jwt_required()
def get_notification_settings():
    """取得通知設定"""
    user_id = get_jwt_identity()
    
    from models import UserPreference
    preference = UserPreference.query.filter_by(user_id=user_id).first()
    
    if not preference:
        # 回傳預設值
        return jsonify({
            'email_notifications': True,
            'push_notifications': False,
            'notification_types': {
                'task_assigned': True,
                'task_completed': True,
                'comment_added': True,
                'member_joined': True,
                'task_reminder': True
            }
        }), 200
    
    return jsonify({
        'email_notifications': preference.email_notifications,
        'push_notifications': preference.push_notifications,
        'notification_types': preference.notification_types or {
            'task_assigned': True,
            'task_completed': True,
            'comment_added': True,
            'member_joined': True,
            'task_reminder': True
        }
    }), 200

@notifications_bp.route('/notifications/settings', methods=['PATCH'])
@jwt_required()
def update_notification_settings():
    """更新通知設定"""
    user_id = get_jwt_identity()
    data = request.json
    
    from models import UserPreference
    preference = UserPreference.query.filter_by(user_id=user_id).first()
    
    if not preference:
        preference = UserPreference(user_id=user_id)
        db.session.add(preference)
    
    # 更新設定
    if 'email_notifications' in data:
        preference.email_notifications = data['email_notifications']
    
    if 'push_notifications' in data:
        preference.push_notifications = data['push_notifications']
    
    if 'notification_types' in data:
        preference.notification_types = data['notification_types']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Notification settings updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============================================
# 5. 批量建立通知（內部使用）
# ============================================

def create_notification_for_members(project_id, notification_type, title, content, 
                                   exclude_user_id=None, task_id=None):
    """為專案成員批量建立通知（內部函數）"""
    from models import ProjectMember
    
    # 取得所有專案成員
    members = ProjectMember.query.filter_by(project_id=project_id).all()
    
    notifications = []
    for member in members:
        # 排除特定使用者（例如操作者本身）
        if exclude_user_id and member.user_id == exclude_user_id:
            continue
        
        notification = Notification(
            user_id=member.user_id,
            type=notification_type,
            title=title,
            content=content,
            related_project_id=project_id,
            related_task_id=task_id
        )
        notifications.append(notification)
        db.session.add(notification)
    
    return notifications

# ============================================
# 6. 通知統計
# ============================================

@notifications_bp.route('/notifications/stats', methods=['GET'])
@jwt_required()
def get_notification_stats():
    """取得通知統計資料"""
    user_id = get_jwt_identity()
    
    # 總通知數
    total = Notification.query.filter_by(user_id=user_id).count()
    
    # 未讀數
    unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    # 按類型統計
    from sqlalchemy import func
    type_stats = db.session.query(
        Notification.type,
        func.count(Notification.id)
    ).filter_by(user_id=user_id).group_by(Notification.type).all()
    
    # 今日通知
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.created_at >= today_start
    ).count()
    
    # 本週通知
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_count = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.created_at >= week_start
    ).count()
    
    return jsonify({
        'total': total,
        'unread': unread,
        'today': today_count,
        'this_week': week_count,
        'by_type': {t: count for t, count in type_stats}
    }), 200
