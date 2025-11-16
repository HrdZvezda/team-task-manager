from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from config import Config
from models import db

app = Flask(__name__)
app.config.from_object(Config)

# CORS(app)
CORS(app, supports_credentials=True, origins=['*'])
db.init_app(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# create data table
with app.app_context():
    db.create_all()

# 註冊 Blueprint
from auth import auth_bp, init_bcrypt
init_bcrypt(bcrypt) # ← 傳入 bcrypt 實例
app.register_blueprint(auth_bp, url_prefix='/auth')

from projects import projects_bp
app.register_blueprint(projects_bp, url_prefix='/projects')

from tasks import tasks_bp
app.register_blueprint(tasks_bp)

# 404 Error Handler
@app.errorhandler(404)
def not_found_todo(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist',
        'status': 404
    }), 404

# 500 Error Handler
@app.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong',
        'status': 500
    }), 500

jwt = JWTManager(app)

# 處理 token 過期
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'error': 'Token has expired',
        'message': 'Please login again'
    }), 401

# 處理無效的 token
@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'error': 'Invalid token',
        'message': 'Please provide a valid token'
    }), 401

# 處理缺少 token
@jwt.unauthorized_loader
def unauthorized_callback(error):
    return jsonify({
        'error': 'Missing token',
        'message': 'Please provide an authorization token'
    }), 401

# 首頁
@app.route('/')
def home():
    return jsonify({
        'message': 'Team Task Manager API',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/auth/register, /auth/login, /auth/me',
            'project': '/projects(GET, POST), /projects/:id(GET, PATCH, DELETE)',
            'members': '/projects/:id/members(GET, POST, PATCH , DELETE)'
        }
    })


if __name__ == '__main__':
    app.run(debug=True,port=8888)

