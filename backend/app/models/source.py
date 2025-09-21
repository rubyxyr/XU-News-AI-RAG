"""
Source model for RSS feeds and web crawling sources.
"""
from datetime import datetime, timedelta
from app import db


class Source(db.Model):
    """Source model for RSS feeds and web crawling configuration."""
    
    __tablename__ = 'sources'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Source information
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    source_type = db.Column(db.String(50), nullable=False, index=True)  # 'rss', 'web', 'api'
    description = db.Column(db.Text)
    
    # Status and configuration
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    update_frequency = db.Column(db.Integer, default=30)  # minutes
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_crawled = db.Column(db.DateTime)
    next_crawl = db.Column(db.DateTime)
    
    # Crawling statistics
    total_articles = db.Column(db.Integer, default=0)
    successful_crawls = db.Column(db.Integer, default=0)
    failed_crawls = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text)
    
    # Configuration options
    crawl_settings = db.Column(db.JSON, default=lambda: {
        'auto_tag': True,
        'auto_summarize': True,
        'extract_content': True,
        'follow_redirects': True,
        'respect_robots_txt': True,
        'max_articles_per_crawl': 5,
        'custom_headers': {},
        'xpath_selectors': {}
    })
    
    # Auto-tagging configuration
    auto_tags = db.Column(db.JSON, default=list)  # List of tags to automatically apply
    
    def __repr__(self):
        return f'<Source {self.name}>'
    
    def calculate_next_crawl(self):
        """Calculate next crawl time based on update frequency."""
        if self.last_crawled:
            self.next_crawl = self.last_crawled + timedelta(minutes=self.update_frequency)
        else:
            self.next_crawl = datetime.utcnow()
    
    def update_crawl_stats(self, success=True, articles_count=0, error=None):
        """Update crawling statistics."""
        self.last_crawled = datetime.utcnow()
        
        if success:
            self.successful_crawls += 1
            self.total_articles += articles_count
            self.last_error = None
        else:
            self.failed_crawls += 1
            self.last_error = str(error) if error else "Unknown error"
        
        self.calculate_next_crawl()
        db.session.commit()
    
    def is_due_for_crawl(self):
        """Check if source is due for crawling."""
        if not self.is_active:
            return False
        
        if not self.next_crawl:
            return True
        
        return datetime.utcnow() >= self.next_crawl
    
    def get_success_rate(self):
        """Calculate crawling success rate."""
        total = self.successful_crawls + self.failed_crawls
        if total == 0:
            return 0.0
        return (self.successful_crawls / total) * 100
    
    def to_dict(self, include_stats=True):
        """Convert source to dictionary."""
        data = {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'source_type': self.source_type,
            'description': self.description,
            'is_active': self.is_active,
            'update_frequency': self.update_frequency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_crawled': self.last_crawled.isoformat() if self.last_crawled else None,
            'next_crawl': self.next_crawl.isoformat() if self.next_crawl else None,
            'auto_tags': self.auto_tags,
            'crawl_settings': self.crawl_settings
        }
        
        if include_stats:
            data.update({
                'total_articles': self.total_articles,
                'successful_crawls': self.successful_crawls,
                'failed_crawls': self.failed_crawls,
                'success_rate': self.get_success_rate(),
                'last_error': self.last_error,
                'is_due_for_crawl': self.is_due_for_crawl()
            })
        
        return data
    
    @staticmethod
    def create_source(user_id, name, url, source_type, **kwargs):
        """Create a new source."""
        source = Source(
            user_id=user_id,
            name=name,
            url=url,
            source_type=source_type,
            **kwargs
        )
        
        # Calculate initial next crawl time
        source.calculate_next_crawl()
        
        db.session.add(source)
        db.session.commit()
        
        return source
    
    def update_source(self, **kwargs):
        """Update source configuration."""
        allowed_fields = [
            'name', 'url', 'description', 'is_active', 'update_frequency',
            'crawl_settings', 'auto_tags'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(self, key, value)
        
        # Recalculate next crawl if frequency changed
        if 'update_frequency' in kwargs:
            self.calculate_next_crawl()
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_user_sources(cls, user_id, source_type=None, active_only=False):
        """Get sources for a user with optional filters."""
        query = cls.query.filter_by(user_id=user_id)
        
        if source_type:
            query = query.filter_by(source_type=source_type)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_due_sources(cls, user_id=None):
        """Get sources that are due for crawling."""
        query = cls.query.filter_by(is_active=True)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        now = datetime.utcnow()
        due_sources = []
        
        for source in query.all():
            if source.is_due_for_crawl():
                due_sources.append(source)
        
        return due_sources
    
    @classmethod
    def get_source_stats(cls, user_id):
        """Get aggregated source statistics for a user."""
        sources = cls.query.filter_by(user_id=user_id).all()
        
        total_sources = len(sources)
        active_sources = len([s for s in sources if s.is_active])
        total_articles = sum(s.total_articles for s in sources)
        total_crawls = sum(s.successful_crawls + s.failed_crawls for s in sources)
        successful_crawls = sum(s.successful_crawls for s in sources)
        
        success_rate = (successful_crawls / total_crawls * 100) if total_crawls > 0 else 0
        
        # Group by source type
        by_type = {}
        for source in sources:
            if source.source_type not in by_type:
                by_type[source.source_type] = {
                    'count': 0,
                    'articles': 0,
                    'active': 0
                }
            
            by_type[source.source_type]['count'] += 1
            by_type[source.source_type]['articles'] += source.total_articles
            if source.is_active:
                by_type[source.source_type]['active'] += 1
        
        return {
            'total_sources': total_sources,
            'active_sources': active_sources,
            'total_articles': total_articles,
            'total_crawls': total_crawls,
            'successful_crawls': successful_crawls,
            'success_rate': round(success_rate, 2),
            'by_type': by_type,
            'recent_sources': [s.to_dict(include_stats=False) for s in sources[:5]]
        }
