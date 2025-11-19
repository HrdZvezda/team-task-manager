from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from models import db
from sqlalchemy import text
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os

# ============================================
# 初始化 Flask App
# ============================================

app = Flask(__name__)
app.config.from_object(Config)

# ============================================
# CORS 設定 (改進版)
# ============================================

# 不要用 '*',應該指定允許的來源
# 在 production 環境應該從環境變數讀取
# 改正環境變數名稱
allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:5500').split(',')

CORS(app, 
     supports_credentials=True, 
     origins=allowed_origins,
     methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])

# ============================================
# 擴展初始化
# ============================================

db.init_app(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

app.extensions['bcrypt'] = bcrypt

# Rate Limiting (改進版)
# 使用 Redis 作為後端 (在 production 環境)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri=os.getenv('REDIS_URL', 'memory://'),  # 開發環境用記憶體,production 用 Redis
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window"
)

# ============================================
# Logging 設定 (改進版)
# ============================================

def setup_logging(app):
    """
    設定完整的 logging 系統
    
    改進點:
    1. 分開 info 和 error logs
    2. 使用 RotatingFileHandler 避免 log 檔案過大
    3. 設定統一的 log format
    """
    if not app.debug:
        # 確保 logs 目錄存在
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Log format
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
        
        # Info log handler (記錄一般資訊)
        info_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)
        
        # Error log handler (只記錄錯誤)
        error_handler = RotatingFileHandler(
            'logs/error.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # 加到 app logger
        app.logger.addHandler(info_handler)
        app.logger.addHandler(error_handler)
        app.logger.setLevel(logging.INFO)
        
        app.logger.info('Application startup')

# 在 production 環境啟用 logging
if not app.debug:
    setup_logging(app)

# ============================================
# 資料庫初始化
# ============================================

with app.app_context():
    db.create_all()
    app.logger.info('Database tables created')

# ============================================
# 註冊 Blueprints
# ============================================

from auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

from projects import projects_bp
app.register_blueprint(projects_bp, url_prefix='/projects')

from tasks import tasks_bp
app.register_blueprint(tasks_bp)

from notifications import notifications_bp
app.register_blueprint(notifications_bp, url_prefix='/api')

# ============================================
# JWT 錯誤處理 (改進版)
# ============================================

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """處理 token 過期"""
    app.logger.warning(f"Expired token attempt from: {request.remote_addr}")
    return jsonify({
        'error': 'token_expired',
        'message': 'The token has expired. Please refresh your token or login again.'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    """處理無效的 token"""
    app.logger.warning(f"Invalid token attempt from: {request.remote_addr}, error: {error}")
    return jsonify({
        'error': 'invalid_token',
        'message': 'Token validation failed. Please provide a valid token.'
    }), 401

@jwt.unauthorized_loader
def unauthorized_callback(error):
    """處理缺少 token"""
    app.logger.warning(f"Unauthorized access attempt from: {request.remote_addr}, error: {error}")
    return jsonify({
        'error': 'authorization_required',
        'message': 'Access token is required. Please provide an authorization token.'
    }), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    """處理被撤銷的 token (需要實作 token blacklist)"""
    return jsonify({
        'error': 'token_revoked',
        'message': 'The token has been revoked. Please login again.'
    }), 401

# ============================================
# 全域錯誤處理 (改進版)
# ============================================

@app.errorhandler(400)
def bad_request(error):
    """處理 400 錯誤"""
    return jsonify({
        'error': 'bad_request',
        'message': 'The request is malformed or invalid',
        'status': 400
    }), 400

@app.errorhandler(404)
def not_found(error):
    """處理 404 錯誤"""
    return jsonify({
        'error': 'not_found',
        'message': 'The requested resource does not exist',
        'status': 404
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """處理 405 錯誤"""
    return jsonify({
        'error': 'method_not_allowed',
        'message': 'The HTTP method is not allowed for this endpoint',
        'status': 405
    }), 405

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """處理 rate limit 超過"""
    app.logger.warning(f"Rate limit exceeded from: {request.remote_addr}")
    return jsonify({
        'error': 'rate_limit_exceeded',
        'message': 'Too many requests. Please try again later.',
        'status': 429
    }), 429

@app.errorhandler(500)
def internal_server_error(error):
    """
    處理 500 錯誤
    
    改進點:
    1. 不洩漏錯誤細節給前端
    2. 記錄完整的 stack trace 到 log
    3. rollback transaction
    """
    db.session.rollback()
    
    # 記錄完整錯誤到 log (不給前端看)
    app.logger.error(f"Internal server error: {str(error)}", exc_info=True)
    
    # 只給前端看通用訊息
    return jsonify({
        'error': 'internal_server_error',
        'message': 'An internal error occurred. Our team has been notified.',
        'status': 500
    }), 500

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """
    處理所有未預期的錯誤
    
    這是最後的防線,捕捉所有沒被處理的 exception
    """
    db.session.rollback()
    
    app.logger.error(f"Unexpected error: {str(error)}", exc_info=True)
    
    return jsonify({
        'error': 'unexpected_error',
        'message': 'An unexpected error occurred. Please try again later.',
        'status': 500
    }), 500

# ============================================
# Request/Response Logging (改進版)
# ============================================

@app.before_request
def log_request():
    """記錄每個請求"""
    if not app.debug:
        app.logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response(response):
    """記錄每個回應"""
    if not app.debug:
        app.logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
    
    # 加上 security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

# ============================================
# Health Check Endpoint (新增)
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """
    健康檢查端點
    
    用於 load balancer 或監控系統檢查服務是否正常
    """
    try:
        # 檢查資料庫連線
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': 'Database connection failed'
        }), 503

# ============================================
# API 首頁
# ============================================

@app.route('/')
@limiter.limit("10 per minute")  # 首頁限制寬鬆一點
def home():
    """
    API 首頁
    
    改進點:加上更完整的 API 文件
    """
    return jsonify({
        'message': 'Team Task Manager API',
        'version': '2.0.0',
        'documentation': '/api/docs',  # 可以用 Flask-RESTX 或 Flask-Smorest 產生
        'endpoints': {
            'health': {
                'path': '/health',
                'methods': ['GET'],
                'description': 'Health check endpoint'
            },
            'auth': {
                'register': {'path': '/auth/register', 'methods': ['POST']},
                'login': {'path': '/auth/login', 'methods': ['POST']},
                'refresh': {'path': '/auth/refresh', 'methods': ['POST']},
                'logout': {'path': '/auth/logout', 'methods': ['POST']},
                'me': {'path': '/auth/me', 'methods': ['GET', 'PATCH']},
                'change_password': {'path': '/auth/change-password', 'methods': ['POST']}
            },
            'projects': {
                'list': {'path': '/projects', 'methods': ['GET', 'POST']},
                'detail': {'path': '/projects/:id', 'methods': ['GET', 'PATCH', 'DELETE']},
                'members': {'path': '/projects/:id/members', 'methods': ['GET', 'POST']},
                'stats': {'path': '/projects/:id/stats', 'methods': ['GET']}
            },
            'tasks': {
                'list': {'path': '/projects/:id/tasks', 'methods': ['GET', 'POST']},
                'my_tasks': {'path': '/tasks/my', 'methods': ['GET']},
                'detail': {'path': '/tasks/:id', 'methods': ['GET', 'PATCH', 'DELETE']},
                'comments': {'path': '/tasks/:id/comments', 'methods': ['GET', 'POST']}
            },
            'notifications': {
                'list': {'path': '/api/notifications', 'methods': ['GET']},
                'mark_read': {'path': '/api/notifications/:id/read', 'methods': ['PATCH']},
                'settings': {'path': '/api/notifications/settings', 'methods': ['GET', 'PATCH']}
            }
        },
        'rate_limits': {
            'default': '200 per hour, 1000 per day',
            'auth': {
                'register': '5 per hour',
                'login': '10 per minute'
            }
        }
    })

# ============================================
# 開發環境專用的 Debug Route
# ============================================

if app.debug:
    @app.route('/debug/routes')
    def debug_routes():
        """列出所有註冊的路由 (僅開發環境)"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        return jsonify({'routes': routes})

# ============================================
# 啟動應用
# ============================================

if __name__ == '__main__':
    # 在 production 環境不要用 Flask 內建的 server
    # 應該用 gunicorn 或 uwsgi
    
    # 從環境變數讀取設定
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('FLASK_PORT', 8888))
    
    app.run(
        debug=debug_mode,
        port=port,
        host='0.0.0.0'  # 允許外部訪問
    )