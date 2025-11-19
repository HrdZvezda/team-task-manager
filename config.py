import os
from datetime import timedelta
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

class Config:
    """
    應用程式設定
    
    改進點:
    1. 從環境變數讀取敏感資訊
    2. 加上更多安全設定
    3. 區分開發和生產環境
    """
    
    # ============================================
    # 基本設定
    # ============================================
    
    # Secret Key (用於 session 和 JWT)
    # ⚠️ 在 production 環境必須設定強隨機值
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 環境
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # ============================================
    # 資料庫設定
    # ============================================
    
    # 從環境變數讀取資料庫 URL
    # 格式: postgresql://user:password@localhost/dbname
    # 或: sqlite:///path/to/database.db
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///task_manager.db'  # 開發環境預設用 SQLite
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection Pool 設定 (對 production 很重要)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,  # 檢查連線是否有效
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20))
    }
    
    # ============================================
    # JWT 設定
    # ============================================
    
    # JWT Secret Key (可以跟 SECRET_KEY 不同以提高安全性)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    
    # Token 過期時間
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 30))
    )
    
    # JWT 位置設定
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # JWT Error Messages (自訂錯誤訊息)
    JWT_ERROR_MESSAGE_KEY = 'message'
    
    # Token Blacklist (需要 Redis)
    # JWT_BLACKLIST_ENABLED = True
    # JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # ============================================
    # CORS 設定
    # ============================================
    
    # 允許的來源 (不要在 production 用 '*')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # ============================================
    # Rate Limiting 設定
    # ============================================
    
    # Redis URL (用於 rate limiting 和 session storage)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # 預設 rate limits
    RATELIMIT_STORAGE_URL = REDIS_URL if ENV == 'production' else 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True
    
    # ============================================
    # Session 設定
    # ============================================
    
    SESSION_COOKIE_SECURE = ENV == 'production'  # production 環境只允許 HTTPS
    SESSION_COOKIE_HTTPONLY = True  # 防止 XSS 攻擊
    SESSION_COOKIE_SAMESITE = 'Lax'  # 防止 CSRF 攻擊
    
    # ============================================
    # 檔案上傳設定 (如果需要的話)
    # ============================================
    
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # ============================================
    # Email 設定 (用於發送通知郵件)
    # ============================================
    
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@taskmanager.com')
    
    # ============================================
    # Logging 設定
    # ============================================
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    # ============================================
    # 安全設定
    # ============================================
    
    # 密碼強度要求
    PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_REQUIRE_UPPERCASE = os.getenv('PASSWORD_REQUIRE_UPPERCASE', 'False').lower() == 'true'
    PASSWORD_REQUIRE_NUMBERS = os.getenv('PASSWORD_REQUIRE_NUMBERS', 'False').lower() == 'true'
    PASSWORD_REQUIRE_SPECIAL = os.getenv('PASSWORD_REQUIRE_SPECIAL', 'False').lower() == 'true'
    
    # ============================================
    # Celery 設定 (如果使用非同步任務)
    # ============================================
    
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    
    # ============================================
    # 其他設定
    # ============================================
    
    # API 版本
    API_VERSION = '2.0.0'
    
    # Timezone
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')
    
    # Pagination 預設值
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', 20))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', 100))
    
    @staticmethod
    def validate():
        """
        驗證設定是否正確
        
        在啟動時檢查必要的設定是否都有設定
        """
        required_in_production = [
            'SECRET_KEY',
            'JWT_SECRET_KEY',
            'DATABASE_URL'
        ]
        
        if Config.ENV == 'production':
            missing = []
            for key in required_in_production:
                if not os.getenv(key):
                    missing.append(key)
            
            if missing:
                raise ValueError(
                    f"Missing required environment variables in production: {', '.join(missing)}"
                )
            
            # 檢查是否使用預設的 secret key
            if Config.SECRET_KEY == 'dev-secret-key-change-in-production':
                raise ValueError("You must set a strong SECRET_KEY in production!")


class DevelopmentConfig(Config):
    """開發環境設定"""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # 印出 SQL 查詢


class ProductionConfig(Config):
    """生產環境設定"""
    DEBUG = False
    TESTING = False
    
    # 在 production 環境強制使用 HTTPS
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """測試環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 使用記憶體資料庫
    WTF_CSRF_ENABLED = False


# 根據環境變數選擇設定
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """取得當前環境的設定"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])