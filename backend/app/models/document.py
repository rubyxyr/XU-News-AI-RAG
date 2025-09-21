"""
Document model for knowledge base content storage.
"""
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from app import db

# Association table for many-to-many relationship between documents and tags
document_tags = db.Table('document_tags',
    db.Column('document_id', db.Integer, db.ForeignKey('documents.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)


class Document(db.Model):
    """Document model for storing knowledge base content."""
    
    __tablename__ = 'documents'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Content fields
    title = db.Column(db.String(500), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    
    # Source information
    source_url = db.Column(db.String(1000))
    source_type = db.Column(db.String(50), nullable=False, index=True, default='manual')
    source_name = db.Column(db.String(200))
    author = db.Column(db.String(200))
    
    # Dates
    published_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Vector storage metadata
    vector_id = db.Column(db.String(255))  # FAISS vector ID
    embedding_model = db.Column(db.String(100), default='sentence-transformers/all-MiniLM-L6-v2')
    has_embeddings = db.Column(db.Boolean, default=False)
    
    # Content metadata
    word_count = db.Column(db.Integer, default=0)
    language = db.Column(db.String(10), default='en')
    content_type = db.Column(db.String(50), default='text/plain')
    
    # Status and processing
    is_processed = db.Column(db.Boolean, default=False)
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    processing_error = db.Column(db.Text)
    
    # Search and relevance
    view_count = db.Column(db.Integer, default=0)
    search_count = db.Column(db.Integer, default=0)  # How many times this doc appeared in search results
    relevance_score = db.Column(db.Float, default=0.0)  # Computed relevance score
    
    # Relationships
    tags = db.relationship('Tag', secondary=document_tags, lazy='subquery',
                          backref=db.backref('documents', lazy=True))
    
    def __repr__(self):
        return f'<Document {self.title[:50]}...>'
    
    @hybrid_property
    def content_preview(self):
        """Get a preview of the document content."""
        if not self.content:
            return ""
        words = self.content.split()[:50]  # First 50 words
        preview = ' '.join(words)
        if len(words) == 50:
            preview += "..."
        return preview
    
    def calculate_word_count(self):
        """Calculate and update word count."""
        if self.content:
            self.word_count = len(self.content.split())
        else:
            self.word_count = 0
    
    def increment_view_count(self):
        """Increment view count."""
        self.view_count += 1
        db.session.commit()
    
    def increment_search_count(self):
        """Increment search count (when document appears in search results)."""
        self.search_count += 1
        db.session.commit()
    
    def add_tag(self, tag_name):
        """Add a tag to the document."""
        from .tag import Tag
        
        # Find or create tag
        tag = Tag.query.filter_by(name=tag_name.lower().strip()).first()
        if not tag:
            tag = Tag(name=tag_name.lower().strip())
            db.session.add(tag)
            db.session.flush()  # Get tag ID
        
        # Add tag to document if not already present
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag_name):
        """Remove a tag from the document."""
        tag = next((t for t in self.tags if t.name == tag_name.lower().strip()), None)
        if tag:
            self.tags.remove(tag)
    
    def set_tags(self, tag_names):
        """Set document tags (replace existing tags)."""
        # Clear existing tags
        self.tags.clear()
        
        # Add new tags
        if tag_names:
            for tag_name in tag_names:
                if tag_name.strip():  # Skip empty tags
                    self.add_tag(tag_name.strip())
    
    def update_processing_status(self, status, error=None):
        """Update processing status."""
        allowed_statuses = ['pending', 'processing', 'completed', 'failed']
        if status in allowed_statuses:
            self.processing_status = status
            self.processing_error = error
            
            if status == 'completed':
                self.is_processed = True
                self.has_embeddings = True
            elif status == 'failed':
                self.is_processed = False
                self.has_embeddings = False
    
    def to_dict(self, include_content=True, include_embeddings_info=False):
        """Convert document to dictionary."""
        data = {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'source_url': self.source_url,
            'source_type': self.source_type,
            'source_name': self.source_name,
            'author': self.author,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'word_count': self.word_count,
            'language': self.language,
            'content_type': self.content_type,
            'view_count': self.view_count,
            'search_count': self.search_count,
            'relevance_score': self.relevance_score,
            'is_processed': self.is_processed,
            'processing_status': self.processing_status,
            'tags': [tag.name for tag in self.tags]
        }
        
        if include_content:
            data['content'] = self.content
            data['content_preview'] = self.content_preview
        
        if include_embeddings_info:
            data['vector_id'] = self.vector_id
            data['embedding_model'] = self.embedding_model
            data['has_embeddings'] = self.has_embeddings
            data['processing_error'] = self.processing_error
        
        return data
    
    def to_search_result(self, similarity_score=None, rank=None):
        """Convert document to search result format."""
        result = {
            'document_id': self.id,
            'title': self.title,
            'content_preview': self.content_preview,
            'source_url': self.source_url,
            'source_type': self.source_type,
            'source_name': self.source_name,
            'author': self.author,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'tags': [tag.name for tag in self.tags],
            'word_count': self.word_count,
            'relevance_score': self.relevance_score
        }
        
        if similarity_score is not None:
            result['similarity_score'] = similarity_score
        
        if rank is not None:
            result['rank'] = rank
        
        return result
    
    @staticmethod
    def create_document(user_id, title, content, **kwargs):
        """Create a new document."""
        # Extract tags before passing kwargs to constructor
        tags = kwargs.pop('tags', None)
        
        document = Document(
            user_id=user_id,
            title=title,
            content=content,
            **kwargs
        )
        
        # Calculate word count
        document.calculate_word_count()
        
        # Add document to session first
        db.session.add(document)
        db.session.flush()  # Get document ID
        
        # Set tags if provided
        if tags:
            document.set_tags(tags)
        
        db.session.commit()
        
        return document
    
    def update_content(self, **kwargs):
        """Update document content and metadata."""
        allowed_fields = [
            'title', 'content', 'summary', 'source_url', 'source_name', 
            'author', 'published_date', 'language', 'content_type'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(self, key, value)
        
        # Handle tags separately
        if 'tags' in kwargs:
            self.set_tags(kwargs['tags'])
        
        # Recalculate word count if content changed
        if 'content' in kwargs:
            self.calculate_word_count()
            # Mark for reprocessing if content changed
            self.update_processing_status('pending')
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_user_documents(cls, user_id, page=1, per_page=20, filters=None):
        """Get paginated documents for a user with optional filters."""
        query = cls.query.filter_by(user_id=user_id)
        
        if filters:
            # Filter by source type
            if filters.get('source_type'):
                query = query.filter(cls.source_type == filters['source_type'])
            
            # Filter by date range
            if filters.get('date_from'):
                query = query.filter(cls.published_date >= filters['date_from'])
            
            if filters.get('date_to'):
                query = query.filter(cls.published_date <= filters['date_to'])
            
            # Filter by tags
            if filters.get('tags'):
                tag_names = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                from .tag import Tag
                tag_ids = [tag.id for tag in Tag.query.filter(Tag.name.in_(tag_names)).all()]
                if tag_ids:
                    query = query.join(document_tags).filter(document_tags.c.tag_id.in_(tag_ids))
            
            # Search in title and content
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    db.or_(
                        cls.title.ilike(search_term),
                        cls.content.ilike(search_term),
                        cls.summary.ilike(search_term)
                    )
                )
            
            # Filter by processing status
            if filters.get('processing_status'):
                query = query.filter(cls.processing_status == filters['processing_status'])
        
        # Order by creation date (newest first)
        query = query.order_by(cls.created_at.desc())
        
        return query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    
    @classmethod
    def get_recent_documents(cls, user_id, limit=10):
        """Get recently created documents for a user."""
        return cls.query.filter_by(user_id=user_id)\
                      .order_by(cls.created_at.desc())\
                      .limit(limit)\
                      .all()
    
    @classmethod
    def get_popular_documents(cls, user_id, limit=10):
        """Get popular documents (by view count) for a user."""
        return cls.query.filter_by(user_id=user_id)\
                      .order_by(cls.view_count.desc())\
                      .limit(limit)\
                      .all()
    
    @classmethod
    def search_documents(cls, user_id, query_text, limit=50):
        """Simple text search in documents."""
        search_term = f"%{query_text}%"
        return db.session.query(cls).filter(
            cls.user_id == user_id,
            db.or_(
                cls.title.ilike(search_term),
                cls.content.ilike(search_term),
                cls.summary.ilike(search_term)
            )
        ).order_by(
            cls.relevance_score.desc(),
            cls.created_at.desc()
        ).limit(limit).all()
