"""
Configuration settings for the XU-News-AI-RAG application.
"""
import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = BASE_DIR.parent


class Config:
    """Base configuration class."""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'xu-news-ai-rag-dev-secret-key-2024'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-xu-news-ai-rag-2024'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # Increased to 24 hours for better UX
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Caching Configuration (currently in-memory)
    # Note: Using in-memory caching (Python dicts) for simplicity
    # For production scale, consider implementing Redis or Memcached
    
    # Background Task Configuration
    BACKGROUND_TASK_MAX_WORKERS = int(os.environ.get('BACKGROUND_TASK_MAX_WORKERS', 4))
    BACKGROUND_TASK_TIMEOUT = int(os.environ.get('BACKGROUND_TASK_TIMEOUT', 300))
    
    # Scheduler Configuration  
    SCHEDULER_TIMEZONE = os.environ.get('SCHEDULER_TIMEZONE', 'UTC')
    SCHEDULER_MAX_WORKERS = int(os.environ.get('SCHEDULER_MAX_WORKERS', 2))
    
    # AI Model Configuration
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL') or 'http://localhost:11434'
    EMBEDDINGS_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
    EMBEDDINGS_MODEL_CACHE_FOLDER = os.environ.get('EMBEDDINGS_MODEL_CACHE_FOLDER') or str(PROJECT_ROOT / 'data' / 'models')
    RERANKER_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
    LLM_MODEL = 'qwen3:4b'
    
    # File Storage Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or str(PROJECT_ROOT / 'data' / 'uploads')
    VECTOR_STORE_PATH = os.environ.get('VECTOR_STORE_PATH') or str(PROJECT_ROOT / 'data' / 'vector_stores')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@xu-news-ai-rag.com'
    
    # External API Configuration
    GOOGLE_SEARCH_API_KEY = os.environ.get('GOOGLE_SEARCH_API_KEY')
    GOOGLE_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
    
    # Security Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    BCRYPT_LOG_ROUNDS = 12
    
    # Crawler Configuration
    CRAWLER_USER_AGENT = 'XU-News-AI-RAG-Bot/1.0 (+https://github.com/xu-news-ai-rag)'
    CRAWLER_DELAY = 1  # seconds between requests
    CRAWLER_RESPECT_ROBOTS_TXT = True
    CRAWLER_MAX_CONCURRENT_REQUESTS = 5
    
    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Search Configuration
    DEFAULT_SEARCH_RESULTS = 10
    MAX_SEARCH_RESULTS = 100
    SEARCH_TIMEOUT = 30  # seconds
    
    @staticmethod
    def init_app(app):
        """Initialize application with config."""
        # Ensure required directories exist
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.VECTOR_STORE_PATH, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or f'sqlite:///{BASE_DIR}/dev.db'
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Disable email in development
    MAIL_SUPPRESS_SEND = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=1)
    MAIL_SUPPRESS_SEND = True
    
    # Use smaller models for testing
    EMBEDDINGS_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
    
    # Background tasks run synchronously for testing
    BACKGROUND_TASK_MAX_WORKERS = 1
    BACKGROUND_TASK_TIMEOUT = 30


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/xu_news_ai_rag'
    
    # Enhanced security in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production logging
    LOG_LEVEL = 'INFO'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to stderr in production
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
