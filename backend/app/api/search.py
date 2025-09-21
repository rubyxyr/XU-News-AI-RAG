"""
Search API endpoints for semantic and traditional search functionality.
"""
from flask import Blueprint, request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime
from pathlib import Path
import time
import json
import logging

from app import db
from app.models import Document, SearchHistory
from app.utils.decorators import validate_json, rate_limit
from app.utils.validators import validate_search_query

bp = Blueprint('search', __name__)

# Create logger for streaming functions (outside Flask context)
stream_logger = logging.getLogger(__name__ + '.stream')

def get_logger():
    """Get appropriate logger based on context."""
    try:
        # Try to use Flask's app logger if we're in app context
        return current_app.logger
    except RuntimeError:
        # Fall back to stream logger if outside Flask context
        return stream_logger

# Validation Schemas
class SearchSchema(Schema):
    query = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    search_type = fields.Str(validate=validate.OneOf(['semantic', 'keyword', 'hybrid']), missing='semantic')
    limit = fields.Int(validate=validate.Range(min=1, max=100), missing=10)
    include_external = fields.Bool(missing=True)
    filters = fields.Dict(missing={})


class SearchFeedbackSchema(Schema):
    search_id = fields.Int(required=True)
    feedback = fields.Str(required=True, validate=validate.OneOf(['helpful', 'not_helpful', 'partially_helpful']))


class ResultInteractionSchema(Schema):
    search_id = fields.Int(required=True)
    document_id = fields.Int(required=True)
    action = fields.Str(required=True, validate=validate.OneOf(['click', 'save']))


