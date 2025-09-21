"""
Search history model for tracking user search patterns and analytics.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db


class SearchHistory(db.Model):
    """Search history model for tracking user queries and results."""
    
    __tablename__ = 'search_history'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Search details
    query = db.Column(db.Text, nullable=False, index=True)
    query_type = db.Column(db.String(50), default='semantic')  # semantic, keyword, hybrid
    
    # Results information
    results_count = db.Column(db.Integer, default=0)
    has_external_results = db.Column(db.Boolean, default=False)
    external_results_count = db.Column(db.Integer, default=0)
    
    # Performance metrics
    search_time = db.Column(db.Float)  # seconds
    processing_time = db.Column(db.Float)  # seconds for AI processing
    
    # Search parameters
    search_filters = db.Column(db.JSON, default=dict)  # filters applied
    result_limit = db.Column(db.Integer, default=10)
    
    # User interaction
    clicked_results = db.Column(db.JSON, default=list)  # list of clicked document IDs
    saved_results = db.Column(db.JSON, default=list)  # list of saved document IDs
    user_feedback = db.Column(db.String(20))  # 'helpful', 'not_helpful', 'partially_helpful'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<SearchHistory {self.query[:50]}...>'
    
    def add_click(self, document_id):
        """Record a click on a search result."""
        if not self.clicked_results:
            self.clicked_results = []
        
        if document_id not in self.clicked_results:
            self.clicked_results.append(document_id)
            db.session.commit()
    
    def add_save(self, document_id):
        """Record saving a search result."""
        if not self.saved_results:
            self.saved_results = []
        
        if document_id not in self.saved_results:
            self.saved_results.append(document_id)
            db.session.commit()
    
    def set_feedback(self, feedback):
        """Set user feedback for this search."""
        allowed_feedback = ['helpful', 'not_helpful', 'partially_helpful']
        if feedback in allowed_feedback:
            self.user_feedback = feedback
            db.session.commit()
    
    def get_click_through_rate(self):
        """Calculate click-through rate."""
        if self.results_count == 0:
            return 0.0
        
        clicks = len(self.clicked_results) if self.clicked_results else 0
        return (clicks / self.results_count) * 100
    
    def get_save_rate(self):
        """Calculate save rate."""
        if self.results_count == 0:
            return 0.0
        
        saves = len(self.saved_results) if self.saved_results else 0
        return (saves / self.results_count) * 100
    
    def to_dict(self, include_interactions=False):
        """Convert search history to dictionary."""
        data = {
            'id': self.id,
            'query': self.query,
            'query_type': self.query_type,
            'results_count': self.results_count,
            'has_external_results': self.has_external_results,
            'external_results_count': self.external_results_count,
            'search_time': self.search_time,
            'processing_time': self.processing_time,
            'search_filters': self.search_filters,
            'result_limit': self.result_limit,
            'user_feedback': self.user_feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'click_through_rate': self.get_click_through_rate(),
            'save_rate': self.get_save_rate()
        }
        
        if include_interactions:
            data.update({
                'clicked_results': self.clicked_results or [],
                'saved_results': self.saved_results or [],
                'total_clicks': len(self.clicked_results) if self.clicked_results else 0,
                'total_saves': len(self.saved_results) if self.saved_results else 0
            })
        
        return data
    
    @staticmethod
    def create_search_record(user_id, query, query_type='semantic', **kwargs):
        """Create a new search history record."""
        search_record = SearchHistory(
            user_id=user_id,
            query=query,
            query_type=query_type,
            **kwargs
        )
        
        db.session.add(search_record)
        db.session.commit()
        
        return search_record
    
    def update_results(self, results_count, search_time=None, has_external=False, external_count=0):
        """Update search results information."""
        self.results_count = results_count
        self.has_external_results = has_external
        self.external_results_count = external_count
        
        if search_time is not None:
            self.search_time = search_time
        
        db.session.commit()
    
    @classmethod
    def get_user_history(cls, user_id, limit=50, days=None):
        """Get user's search history with optional date filtering."""
        search_query = db.session.query(cls).filter_by(user_id=user_id)
        
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            search_query = search_query.filter(cls.created_at >= cutoff_date)
        
        return search_query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_popular_queries(cls, user_id=None, limit=10, days=30):
        """Get most popular search queries."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Use db.session.query to avoid naming conflict with the query column
        popular_queries = db.session.query(
            cls.query,
            func.count(cls.id).label('count'),
            func.avg(cls.results_count).label('avg_results'),
            func.avg(cls.search_time).label('avg_time')
        ).filter(cls.created_at >= cutoff_date)
        
        if user_id:
            popular_queries = popular_queries.filter(cls.user_id == user_id)
            
        popular_queries = popular_queries.group_by(cls.query)\
                                       .order_by(func.count(cls.id).desc())\
                                       .limit(limit)\
                                       .all()

        return [
            {
                'query': pq[0],  # First column is the query text
                'count': pq[1],  # Second column is the count
                'avg_results': round(pq[2] or 0, 2),  # Third column is avg_results
                'avg_search_time': round(pq[3] or 0, 3)  # Fourth column is avg_time
            }
            for pq in popular_queries
        ]
    
    @classmethod
    def get_search_analytics(cls, user_id, days=30):
        """Get comprehensive search analytics for a user."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        searches = db.session.query(cls).filter(
            cls.user_id == user_id,
            cls.created_at >= cutoff_date
        ).all()
        
        if not searches:
            return {
                'total_searches': 0,
                'avg_results_per_search': 0,
                'avg_search_time': 0,
                'total_clicks': 0,
                'total_saves': 0,
                'avg_click_through_rate': 0,
                'feedback_distribution': {},
                'query_types': {},
                'daily_activity': [],
                'popular_queries': []
            }
        
        total_searches = len(searches)
        total_results = sum(s.results_count for s in searches)
        total_time = sum(s.search_time for s in searches if s.search_time)
        total_clicks = sum(len(s.clicked_results) if s.clicked_results else 0 for s in searches)
        total_saves = sum(len(s.saved_results) if s.saved_results else 0 for s in searches)
        
        # Calculate averages
        avg_results = total_results / total_searches if total_searches > 0 else 0
        avg_time = total_time / len([s for s in searches if s.search_time]) if any(s.search_time for s in searches) else 0
        avg_ctr = sum(s.get_click_through_rate() for s in searches) / total_searches
        
        # Feedback distribution
        feedback_dist = {}
        for search in searches:
            if search.user_feedback:
                feedback_dist[search.user_feedback] = feedback_dist.get(search.user_feedback, 0) + 1
        
        # Query type distribution
        query_types = {}
        for search in searches:
            query_types[search.query_type] = query_types.get(search.query_type, 0) + 1
        
        # Daily activity (last 30 days)
        daily_activity = []
        for i in range(days):
            day = datetime.utcnow() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_searches = [s for s in searches if day_start <= s.created_at < day_end]
            daily_activity.append({
                'date': day_start.date().isoformat(),
                'searches': len(day_searches),
                'avg_results': sum(s.results_count for s in day_searches) / len(day_searches) if day_searches else 0
            })
        
        daily_activity.reverse()  # Chronological order
        
        return {
            'total_searches': total_searches,
            'avg_results_per_search': round(avg_results, 2),
            'avg_search_time': round(avg_time, 3),
            'total_clicks': total_clicks,
            'total_saves': total_saves,
            'avg_click_through_rate': round(avg_ctr, 2),
            'feedback_distribution': feedback_dist,
            'query_types': query_types,
            'daily_activity': daily_activity,
            'popular_queries': cls.get_popular_queries(user_id, limit=5, days=days)
        }
    
    @classmethod
    def get_recent_searches(cls, user_id, limit=10):
        """Get user's most recent searches."""
        return db.session.query(cls).filter_by(user_id=user_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit)\
                       .all()
    
    @classmethod
    def cleanup_old_searches(cls, days=90):
        """Remove search history older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_searches = db.session.query(cls).filter(cls.created_at < cutoff_date)
        count = old_searches.count()
        old_searches.delete()
        
        db.session.commit()
        return count
