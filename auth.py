from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User
from flask_bcrypt import Bcrypt

auth_bp = Blueprint('auth', __name__)

# 需要在 app.py 傳入 bcrypt
bcrypt = None

def init_bcrypt(app_bcrypt):
    """從 app.py 傳入 bcrypt 實例"""
    global bcrypt
    bcrypt = app_bcrypt

# ============ 註冊 ============
@auth_bp.route('/register', methods=['POST'])
def register():
    """使用者註冊"""
    data = request.json
    
    # 驗證必填欄位
    if not data.get('email') or not data.get('password') or not data.get('username'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # 檢查 email 是否已存在
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    # 加密密碼
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    # 建立使用者
    user = User(
        email=data['email'],
        username=data['username'],
        password_hash=hashed_password
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# ============ 登入 ============
@auth_bp.route('/login', methods=['POST'])
def login():
    """使用者登入"""
    data = request.json
    
    # 驗證必填欄位
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    # 查詢使用者
    user = User.query.filter_by(email=data['email']).first()
    
    # 驗證密碼
    if not user or not bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # 建立 JWT token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Login successful',
        'token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username
        }
    }), 200

# ============ 取得當前使用者資訊 ============
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """取得當前登入使用者的資訊"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'created_at': user.created_at.isoformat()
    }), 200

# ============ 輔助函數 ============
def get_current_user():
    """取得當前登入的使用者 (在其他地方使用)"""
    user_id = get_jwt_identity()
    return User.query.get(user_id)