def create_sse_response(data, event_type='data'):
    """Create a Server-Sent Event formatted response."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def stream_semantic_search(current_user_id, query, search_type, limit, include_external, filters):
    """Generator function that streams search progress and results."""
    try:
        yield create_sse_response({
            'status': 'starting',
            'message': 'Initializing semantic search...',
            'progress': 0
        }, 'progress')
        
        # Validate query
        is_valid, message = validate_search_query(query)
        if not is_valid:
            yield create_sse_response({
                'status': 'error',
                'message': message
            }, 'error')
            return
        
        start_time = time.time()
        
        # Create search history record
        yield create_sse_response({
            'status': 'progress',
            'message': 'Creating search record...',
            'progress': 5
        }, 'progress')
        
        search_record = SearchHistory.create_search_record(
            user_id=current_user_id,
            query=query,
            query_type=search_type,
            search_filters=filters,
            result_limit=limit
        )
        
        results = []
        min_relevance_score = 0.0
        
        try:
            # Use actual semantic search with AI pipeline
            if search_type == 'semantic':
                yield create_sse_response({
                    'status': 'progress',
                    'message': 'Loading AI models for semantic search...',
                    'progress': 15
                }, 'progress')
                
                try:
                    from app.ai.langchain_service import LangChainService
                    
                    # Initialize with current app config
                    config = {
                        'EMBEDDINGS_MODEL': current_app.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
                        'VECTOR_STORE_PATH': current_app.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
                        'LLM_MODEL': current_app.config.get('LLM_MODEL', 'qwen3:4b'),
                        'OLLAMA_BASE_URL': current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
                        'RERANKER_MODEL': current_app.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                    }
                    
                    yield create_sse_response({
                        'status': 'progress',
                        'message': 'Initializing LangChain AI service...',
                        'progress': 25
                    }, 'progress')
                    
                    ai_service = LangChainService(config=config)
                    
                    yield create_sse_response({
                        'status': 'progress',
                        'message': 'Performing semantic search with AI embeddings...',
                        'progress': 35
                    }, 'progress')
                    
                    # Perform semantic search using vector embeddings
                    score_threshold = 0.6
                    results_with_scores = ai_service.semantic_search(
                        user_id=str(current_user_id), 
                        query=query, 
                        k=limit,
                        filters=filters,
                        score_threshold=score_threshold
                    )
                    
                    # Extract documents and calculate relevance threshold
                    # Filter results with semantic score > 0.3 for quality matches (using reciprocal similarity)
                    filtered_results = []
                    min_relevance_score = 0.0
                    
                    for doc, score in results_with_scores:
                        current_app.logger.info(f"[+] Semantic score: {score}")
                        if score >= score_threshold:
                            filtered_results.append((doc, score))
                            if score > min_relevance_score:
                                min_relevance_score = score
                    
                    # Sort by relevance score (descending - highest scores first)
                    filtered_results.sort(key=lambda x: x[1], reverse=True)
                    
                    # Extract documents for compatibility with existing code
                    results = [doc for doc, score in filtered_results]
                    
                    current_app.logger.info(f"Filtered {len(results_with_scores)} results to {len(results)} results above score threshold {score_threshold}, sorted by relevance")
                    
                    # Store minimum relevance for external search decision
                    if not search_record.search_filters:
                        search_record.search_filters = {}
                    search_record.search_filters['min_relevance_score'] = min_relevance_score
                    
                    yield create_sse_response({
                        'status': 'progress',
                        'message': f'LangChain semantic search completed: {len(results)} results found',
                        'progress': 60,
                        'results_count': len(results),
                        'min_relevance': min_relevance_score
                    }, 'progress')
                    
                    current_app.logger.info(f"LangChain semantic search returned {len(results)} results with min_relevance: {min_relevance_score}")
                    
                except Exception as e:
                    current_app.logger.error(f"LangChain semantic search failed, trying direct sentence-transformer approach: {e}")
                    
                    yield create_sse_response({
                        'status': 'progress',
                        'message': 'LangChain failed, trying direct semantic search...',
                        'progress': 30
                    }, 'progress')
                    
                    # Try direct sentence-transformer approach as fallback
                    try:
                        yield create_sse_response({
                            'status': 'progress',
                            'message': 'Loading sentence transformer model...',
                            'progress': 40
                        }, 'progress')
                        
                        direct_results = perform_direct_semantic_search(current_user_id, query, limit, filters)
                        
                        # Extract documents and calculate relevance scores
                        filtered_results = direct_results  # This contains (doc, score) tuples
                        results = [doc for doc, score in filtered_results]
                        
                        # Calculate minimum relevance score based on results
                        min_relevance_score = max([score for doc, score in filtered_results]) if filtered_results else 0.0
                        
                        if not search_record.search_filters:
                            search_record.search_filters = {}
                        search_record.search_filters['min_relevance_score'] = min_relevance_score
                        
                        yield create_sse_response({
                            'status': 'progress',
                            'message': f'Direct semantic search completed: {len(results)} results found',
                            'progress': 60,
                            'results_count': len(results)
                        }, 'progress')
                        
                        current_app.logger.info(f"Direct semantic search returned {len(results)} results")
                        
                    except Exception as fallback_error:
                        current_app.logger.error(f"Direct semantic search also failed, using keyword search: {fallback_error}")
                        
                        yield create_sse_response({
                            'status': 'progress',
                            'message': 'Semantic search failed, falling back to keyword search...',
                            'progress': 45
                        }, 'progress')
                        
                        # Final fallback to keyword search
                        results = perform_keyword_search(current_user_id, query, limit, filters)
                        if not search_record.search_filters:
                            search_record.search_filters = {}
                        search_record.search_filters['min_relevance_score'] = 0.6
                        
                        yield create_sse_response({
                            'status': 'progress',
                            'message': f'Keyword search completed: {len(results)} results found',
                            'progress': 60,
                            'results_count': len(results)
                        }, 'progress')
                
            else:
                yield create_sse_response({
                    'status': 'progress',
                    'message': 'Performing keyword search...',
                    'progress': 30
                }, 'progress')
                
                # Fall back to keyword/hybrid search
                results = perform_keyword_search(current_user_id, query, limit, filters)
                if not search_record.search_filters:
                    search_record.search_filters = {}
                search_record.search_filters['min_relevance_score'] = 0.6  # Default threshold
                
                yield create_sse_response({
                    'status': 'progress',
                    'message': f'Keyword search completed: {len(results)} results found',
                    'progress': 60,
                    'results_count': len(results)
                }, 'progress')
            
            # External search if enabled and knowledge base results are insufficient
            external_results = []
            should_search_external = False
            
            if include_external:
                yield create_sse_response({
                    'status': 'progress',
                    'message': 'Evaluating need for external search...',
                    'progress': 70
                }, 'progress')
                
                # Determine if knowledge base results are insufficient based on:
                # 1. No results at all
                # 2. Few results (< 3) 
                # 3. Low relevance scores (< 0.3 for semantic search with reciprocal similarity)
                min_relevance = search_record.search_filters.get('min_relevance_score', 0.0) if search_record.search_filters else 0.0
                
                should_search_external = (
                    len(results) == 0 or  # No results
                    len(results) < 3 or   # Few results 
                    (search_type == 'semantic' and min_relevance < 0.4)  # Low relevance
                )
            
            if should_search_external:
                try:
                    current_app.logger.info(f"Triggering external search - results: {len(results)}, min_relevance: {search_record.search_filters.get('min_relevance_score', 0.0) if search_record.search_filters else 0.0}")
                    
                    # Use streaming external search generator
                    external_results = []
                    for progress_data in perform_external_search_streaming(query, 3):
                        # Emit progress updates
                        if progress_data.get('results') is None:
                            # Progress update - forward to client
                            yield create_sse_response(progress_data, 'progress')
                        else:
                            # Final results - store them
                            external_results = progress_data.get('results', [])
                            yield create_sse_response({
                                'status': 'progress',
                                'message': progress_data.get('message', 'External search completed'),
                                'progress': progress_data.get('progress', 90),
                                'external_results_count': len(external_results),
                                'external_search': True
                            }, 'progress')
                    
                except Exception as e:
                    current_app.logger.error(f"External search error: {e}")
                    yield create_sse_response({
                        'status': 'warning',
                        'message': f'External search failed: {str(e)}',
                        'progress': 90
                    }, 'warning')
            else:
                yield create_sse_response({
                    'status': 'progress',
                    'message': 'Skipping external search - sufficient results found',
                    'progress': 90
                }, 'progress')
            
            end_time = time.time()
            search_time = end_time - start_time
            
            yield create_sse_response({
                'status': 'progress',
                'message': 'Finalizing search results...',
                'progress': 95
            }, 'progress')
            
            # Update search record
            search_record.update_results(
                results_count=len(results),
                search_time=search_time,
                has_external=len(external_results) > 0,
                external_count=len(external_results)
            )
            
            # Format results with relevance scores
            formatted_results = []
            # Use filtered_results if available (contains scores), otherwise fallback to results
            if 'filtered_results' in locals():
                results_to_format = filtered_results
            else:
                # Fallback for other search methods that don't preserve scores
                results_to_format = [(doc, None) for doc in results]
            
            for i, (doc, score) in enumerate(results_to_format):
                result = doc.to_search_result(rank=i + 1)
                # Add relevance score to the result
                if score is not None:
                    result['relevance_score'] = round(score, 3)
                # Increment search count for this document
                doc.increment_search_count()
                formatted_results.append(result)
            
            # Send final results
            final_response = {
                'status': 'completed',
                'results': formatted_results,
                'external_results': external_results,
                'search_metadata': {
                    'search_id': search_record.id,
                    'query': query,
                    'search_type': search_type,
                    'total_results': len(results),
                    'search_time': round(search_time, 3),
                    'has_external_results': len(external_results) > 0,
                    'external_results_count': len(external_results)
                },
                'progress': 100
            }
            
            yield create_sse_response(final_response, 'result')
            yield create_sse_response({'status': 'done'}, 'done')
            
        except Exception as e:
            # Update search record with error
            search_record.update_results(0, time.time() - start_time)
            yield create_sse_response({
                'status': 'error',
                'message': f'Search processing failed: {str(e)}',
                'error': str(e)
            }, 'error')
            
    except Exception as e:
        current_app.logger.error(f"Stream semantic search error: {e}")
        yield create_sse_response({
            'status': 'error',
            'message': f'Search failed: {str(e)}',
            'error': str(e)
        }, 'error')


@bp.route('/semantic', methods=['POST'])
@jwt_required()
@rate_limit(requests_per_minute=30)  # Limit AI-powered searches
@validate_json(SearchSchema)
def semantic_search(validated_data):
    """Perform semantic search using AI embeddings with streaming response."""
    try:
        current_user_id = int(get_jwt_identity())
        query = validated_data['query']
        search_type = validated_data['search_type']
        limit = validated_data['limit']
        # include_external = validated_data['include_external']
        include_external = True
        filters = validated_data.get('filters', {})
        
        # Store the current Flask application context
        app_context = current_app._get_current_object()
        
        # Create streaming response with Flask context
        def generate():
            with app_context.app_context():
                try:
                    yield from stream_semantic_search(
                        current_user_id=current_user_id,
                        query=query,
                        search_type=search_type,
                        limit=limit,
                        include_external=include_external,
                        filters=filters
                    )
                except Exception as e:
                    current_app.logger.error(f"Stream generation error: {e}")
                    yield create_sse_response({
                        'status': 'error',
                        'message': f'Search failed: {str(e)}',
                        'error': str(e)
                    }, 'error')
        
        # Return streaming response with proper headers
        return Response(
            generate(),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'X-Accel-Buffering': 'no'  # Disable nginx buffering for streaming
            }
        )
            
    except Exception as e:
        current_app.logger.error(f"Semantic search endpoint error: {e}")
        return jsonify({'error': 'Search failed'}), 500


@bp.route('/suggestions', methods=['GET'])
@jwt_required()
def get_search_suggestions():
    """Get search suggestions based on user's search history."""
    try:
        current_user_id = int(get_jwt_identity())
        query = request.args.get('q', '').strip()
        limit = min(request.args.get('limit', 10, type=int), 20)
        
        suggestions = []
        
        if query:
            # Get similar queries from search history
            similar_searches = db.session.query(SearchHistory).filter(
                SearchHistory.user_id == current_user_id,
                SearchHistory.query.ilike(f'%{query}%')
            ).order_by(SearchHistory.created_at.desc())\
             .limit(limit)\
             .all()
            
            suggestions = [{'query': search.query, 'type': 'history'} for search in similar_searches]
        else:
            # Get popular queries for this user
            popular_queries = SearchHistory.get_popular_queries(current_user_id, limit=limit)
            suggestions = [{'query': pq['query'], 'type': 'popular'} for pq in popular_queries]
        
        return jsonify({
            'suggestions': suggestions,
            'query': query
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get search suggestions error: {e}")
        return jsonify({'error': 'Failed to get suggestions'}), 500


@bp.route('/history', methods=['GET'])
@jwt_required()
def get_search_history():
    """Get user's search history."""
    try:
        current_user_id = int(get_jwt_identity())
        limit = min(request.args.get('limit', 20, type=int), 100)
        days = request.args.get('days', type=int)
        
        searches = SearchHistory.get_user_history(current_user_id, limit, days)
        
        return jsonify({
            'searches': [search.to_dict() for search in searches],
            'count': len(searches)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get search history error: {e}")
        return jsonify({'error': 'Failed to get search history'}), 500


@bp.route('/feedback', methods=['POST'])
@jwt_required()
@validate_json(SearchFeedbackSchema)
def provide_search_feedback(validated_data):
    """Provide feedback on search results."""
    try:
        current_user_id = int(get_jwt_identity())
        search_id = validated_data['search_id']
        feedback = validated_data['feedback']
        
        # Verify search belongs to user
        search_record = SearchHistory.query.filter_by(
            id=search_id,
            user_id=current_user_id
        ).first()
        
        if not search_record:
            return jsonify({'error': 'Search record not found'}), 404
        
        # Update feedback
        search_record.set_feedback(feedback)
        
        return jsonify({'message': 'Feedback recorded successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Search feedback error: {e}")
        return jsonify({'error': 'Failed to record feedback'}), 500


@bp.route('/interaction', methods=['POST'])
@jwt_required()
@validate_json(ResultInteractionSchema)
def record_result_interaction(validated_data):
    """Record user interaction with search results."""
    try:
        current_user_id = int(get_jwt_identity())
        search_id = validated_data['search_id']
        document_id = validated_data['document_id']
        action = validated_data['action']
        
        # Verify search belongs to user
        search_record = SearchHistory.query.filter_by(
            id=search_id,
            user_id=current_user_id
        ).first()
        
        if not search_record:
            return jsonify({'error': 'Search record not found'}), 404
        
        # Verify document belongs to user
        document = Document.query.filter_by(
            id=document_id,
            user_id=current_user_id
        ).first()
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Record interaction
        if action == 'click':
            search_record.add_click(document_id)
        elif action == 'save':
            search_record.add_save(document_id)
        
        return jsonify({'message': 'Interaction recorded successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Record interaction error: {e}")
        return jsonify({'error': 'Failed to record interaction'}), 500


@bp.route('/analytics', methods=['GET'])
@jwt_required()
def get_search_analytics():
    """Get search analytics for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        days = request.args.get('days', 30, type=int)
        
        analytics = SearchHistory.get_search_analytics(current_user_id, days)
        
        return jsonify(analytics), 200
        
    except Exception as e:
        current_app.logger.error(f"Get search analytics error: {e}")
        return jsonify({'error': 'Failed to get search analytics'}), 500


def perform_direct_semantic_search(user_id, query, limit, filters=None):
    """
    Perform semantic search using sentence-transformers directly, without LangChain.
    This is a robust fallback when LangChain has compatibility issues.
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        get_logger().info(f"Starting direct semantic search for user {user_id} with query: {query}")
        
        # Initialize sentence transformer model with error handling
        model = None
        model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        
        try:
            # Try to initialize the model
            # Use a fallback cache folder if Flask context is not available
            try:
                cache_folder = current_app.config.get('EMBEDDINGS_MODEL_CACHE_FOLDER')
            except RuntimeError:
                cache_folder = str(Path(__file__).parent.parent.parent / 'data' / 'models')
            
            model = SentenceTransformer(model_name, cache_folder=cache_folder)
            get_logger().info(f"Direct semantic search model initialized: {model_name}")
        except Exception as model_error:
            get_logger().warning(f"Failed to initialize model {model_name}: {model_error}")
            
            # Try cached version
            try:
                try:
                    cache_folder = current_app.config.get('EMBEDDINGS_MODEL_CACHE_FOLDER')
                except RuntimeError:
                    cache_folder = str(Path(__file__).parent.parent.parent / 'data' / 'models')
                    
                model = SentenceTransformer(model_name, cache_folder=cache_folder)
                get_logger().info(f"Using cached model: {model_name}")
            except Exception as cache_error:
                get_logger().error(f"Failed to use cached model: {cache_error}")
                # If model can't be initialized, raise to trigger keyword search fallback
                raise Exception(f"SentenceTransformer model unavailable: {model_error}")
        
        if not model:
            raise Exception("SentenceTransformer model could not be initialized")
        
        # Get user's documents
        documents = Document.query.filter_by(user_id=user_id).all()
        
        if not documents:
            get_logger().info(f"No documents found for user {user_id}")
            return []
        
        get_logger().info(f"Found {len(documents)} documents for user {user_id}")
        
        # Prepare texts for embedding
        doc_texts = []
        doc_objects = []
        
        for doc in documents:
            # Combine title and content/summary for better search
            text_parts = [doc.title or '']
            if doc.summary:
                text_parts.append(doc.summary)
            elif doc.content_preview:
                text_parts.append(doc.content_preview)
            elif doc.content:
                # Use first 500 chars of content if no summary
                text_parts.append(doc.content[:500])
            
            text = ' '.join(text_parts).strip()
            if text:  # Only include documents with some text content
                doc_texts.append(text)
                doc_objects.append(doc)
        
        if not doc_texts:
            get_logger().info(f"No documents with text content found for user {user_id}")
            return []
        
        get_logger().info(f"Processing {len(doc_texts)} documents with text content")
        
        # Generate embeddings
        query_embedding = model.encode([query], normalize_embeddings=True)
        doc_embeddings = model.encode(doc_texts, normalize_embeddings=True)
        
        # Calculate cosine similarities
        similarities = np.dot(doc_embeddings, query_embedding.T).flatten()
        
        # Sort by similarity (descending)
        sorted_indices = np.argsort(similarities)[::-1]
        
        # Apply filters if provided
        filtered_results = []
        for idx in sorted_indices:
            doc = doc_objects[idx]
            similarity_score = similarities[idx]
            
            # Apply filters
            if filters:
                if filters.get('source_type') and doc.source_type != filters['source_type']:
                    continue
                if filters.get('date_from'):
                    date_from = datetime.fromisoformat(filters['date_from'])
                    if doc.published_date and doc.published_date < date_from:
                        continue
                if filters.get('date_to'):
                    date_to = datetime.fromisoformat(filters['date_to'])
                    if doc.published_date and doc.published_date > date_to:
                        continue
                if filters.get('tags'):
                    tag_names = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                    if not any(tag.name in tag_names for tag in doc.tags):
                        continue
            
            # Only include results with high semantic similarity (> 0.6)
            if similarity_score > 0.6:
                filtered_results.append((doc, similarity_score))
                get_logger().debug(f"Added document {doc.id} with similarity {similarity_score:.3f}")
            
            if len(filtered_results) >= limit:
                break
        
        # Sort by similarity score (descending - highest scores first)
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        
        get_logger().info(f"Direct semantic search returned {len(filtered_results)} results for user {user_id}")
        return filtered_results
        
    except ImportError as ie:
        get_logger().error(f"sentence-transformers not available: {ie}")
        raise
    except Exception as e:
        get_logger().error(f"Direct semantic search error: {e}")
        raise


def perform_keyword_search(user_id, query, limit, filters=None):
    """
    Perform keyword-based search on user's documents.
    This is a fallback when semantic search is not available.
    """
    try:
        get_logger().info(f"Starting keyword search for user {user_id} with query: {query}")
        
        # Try to use the document model's search method first
        try:
            documents = Document.search_documents(user_id, query, limit)
            get_logger().info(f"Document.search_documents returned {len(documents)} results")
        except Exception as search_error:
            get_logger().warning(f"Document.search_documents failed: {search_error}")
            # Fallback to simple text search
            documents = perform_simple_text_search(user_id, query, limit)
        
        # Apply additional filters if provided
        if filters:
            original_count = len(documents)
            if filters.get('source_type'):
                documents = [doc for doc in documents if doc.source_type == filters['source_type']]
            
            if filters.get('date_from'):
                date_from = datetime.fromisoformat(filters['date_from'])
                documents = [doc for doc in documents if doc.published_date and doc.published_date >= date_from]
            
            if filters.get('date_to'):
                date_to = datetime.fromisoformat(filters['date_to'])
                documents = [doc for doc in documents if doc.published_date and doc.published_date <= date_to]
            
            if filters.get('tags'):
                tag_names = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                documents = [doc for doc in documents 
                           if any(tag.name in tag_names for tag in doc.tags)]
            
            get_logger().info(f"Filters reduced results from {original_count} to {len(documents)}")
        
        final_results = documents[:limit]
        get_logger().info(f"Keyword search returning {len(final_results)} results")
        return final_results
        
    except Exception as e:
        get_logger().error(f"Keyword search error: {e}")
        # Final fallback - return empty results rather than crashing
        return []


def perform_simple_text_search(user_id, query, limit, filters=None):
    """
    Perform simple text-based search without any external dependencies.
    This is the most basic fallback when everything else fails.
    """
    try:
        get_logger().info(f"Starting simple text search for user {user_id}")
        
        # Get all user documents
        documents = Document.query.filter_by(user_id=user_id).all()
        
        if not documents:
            return []
        
        # Simple text matching
        query_words = set(query.lower().split())
        scored_docs = []
        
        for doc in documents:
            score = 0
            
            # Check title
            if doc.title:
                title_words = set(doc.title.lower().split())
                score += len(query_words.intersection(title_words)) * 3  # Title matches weighted higher
            
            # Check summary
            if doc.summary:
                summary_words = set(doc.summary.lower().split())
                score += len(query_words.intersection(summary_words)) * 2
            
            # Check content preview
            if doc.content_preview:
                content_words = set(doc.content_preview.lower().split())
                score += len(query_words.intersection(content_words))
            
            # Check tags
            if doc.tags:
                for tag in doc.tags:
                    if any(word in tag.name.lower() for word in query_words):
                        score += 2
            
            if score > 0:
                scored_docs.append((doc, score))
        
        # Sort by score (descending)
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Extract documents
        results = [doc for doc, score in scored_docs[:limit]]
        
        get_logger().info(f"Simple text search found {len(results)} results")
        return results
        
    except Exception as e:
        get_logger().error(f"Simple text search error: {e}")
        return []


def perform_external_search_streaming(query, limit=3):
    """
    Perform external search with streaming progress updates.
    Generator function that yields progress updates and returns results.
    """
    try:
        from flask import current_app
        import requests
        from app.ai.langchain_service import LangChainService
        
        # Emit initial progress
        yield {
            'status': 'progress',
            'message': 'Starting external search...',
            'progress': 82,
            'external_search': True,
            'results': None
        }
        
        # Get Google Search API configuration with fallback
        try:
            api_key = current_app.config.get('GOOGLE_SEARCH_API_KEY')
            engine_id = current_app.config.get('GOOGLE_SEARCH_ENGINE_ID')
        except RuntimeError:
            # Fallback values if outside Flask context
            api_key = ''
            engine_id = ''
        
        # Emit Google API call progress
        yield {
            'status': 'progress',
            'message': 'Calling Google Search API...',
            'progress': 84,
            'external_search': True,
            'results': None
        }
        
        # Perform Google Custom Search API request
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': engine_id,
            'q': query,
            'num': min(limit, 5)  # Google API supports max 10 results per request
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        external_results = []
        
        # Process search results
        items = data.get('items', [])[:limit]
        
        if items:
            # Emit AI service initialization progress
            yield {
                'status': 'progress',
                'message': f'Found {len(items)} external results, initializing AI summarization...',
                'progress': 86,
                'external_search': True,
                'results': None
            }
            
            # Initialize AI service for LLM inference
            try:
                from app.ai.langchain_service import LangChainService
                
                # Initialize with config (with fallbacks for streaming context)
                try:
                    config = {
                        'EMBEDDINGS_MODEL': current_app.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
                        'VECTOR_STORE_PATH': current_app.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
                        'LLM_MODEL': current_app.config.get('LLM_MODEL', 'qwen3:4b'),
                        'OLLAMA_BASE_URL': current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
                        'RERANKER_MODEL': current_app.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                    }
                except RuntimeError:
                    # Fallback config if outside Flask context
                    config = {
                        'EMBEDDINGS_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
                        'VECTOR_STORE_PATH': str(Path(__file__).parent.parent.parent / 'data' / 'vector_stores'),
                        'LLM_MODEL': 'qwen3:4b',
                        'OLLAMA_BASE_URL': 'http://localhost:11434',
                        'RERANKER_MODEL': 'cross-encoder/ms-marco-MiniLM-L-6-v2'
                    }
                
                ai_service = LangChainService(config=config)
                
                yield {
                    'status': 'progress',
                    'message': 'AI service initialized, generating summaries...',
                    'progress': 87,
                    'external_search': True,
                    'results': None
                }
                
            except Exception as e:
                current_app.logger.error(f"Failed to initialize LangChain service for external search: {e}")
                ai_service = None
                
                yield {
                    'status': 'progress',
                    'message': 'AI service unavailable, using simple summaries...',
                    'progress': 87,
                    'external_search': True,
                    'results': None
                }
            
            for i, item in enumerate(items):
                title = item.get('title', '')
                url = item.get('link', '')
                snippet = item.get('snippet', '')
                
                # Emit progress for each result processing
                progress_percent = 87 + ((i + 1) / len(items)) * 3  # 87% to 90%
                yield {
                    'status': 'progress',
                    'message': f'Processing external result {i + 1}/{len(items)}: {title[:50]}...',
                    'progress': int(progress_percent),
                    'external_search': True,
                    'results': None
                }
                
                # Create basic result
                result = {
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'source': 'google_search',
                    'type': 'web_search'
                }
                
                # Generate AI summary using LLM inference with streaming
                try:
                    if ai_service and ai_service.llm:
                        # Combine title and snippet for LLM processing
                        content_to_analyze = f"Title: {title}\n\nContent: {snippet}"
                        
                        # Use streaming LLM to generate enhanced summary
                        ai_summary = ""
                        summary_completed = False
                        
                        for summary_progress in ai_service.generate_summary_stream(
                            content_to_analyze, 
                            max_length=150
                        ):
                            status = summary_progress.get('status')
                            partial_text = summary_progress.get('partial_text', '')
                            
                            # Emit streaming progress for this external result
                            stream_progress = 87 + ((i + 1) / len(items)) * 3  # Base progress + streaming within result
                            
                            if status == 'starting':
                                yield {
                                    'status': 'progress',
                                    'message': f'Starting AI summary for result {i + 1}/{len(items)}: {title[:30]}...',
                                    'progress': int(stream_progress),
                                    'external_search': True,
                                    'streaming_summary': True,
                                    'result_index': i,
                                    'partial_summary': '',
                                    'results': None
                                }
                            elif status == 'streaming':
                                yield {
                                    'status': 'progress',
                                    'message': f'Generating AI summary for result {i + 1}/{len(items)}...',
                                    'progress': int(stream_progress),
                                    'external_search': True,
                                    'streaming_summary': True,
                                    'result_index': i,
                                    'partial_summary': partial_text,
                                    'results': None
                                }
                            elif status == 'completed':
                                ai_summary = summary_progress.get('final_summary', partial_text)
                                summary_completed = True
                                yield {
                                    'status': 'progress',
                                    'message': f'AI summary completed for result {i + 1}/{len(items)}: {title[:30]}...',
                                    'progress': int(stream_progress + 1),
                                    'external_search': True,
                                    'streaming_summary': True,
                                    'result_index': i,
                                    'partial_summary': ai_summary,
                                    'summary_completed': True,
                                    'results': None
                                }
                                break
                            elif status == 'error':
                                current_app.logger.error(f"Streaming summary error: {summary_progress.get('error', 'Unknown error')}")
                                ai_summary = generate_simple_summary(snippet, query, max_length=150)
                                summary_completed = True
                                yield {
                                    'status': 'progress',
                                    'message': f'AI summary failed, using fallback for result {i + 1}/{len(items)}',
                                    'progress': int(stream_progress),
                                    'external_search': True,
                                    'streaming_summary': True,
                                    'result_index': i,
                                    'partial_summary': ai_summary,
                                    'summary_completed': True,
                                    'results': None
                                }
                                break
                        
                        if summary_completed and ai_summary:
                            result['ai_summary'] = ai_summary
                            result['enhanced'] = True
                        else:
                            result['ai_summary'] = snippet[:150] + '...' if len(snippet) > 150 else snippet
                            result['enhanced'] = False
                    else:
                        # Fall back to simple summary
                        result['ai_summary'] = generate_simple_summary(snippet, query, max_length=150)
                        result['enhanced'] = False
                        
                        # Emit progress for non-AI summary
                        stream_progress = 87 + ((i + 1) / len(items)) * 3
                        yield {
                            'status': 'progress',
                            'message': f'Generated simple summary for result {i + 1}/{len(items)}: {title[:30]}...',
                            'progress': int(stream_progress),
                            'external_search': True,
                            'streaming_summary': False,
                            'result_index': i,
                            'results': None
                        }
                        
                except Exception as e:
                    current_app.logger.error(f"LLM inference error for external result: {e}")
                    # Fall back to simple summary
                    result['ai_summary'] = generate_simple_summary(snippet, query, max_length=150)
                    result['enhanced'] = False
                    
                    # Emit error progress
                    stream_progress = 87 + ((i + 1) / len(items)) * 3
                    yield {
                        'status': 'progress',
                        'message': f'Summary generation failed, using fallback for result {i + 1}/{len(items)}',
                        'progress': int(stream_progress),
                        'external_search': True,
                        'streaming_summary': False,
                        'result_index': i,
                        'error': str(e)[:50],
                        'results': None
                    }
                
                external_results.append(result)
        else:
            yield {
                'status': 'progress',
                'message': 'No external results found',
                'progress': 90,
                'external_search': True,
                'results': None
            }
        
        current_app.logger.info(f"External search returned {len(external_results)} results for query: {query}")
        
        # Yield final results
        yield {
            'status': 'progress',
            'message': f'External search completed: {len(external_results)} results found',
            'progress': 90,
            'external_search': True,
            'results': external_results
        }
        
    except requests.RequestException as e:
        current_app.logger.error(f"Google Search API request error: {e}")
        yield {
            'status': 'warning',
            'message': f'External search failed: Google API error',
            'progress': 90,
            'external_search': True,
            'results': []
        }
    except Exception as e:
        current_app.logger.error(f"External search error: {e}")
        yield {
            'status': 'warning',
            'message': f'External search failed: {str(e)[:50]}...',
            'progress': 90,
            'external_search': True,
            'results': []
        }


def perform_external_search(query, limit=3):
    """
    Perform external search using Google Search API.
    Returns top results when knowledge base doesn't have enough content.
    (Non-streaming version for compatibility)
    """
    # Consume the streaming generator and return final results
    external_results = []
    for progress_data in perform_external_search_streaming(query, limit):
        if progress_data.get('results') is not None:
            external_results = progress_data.get('results', [])
    return external_results


def generate_simple_summary(text, query, max_length=150):
    """
    Generate a simple enhanced summary without LLM dependency.
    This focuses on content most relevant to the query.
    """
    try:
        import re
        
        # Clean the text
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # If text is short enough, return as is
        if len(cleaned_text) <= max_length:
            return cleaned_text
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', cleaned_text)
        
        # Score sentences based on query word overlap
        query_words = set(query.lower().split())
        scored_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
                
            sentence_words = set(sentence.lower().split())
            overlap_score = len(query_words.intersection(sentence_words))
            scored_sentences.append((sentence, overlap_score))
        
        # Sort by relevance score (descending)
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Build summary with most relevant sentences
        summary_parts = []
        current_length = 0
        
        for sentence, score in scored_sentences:
            if current_length + len(sentence) + 2 <= max_length:
                summary_parts.append(sentence)
                current_length += len(sentence) + 2  # +2 for '. '
            else:
                # Try to fit a partial sentence
                remaining_space = max_length - current_length - 3  # -3 for '...'
                if remaining_space > 20:  # Only if we have reasonable space
                    partial = sentence[:remaining_space].rsplit(' ', 1)[0]  # Cut at word boundary
                    summary_parts.append(partial + '...')
                break
        
        if not summary_parts:
            # Fallback: just truncate the original text
            return cleaned_text[:max_length-3] + '...'
        
        return '. '.join(summary_parts) if len(summary_parts) > 1 else summary_parts[0]
        
    except Exception as e:
        get_logger().error(f"Simple summary generation error: {e}")
        # Fallback to simple truncation
        return text[:max_length-3] + '...' if len(text) > max_length else text
