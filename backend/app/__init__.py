"""
Flask application factory for XU-News-AI-RAG system.
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
mail = Mail()
migrate = Migrate()


def create_app(config_name=None):
    """
    Flask application factory.
    
    Args:
        config_name (str): Configuration name ('development', 'testing', 'production')
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    
    from config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, origins=app.config['CORS_ORIGINS'])
    mail.init_app(app)
    migrate.init_app(app, db)
    
    # Configure logging
    configure_logging(app)
    
    # JWT error handlers
    configure_jwt_handlers(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Error handlers
    register_error_handlers(app)
    
    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Document, Source, Tag, SearchHistory
        return {
            'db': db,
            'User': User,
            'Document': Document,
            'Source': Source,
            'Tag': Tag,
            'SearchHistory': SearchHistory
        }
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'xu-news-ai-rag'}, 200
    
    return app


def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        if not app.logger.handlers:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler('logs/xu-news-ai-rag.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('XU-News-AI-RAG startup')


def configure_jwt_handlers(app):
    """Configure JWT error handlers."""
    
    # Import the blacklist checker from auth module
    from app.api.auth import check_if_token_revoked, blacklisted_tokens
    
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        return check_if_token_revoked(jwt_header, jwt_payload)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.warning(f"Expired token access attempt: {jwt_payload.get('sub', 'unknown')}")
        return {'error': 'Token has expired'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        app.logger.warning(f"Invalid token error: {error}")
        return {'error': 'Invalid token'}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        app.logger.info(f"Missing token access attempt: {error}")
        return {'error': 'Authorization token is required'}, 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        app.logger.warning(f"Revoked token access attempt: {jwt_payload.get('sub', 'unknown')}")
        return {'error': 'Token has been revoked'}, 401
    
    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        return {'error': 'Fresh token required'}, 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has been revoked'}, 401


def register_blueprints(app):
    """Register application blueprints."""
    from app.api.auth import bp as auth_bp
    from app.api.content import bp as content_bp
    from app.api.search import bp as search_bp
    from app.api.analytics import bp as analytics_bp
    from app.api.sources import bp as sources_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(content_bp, url_prefix='/api/content')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(sources_bp, url_prefix='/api/sources')


def register_error_handlers(app):
    """Register application error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request'}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {'error': 'Unauthorized'}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {'error': 'Forbidden'}, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        return {'error': 'Unprocessable entity'}, 422
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'Unhandled Exception: {error}')
        db.session.rollback()
        return {'error': 'An unexpected error occurred'}, 500
