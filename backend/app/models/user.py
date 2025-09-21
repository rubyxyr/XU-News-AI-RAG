"""
User model for authentication and user management.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model):
    """User model for authentication and profile management."""
    
    __tablename__ = 'users'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile fields
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    bio = db.Column(db.Text)
    
    # Status fields
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Settings
    notification_preferences = db.Column(db.JSON, default=lambda: {
        'email_notifications': True,
        'digest_frequency': 'daily',
        'new_content_alerts': True
    })
    
    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    sources = db.relationship('Source', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    search_history = db.relationship('SearchHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches user's password."""
        return check_password_hash(self.password_hash, password)
    
    def generate_tokens(self, remember_me=False):
        """Generate JWT access and refresh tokens with optional extended expiration."""
        from datetime import timedelta
        
        additional_claims = {
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active
        }
        
        # Set custom expiration times for remember me
        if remember_me:
            # Remember me: 30 days for access token, 90 days for refresh token
            access_expires = timedelta(days=30)
            refresh_expires = timedelta(days=90)
        else:
            # Normal: 24 hours for access token, 30 days for refresh token (better UX)
            access_expires = timedelta(hours=24)
            refresh_expires = timedelta(days=30)
        
        access_token = create_access_token(
            identity=str(self.id),
            additional_claims=additional_claims,
            expires_delta=access_expires
        )
        
        refresh_token = create_refresh_token(
            identity=str(self.id),
            expires_delta=refresh_expires
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    
    def update_last_login(self):
        """Update user's last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def get_full_name(self):
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def to_dict(self, include_sensitive=False):
        """Convert user object to dictionary."""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_sensitive else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'bio': self.bio,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'full_name': self.get_full_name()
        }
        
        if include_sensitive:
            data['notification_preferences'] = self.notification_preferences
        
        return data
    
    @staticmethod
    def create_user(username, email, password, **kwargs):
        """Create a new user."""
        user = User(
            username=username,
            email=email,
            **kwargs
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    def update_profile(self, **kwargs):
        """Update user profile."""
        allowed_fields = ['first_name', 'last_name', 'bio', 'notification_preferences']
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_stats(self):
        """Get user statistics."""
        return {
            'total_documents': self.documents.count(),
            'total_sources': self.sources.filter_by(is_active=True).count(),
            'total_searches': self.search_history.count(),
            'recent_activity': self.get_recent_activity()
        }
    
    def get_recent_activity(self, limit=5):
        """Get recent user activity."""
        # Import locally to avoid circular imports
        from app.models.document import Document
        from app.models.search_history import SearchHistory
        
        activities = []
        
        # Recent documents
        recent_docs = self.documents.order_by(Document.created_at.desc()).limit(limit).all()
        for doc in recent_docs:
            activities.append({
                'type': 'document_created',
                'timestamp': doc.created_at,
                'description': f'Added document: {doc.title}',
                'data': {'document_id': doc.id}
            })
        
        # Recent searches
        recent_searches = self.search_history.order_by(SearchHistory.created_at.desc()).limit(limit).all()
        for search in recent_searches:
            activities.append({
                'type': 'search_performed',
                'timestamp': search.created_at,
                'description': f'Searched: {search.query}',
                'data': {'query': search.query, 'results_count': search.results_count}
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:limit]
