from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from models import db, User
from marshmallow import Schema, fields, validate, ValidationError
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)



# ============================================
# Input Validation Schemas (用 marshmallow)
# ============================================

class RegisterSchema(Schema):
    """註冊輸入驗證"""
    email = fields.Email(required=True, error_messages={
        'required': 'Email is required',
        'invalid': 'Invalid email format'
    })
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128, error='Password must be 8-128 characters'),
        error_messages={'required': 'Password is required'}
    )
    username = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=50, error='Username must be 2-50 characters'),
        error_messages={'required': 'Username is required'}
    )

class LoginSchema(Schema):
    """登入輸入驗證"""
    email = fields.Email(required=True)
    password = fields.Str(required=True)

# ============================================
# Helper Functions
# ============================================

def get_bcrypt():
    """從 Flask app extensions 取得 bcrypt 實例 (不用 global variable)"""
    try:
        bcrypt = current_app.extensions.get('bcrypt')
        if bcrypt is None:
            # 如果還是找不到,嘗試直接從 app 取得
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt(current_app)
            current_app.extensions['bcrypt'] = bcrypt
        return bcrypt
    except Exception as e:
        logger.error(f"Failed to get bcrypt: {str(e)}")
        return None

def validate_request_data(schema_class, data):
    """
    統一的輸入驗證函數
    
    Returns:
        tuple: (is_valid, data_or_errors)
    """
    schema = schema_class()
    try:
        validated_data = schema.load(data)
        return True, validated_data
    except ValidationError as err:
        return False, err.messages

# ============================================
# 註冊 API
# ============================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    使用者註冊
    
    改進點:
    1. 加上 input validation (marshmallow)
    2. 移除 global bcrypt,改用 current_app
    3. 改進錯誤處理,不洩漏敏感資訊
    4. 單一 transaction
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(RegisterSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 檢查 email 是否已存在
    if User.query.filter_by(email=result['email']).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    # 加密密碼 (使用 current_app 而非 global variable)
    bcrypt = get_bcrypt()
    if not bcrypt:
    # 這裡應該要檢查並回傳 500 錯誤，而不是直接讓它崩潰
        logger.error("Bcrypt extension not loaded correctly.")
        return jsonify({'error': 'Server configuration error (Bcrypt missing)'}), 500

    hashed_password = bcrypt.generate_password_hash(result['password']).decode('utf-8')

    
    # 建立使用者
    user = User(
        email=result['email'],
        username=result['username'],
        password_hash=hashed_password
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"New user registered: {user.email}")
        
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
        # 不要把 exception 細節洩漏給前端
        logger.error(f"Registration error for {result['email']}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Registration failed due to server error'}), 500

# ============================================
# 登入 API
# ============================================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    使用者登入
    
    改進點:
    1. 加上 input validation
    2. 返回 refresh token (支援 token 刷新機制)
    3. 更新 last_login 時間
    4. 改進錯誤訊息 (不區分 email/password 錯誤,避免帳號枚舉攻擊)
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(LoginSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 查詢使用者
    user = User.query.filter_by(email=result['email']).first()
    
    # 驗證密碼
    bcrypt = get_bcrypt()
    if not user or not bcrypt.check_password_hash(user.password_hash, result['password']):
        # 不要區分是 email 錯還是 password 錯,避免帳號枚舉攻擊
        logger.warning(f"Failed login attempt for email: {result['email']}")
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # 檢查帳號是否被停用
    if not user.is_active:
        logger.warning(f"Inactive user login attempt: {user.email}")
        return jsonify({'error': 'Account is disabled'}), 403
    
    # 建立 JWT tokens (包含 access token 和 refresh token)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    # 更新最後登入時間
    try:
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        # 這個錯誤不影響登入,只記錄就好
        logger.error(f"Failed to update last_login for {user.email}: {str(e)}")
    
    logger.info(f"User logged in: {user.email}")
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username
        }
    }), 200

# ============================================
# Token 刷新 API (新增)
# ============================================

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    刷新 access token
    
    這是新增的功能,讓前端可以用 refresh token 換新的 access token
    避免使用者頻繁重新登入
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'Invalid or inactive user'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token
    }), 200

# ============================================
# 登出 API (新增,需要 Redis)
# ============================================

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    登出 (將 token 加入黑名單)
    
    注意:這需要在 config 裡設定 Redis 作為 token blacklist
    """
    jti = get_jwt()['jti']  # JWT ID
    
    # 這裡需要把 jti 存到 Redis 的 blacklist
    # 示範代碼 (需要實際配置 Redis):
    # from datetime import timedelta
    # redis_client = current_app.extensions['redis']
    # redis_client.setex(f"blacklist:{jti}", timedelta(hours=24), "true")
    
    logger.info(f"User logged out: {get_jwt_identity()}")
    
    return jsonify({'message': 'Logout successful'}), 200

# ============================================
# 取得當前使用者資訊
# ============================================

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """
    取得當前登入使用者的資訊
    
    改進點:
    1. 返回更多有用的資訊
    2. 更好的錯誤處理
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        logger.warning(f"Token valid but user not found: {user_id}")
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'avatar_url': user.avatar_url,
        'bio': user.bio,
        'department': user.department,
        'position': user.position,
        'is_active': user.is_active,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'created_at': user.created_at.isoformat()
    }), 200

# ============================================
# 更新個人資料 (新增)
# ============================================

class UpdateProfileSchema(Schema):
    """個人資料更新驗證"""
    username = fields.Str(validate=validate.Length(min=2, max=50))
    bio = fields.Str(validate=validate.Length(max=500))
    phone = fields.Str(validate=validate.Length(max=20))
    department = fields.Str(validate=validate.Length(max=100))
    position = fields.Str(validate=validate.Length(max=100))

@auth_bp.route('/me', methods=['PATCH'])
@jwt_required()
def update_me():
    """更新當前使用者資料"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(UpdateProfileSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 更新欄位
    for field in ['username', 'bio', 'phone', 'department', 'position']:
        if field in result:
            setattr(user, field, result[field])
    
    try:
        db.session.commit()
        logger.info(f"User profile updated: {user.email}")
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'bio': user.bio,
                'phone': user.phone,
                'department': user.department,
                'position': user.position
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update error for {user.email}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Update failed due to server error'}), 500

# ============================================
# 修改密碼 (新增)
# ============================================

class ChangePasswordSchema(Schema):
    """密碼修改驗證"""
    current_password = fields.Str(required=True)
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128)
    )

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密碼"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # 驗證輸入
    is_valid, result = validate_request_data(ChangePasswordSchema, data)
    if not is_valid:
        return jsonify({'error': 'Validation failed', 'details': result}), 400
    
    # 驗證舊密碼
    bcrypt = get_bcrypt()
    if not bcrypt.check_password_hash(user.password_hash, result['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # 更新密碼
    user.password_hash = bcrypt.generate_password_hash(result['new_password']).decode('utf-8')
    
    try:
        db.session.commit()
        logger.info(f"Password changed for user: {user.email}")
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Password change error for {user.email}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Password change failed due to server error'}), 500

# ============================================
# 輔助函數 (供其他模組使用)
# ============================================

def get_current_user():
    """
    取得當前登入的使用者
    
    改進點:加上錯誤處理
    """
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return None
        return User.query.get(user_id)
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None