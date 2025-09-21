"""
Analytics API endpoints for keyword analysis and usage statistics.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime, timedelta
from collections import Counter
import re

from app import db
from app.models import Document, SearchHistory, Tag
from app.utils.decorators import validate_json

bp = Blueprint('analytics', __name__)

# Validation Schemas
class AnalyticsQuerySchema(Schema):
    date_from = fields.Date()
    date_to = fields.Date()
    limit = fields.Int(validate=validate.Range(min=1, max=100), missing=10)


@bp.route('/keywords', methods=['GET'])
@jwt_required()
def get_keyword_distribution():
    """Get top keywords distribution from user's documents."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get query parameters
        limit = min(int(request.args.get('limit', 10)), 100)
        
        # Get all user documents
        documents = Document.query.filter_by(user_id=current_user_id).all()
        
        if not documents:
            return jsonify({
                'keywords': [],
                'total_documents': 0,
                'total_keywords': 0
            }), 200
        
        # Extract keywords from document content and titles
        keyword_counter = Counter()
        
        for doc in documents:
            # Extract keywords from title and content
            text = f"{doc.title} {doc.content or ''}"
            keywords = extract_keywords(text)
            keyword_counter.update(keywords)
        
        # Get top keywords
        top_keywords = []
        for keyword, count in keyword_counter.most_common(limit):
            top_keywords.append({
                'name': keyword,
                'count': count,
                'percentage': round((count / len(documents)) * 100, 2)
            })
        
        return jsonify({
            'keywords': top_keywords,
            'total_documents': len(documents),
            'total_keywords': len(keyword_counter)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get keyword distribution error: {e}")
        return jsonify({'error': 'Failed to get keyword distribution'}), 500


@bp.route('/search-history', methods=['GET'])
@jwt_required()
def get_search_analytics():
    """Get search analytics for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get query parameters
        days = int(request.args.get('days', 30))
        limit = min(int(request.args.get('limit', 50)), 100)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get search history
        search_history = SearchHistory.query.filter(
            SearchHistory.user_id == current_user_id,
            SearchHistory.timestamp >= start_date,
            SearchHistory.timestamp <= end_date
        ).order_by(SearchHistory.timestamp.desc()).limit(limit).all()
        
        # Analyze search patterns
        search_queries = [search.query for search in search_history]
        query_counter = Counter(search_queries)
        
        # Get top searches
        top_searches = []
        for query, count in query_counter.most_common(10):
            top_searches.append({
                'query': query,
                'count': count,
                'last_searched': max([s.timestamp for s in search_history if s.query == query])
            })
        
        # Calculate statistics
        total_searches = len(search_history)
        unique_queries = len(query_counter)
        avg_searches_per_day = total_searches / max(days, 1)
        
        return jsonify({
            'summary': {
                'total_searches': total_searches,
                'unique_queries': unique_queries,
                'avg_searches_per_day': round(avg_searches_per_day, 2),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            },
            'top_searches': top_searches,
            'recent_searches': [
                {
                    'query': search.query,
                    'timestamp': search.timestamp.isoformat(),
                    'results_count': len(search.results) if search.results else 0
                }
                for search in search_history[:20]
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get search analytics error: {e}")
        return jsonify({'error': 'Failed to get search analytics'}), 500


@bp.route('/document-stats', methods=['GET'])
@jwt_required()
def get_document_statistics():
    """Get document statistics for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get documents with statistics
        documents = Document.query.filter_by(user_id=current_user_id).all()
        
        if not documents:
            return jsonify({
                'total_documents': 0,
                'by_source_type': {},
                'by_date': {},
                'by_tags': {},
                'content_stats': {
                    'total_words': 0,
                    'avg_words_per_document': 0
                }
            }), 200
        
        # Statistics by source type
        source_type_stats = Counter()
        for doc in documents:
            source_type_stats[doc.source_type or 'unknown'] += 1
        
        # Statistics by creation date (last 30 days)
        date_stats = {}
        end_date = datetime.now()
        for i in range(30):
            date = end_date - timedelta(days=i)
            date_key = date.strftime('%Y-%m-%d')
            date_stats[date_key] = 0
        
        for doc in documents:
            if doc.created_at:
                doc_date = doc.created_at.strftime('%Y-%m-%d')
                if doc_date in date_stats:
                    date_stats[doc_date] += 1
        
        # Statistics by tags
        tag_stats = Counter()
        for doc in documents:
            for tag in doc.tags:
                tag_stats[tag.name] += 1
        
        # Content statistics
        total_words = 0
        word_counts = []
        
        for doc in documents:
            if doc.content:
                word_count = len(doc.content.split())
                total_words += word_count
                word_counts.append(word_count)
        
        avg_words = total_words / len(documents) if documents else 0
        
        return jsonify({
            'total_documents': len(documents),
            'by_source_type': dict(source_type_stats),
            'by_date': date_stats,
            'by_tags': dict(tag_stats.most_common(20)),
            'content_stats': {
                'total_words': total_words,
                'avg_words_per_document': round(avg_words, 2),
                'max_words': max(word_counts) if word_counts else 0,
                'min_words': min(word_counts) if word_counts else 0
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get document statistics error: {e}")
        return jsonify({'error': 'Failed to get document statistics'}), 500


@bp.route('/clustering-report', methods=['GET'])
@jwt_required()
def get_clustering_report():
    """Get data clustering analysis report."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get all user documents
        documents = Document.query.filter_by(user_id=current_user_id).all()
        
        if not documents:
            return jsonify({
                'clusters': [],
                'keyword_distribution': [],
                'total_documents': 0
            }), 200
        
        # Simple clustering based on common keywords
        clusters = perform_simple_clustering(documents)
        
        # Get keyword distribution
        all_text = " ".join([f"{doc.title} {doc.content or ''}" for doc in documents])
        keywords = extract_keywords(all_text)
        keyword_counter = Counter(keywords)
        
        # Top 10 keyword distribution
        top_keywords = []
        total_keywords = sum(keyword_counter.values())
        
        for keyword, count in keyword_counter.most_common(10):
            percentage = (count / total_keywords) * 100 if total_keywords > 0 else 0
            top_keywords.append({
                'keyword': keyword,
                'count': count,
                'percentage': round(percentage, 2)
            })
        
        return jsonify({
            'clusters': clusters,
            'keyword_distribution': top_keywords,
            'total_documents': len(documents),
            'total_unique_keywords': len(keyword_counter),
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get clustering report error: {e}")
        return jsonify({'error': 'Failed to generate clustering report'}), 500


def extract_keywords(text, min_length=3, max_keywords=100):
    """
    Extract keywords from text using simple NLP techniques.
    
    Args:
        text: Input text
        min_length: Minimum keyword length
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Convert to lowercase and extract words
    text = text.lower()
    
    # Remove special characters and extract words
    words = re.findall(r'\b[a-z]+\b', text)
    
    # Common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
        'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our',
        'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they',
        'them', 'their', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
        'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 'can', 'just', 'now', 'also', 'here', 'there', 'then'
    }
    
    # Filter words
    keywords = []
    for word in words:
        if (len(word) >= min_length and 
            word not in stop_words and 
            not word.isdigit()):
            keywords.append(word)
    
    # Count frequency and return most common
    keyword_counter = Counter(keywords)
    return [word for word, count in keyword_counter.most_common(max_keywords) if count > 1]


def perform_simple_clustering(documents, max_clusters=5):
    """
    Perform simple clustering based on keyword similarity.
    
    Args:
        documents: List of document objects
        max_clusters: Maximum number of clusters
        
    Returns:
        List of cluster dictionaries
    """
    if not documents:
        return []
    
    # Extract keywords for each document
    doc_keywords = []
    for doc in documents:
        text = f"{doc.title} {doc.content or ''}"
        keywords = set(extract_keywords(text, max_keywords=20))
        doc_keywords.append((doc, keywords))
    
    # Simple clustering based on keyword overlap
    clusters = []
    used_docs = set()
    
    for i, (doc1, keywords1) in enumerate(doc_keywords):
        if doc1.id in used_docs:
            continue
        
        cluster_docs = [doc1]
        used_docs.add(doc1.id)
        
        # Find similar documents
        for j, (doc2, keywords2) in enumerate(doc_keywords[i+1:], i+1):
            if doc2.id in used_docs:
                continue
            
            # Calculate similarity (Jaccard similarity)
            if keywords1 and keywords2:
                intersection = len(keywords1.intersection(keywords2))
                union = len(keywords1.union(keywords2))
                similarity = intersection / union if union > 0 else 0
                
                # If similarity is high enough, add to cluster
                if similarity > 0.2:  # 20% similarity threshold
                    cluster_docs.append(doc2)
                    used_docs.add(doc2.id)
        
        # Only create cluster if it has more than one document or unique keywords
        if len(cluster_docs) > 1 or len(keywords1) > 5:
            # Get cluster keywords
            all_cluster_keywords = set()
            for doc in cluster_docs:
                text = f"{doc.title} {doc.content or ''}"
                doc_kws = extract_keywords(text, max_keywords=10)
                all_cluster_keywords.update(doc_kws[:5])  # Top 5 keywords per doc
            
            cluster_name = generate_cluster_name(list(all_cluster_keywords), cluster_docs)
            
            clusters.append({
                'name': cluster_name,
                'document_count': len(cluster_docs),
                'keywords': list(all_cluster_keywords)[:10],
                'documents': [
                    {
                        'id': doc.id,
                        'title': doc.title,
                        'source_type': doc.source_type,
                        'created_at': doc.created_at.isoformat() if doc.created_at else None
                    }
                    for doc in cluster_docs[:5]  # Show max 5 documents per cluster
                ]
            })
        
        # Limit number of clusters
        if len(clusters) >= max_clusters:
            break
    
    return clusters


def generate_cluster_name(keywords, documents):
    """Generate a meaningful name for a cluster."""
    if not keywords:
        return f"Documents ({len(documents)})"
    
    # Use most common keywords
    keyword_counter = Counter()
    for doc in documents:
        text = f"{doc.title} {doc.content or ''}"
        doc_keywords = extract_keywords(text, max_keywords=10)
        keyword_counter.update(doc_keywords)
    
    if keyword_counter:
        top_keyword = keyword_counter.most_common(1)[0][0]
        return f"{top_keyword.title()} Related"
    
    return f"Cluster ({len(documents)} docs)"


# Error handlers
@bp.errorhandler(ValidationError)
def handle_validation_error(e):
    """Handle marshmallow validation errors."""
    return jsonify({'error': 'Validation failed', 'details': e.messages}), 400
