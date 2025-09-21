"""
Tag model for document categorization and organization.
"""
from datetime import datetime
from sqlalchemy import func
from app import db


class Tag(db.Model):
    """Tag model for document categorization."""
    
    __tablename__ = 'tags'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Metadata
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#1976D2')  # Hex color code
    
    # Statistics
    usage_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tag {self.name}>'
    
    def increment_usage(self):
        """Increment usage count."""
        self.usage_count += 1
        db.session.commit()
    
    def decrement_usage(self):
        """Decrement usage count."""
        if self.usage_count > 0:
            self.usage_count -= 1
        db.session.commit()
    
    def update_usage_count(self):
        """Update usage count based on actual document associations."""
        from .document import document_tags
        
        count = db.session.query(func.count(document_tags.c.document_id))\
                         .filter(document_tags.c.tag_id == self.id)\
                         .scalar()
        
        self.usage_count = count or 0
        db.session.commit()
    
    def to_dict(self, include_stats=True):
        """Convert tag to dictionary."""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_stats:
            data['usage_count'] = self.usage_count
        
        return data
    
    @staticmethod
    def create_tag(name, **kwargs):
        """Create a new tag."""
        # Normalize tag name
        name = name.lower().strip()
        
        # Check if tag already exists
        existing_tag = Tag.query.filter_by(name=name).first()
        if existing_tag:
            return existing_tag
        
        tag = Tag(name=name, **kwargs)
        db.session.add(tag)
        db.session.commit()
        
        return tag
    
    def update_tag(self, **kwargs):
        """Update tag properties."""
        allowed_fields = ['description', 'color']
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_or_create(cls, name, **kwargs):
        """Get existing tag or create new one."""
        name = name.lower().strip()
        tag = cls.query.filter_by(name=name).first()
        
        if not tag:
            tag = cls.create_tag(name, **kwargs)
        
        return tag
    
    @classmethod
    def get_popular_tags(cls, limit=20, min_usage=1):
        """Get most popular tags."""
        return cls.query.filter(cls.usage_count >= min_usage)\
                       .order_by(cls.usage_count.desc())\
                       .limit(limit)\
                       .all()
    
    @classmethod
    def get_user_tags(cls, user_id, limit=None):
        """Get tags used by a specific user."""
        from .document import Document, document_tags
        
        query = cls.query.join(document_tags)\
                        .join(Document)\
                        .filter(Document.user_id == user_id)\
                        .group_by(cls.id)\
                        .order_by(func.count(document_tags.c.document_id).desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def search_tags(cls, query_text, limit=20):
        """Search tags by name."""
        search_term = f"%{query_text.lower()}%"
        return cls.query.filter(cls.name.ilike(search_term))\
                       .order_by(cls.usage_count.desc())\
                       .limit(limit)\
                       .all()
    
    @classmethod
    def get_tag_statistics(cls, user_id=None):
        """Get tag usage statistics."""
        if user_id:
            # User-specific tag stats
            from .document import Document, document_tags
            
            # Get user's tags with counts
            user_tags = db.session.query(
                cls.id,
                cls.name,
                func.count(document_tags.c.document_id).label('doc_count')
            ).join(document_tags)\
             .join(Document)\
             .filter(Document.user_id == user_id)\
             .group_by(cls.id, cls.name)\
             .order_by(func.count(document_tags.c.document_id).desc())\
             .all()
            
            total_tags = len(user_tags)
            most_used = user_tags[0] if user_tags else None
            
            return {
                'total_tags': total_tags,
                'most_used_tag': {
                    'name': most_used.name,
                    'count': most_used.doc_count
                } if most_used else None,
                'top_10': [
                    {'name': tag.name, 'count': tag.doc_count}
                    for tag in user_tags[:10]
                ],
                'distribution': [
                    {'name': tag.name, 'count': tag.doc_count}
                    for tag in user_tags
                ]
            }
        else:
            # Global tag stats
            total_tags = cls.query.count()
            most_used = cls.query.order_by(cls.usage_count.desc()).first()
            
            return {
                'total_tags': total_tags,
                'most_used_tag': {
                    'name': most_used.name,
                    'count': most_used.usage_count
                } if most_used else None,
                'top_10': [
                    tag.to_dict()
                    for tag in cls.get_popular_tags(limit=10)
                ]
            }
    
    @classmethod
    def cleanup_unused_tags(cls, min_usage=1):
        """Remove tags with usage count below threshold."""
        unused_tags = cls.query.filter(cls.usage_count < min_usage).all()
        
        for tag in unused_tags:
            db.session.delete(tag)
        
        db.session.commit()
        return len(unused_tags)
    
    @classmethod
    def update_all_usage_counts(cls):
        """Update usage counts for all tags."""
        from .document import document_tags
        
        # Get actual counts from junction table
        tag_counts = db.session.query(
            document_tags.c.tag_id,
            func.count(document_tags.c.document_id).label('count')
        ).group_by(document_tags.c.tag_id).all()
        
        # Update each tag
        for tag_id, count in tag_counts:
            tag = cls.query.get(tag_id)
            if tag:
                tag.usage_count = count
        
        # Set count to 0 for tags not in the results
        unused_tag_ids = db.session.query(cls.id)\
                                  .filter(~cls.id.in_([tc.tag_id for tc in tag_counts]))\
                                  .all()
        
        for (tag_id,) in unused_tag_ids:
            tag = cls.query.get(tag_id)
            if tag:
                tag.usage_count = 0
        
        db.session.commit()
