"""
Decorators for request validation, authentication, and other common functionality.
"""
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from marshmallow import ValidationError
import json

from app.models.user import User


def validate_json(schema_class):
    """
    Decorator to validate JSON request data against a Marshmallow schema.
    
    Args:
        schema_class: Marshmallow schema class for validation
        
    Returns:
        Decorated function that receives validated_data as parameter
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check content type
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            try:
                # Get JSON data
                json_data = request.get_json()
                if json_data is None:
                    return jsonify({'error': 'Invalid JSON or empty request body'}), 400
                
                # Validate data
                schema = schema_class()
                validated_data = schema.load(json_data)
                
                # Call original function with validated data
                return f(validated_data, *args, **kwargs)
                
            except ValidationError as e:
                return jsonify({
                    'error': 'Validation failed',
                    'details': e.messages
                }), 400
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON format'}), 400
            except Exception as e:
                current_app.logger.error(f"JSON validation error: {e}")
                return jsonify({'error': 'Request validation failed'}), 400
        
        return decorated_function
    return decorator


def require_user_ownership(model_class, id_param='id'):
    """
    Decorator to ensure the current user owns the requested resource.
    
    Args:
        model_class: SQLAlchemy model class to check
        id_param: Parameter name containing the resource ID
        
    Returns:
        Decorated function with ownership verification
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verify JWT token
                verify_jwt_in_request()
                current_user_id = int(get_jwt_identity())
                
                # Get resource ID from URL parameters
                resource_id = kwargs.get(id_param)
                if not resource_id:
                    return jsonify({'error': 'Resource ID not provided'}), 400
                
                # Check if resource exists and belongs to user
                resource = model_class.query.get(resource_id)
                if not resource:
                    return jsonify({'error': 'Resource not found'}), 404
                
                if hasattr(resource, 'user_id') and resource.user_id != current_user_id:
                    return jsonify({'error': 'Access denied'}), 403
                
                # Add resource to kwargs for easy access
                kwargs['resource'] = resource
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Ownership check error: {e}")
                return jsonify({'error': 'Access verification failed'}), 500
        
        return decorated_function
    return decorator


def validate_pagination():
    """
    Decorator to validate and process pagination parameters.
    
    Returns:
        Decorated function that receives pagination parameters
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get pagination parameters
                page = request.args.get('page', 1, type=int)
                per_page = request.args.get('per_page', current_app.config.get('ITEMS_PER_PAGE', 20), type=int)
                
                # Validate pagination parameters
                if page < 1:
                    return jsonify({'error': 'Page must be >= 1'}), 400
                
                if per_page < 1:
                    return jsonify({'error': 'Items per page must be >= 1'}), 400
                
                max_per_page = current_app.config.get('MAX_ITEMS_PER_PAGE', 100)
                if per_page > max_per_page:
                    return jsonify({'error': f'Items per page must be <= {max_per_page}'}), 400
                
                # Add pagination to kwargs
                kwargs['page'] = page
                kwargs['per_page'] = per_page
                
                return f(*args, **kwargs)
                
            except ValueError:
                return jsonify({'error': 'Invalid pagination parameters'}), 400
            except Exception as e:
                current_app.logger.error(f"Pagination validation error: {e}")
                return jsonify({'error': 'Pagination validation failed'}), 400
        
        return decorated_function
    return decorator


def rate_limit(requests_per_minute=60):
    """
    Simple in-memory rate limiting decorator.
    In production, use Redis-based rate limiting.
    
    Args:
        requests_per_minute: Maximum requests per minute per user
        
    Returns:
        Decorated function with rate limiting
    """
    # In-memory storage (use Redis in production)
    rate_limit_storage = {}
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get user identifier
                user_id = None
                try:
                    verify_jwt_in_request(optional=True)
                    user_id = int(get_jwt_identity())
                except:
                    pass
                
                # Use IP address if no user ID
                identifier = user_id or request.remote_addr
                
                # Check rate limit
                import time
                current_time = time.time()
                minute_window = int(current_time // 60)
                
                key = f"{identifier}:{minute_window}"
                
                if key in rate_limit_storage:
                    if rate_limit_storage[key] >= requests_per_minute:
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'retry_after': 60 - (current_time % 60)
                        }), 429
                    rate_limit_storage[key] += 1
                else:
                    rate_limit_storage[key] = 1
                
                # Clean up old entries (simple cleanup)
                if len(rate_limit_storage) > 10000:  # Prevent memory bloat
                    old_keys = [k for k in rate_limit_storage.keys() 
                               if int(k.split(':')[1]) < minute_window - 5]
                    for old_key in old_keys:
                        rate_limit_storage.pop(old_key, None)
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Rate limiting error: {e}")
                return f(*args, **kwargs)  # Continue on rate limit error
        
        return decorated_function
    return decorator


def require_admin():
    """
    Decorator to require admin privileges.
    
    Returns:
        Decorated function with admin check
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                current_user_id = int(get_jwt_identity())
                
                user = User.query.get(current_user_id)
                if not user or not getattr(user, 'is_admin', False):
                    return jsonify({'error': 'Admin access required'}), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Admin check error: {e}")
                return jsonify({'error': 'Admin verification failed'}), 500
        
        return decorated_function
    return decorator


def log_api_call():
    """
    Decorator to log API calls for monitoring and debugging.
    
    Returns:
        Decorated function with API call logging
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                # Get user information if available
                user_id = None
                try:
                    verify_jwt_in_request(optional=True)
                    user_id = int(get_jwt_identity())
                except:
                    pass
                
                # Log request
                current_app.logger.info(
                    f"API Call: {request.method} {request.path} "
                    f"User: {user_id or 'anonymous'} "
                    f"IP: {request.remote_addr}"
                )
                
                # Execute function
                result = f(*args, **kwargs)
                
                # Log response
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # milliseconds
                
                status_code = result[1] if isinstance(result, tuple) else 200
                current_app.logger.info(
                    f"API Response: {request.method} {request.path} "
                    f"Status: {status_code} "
                    f"Time: {response_time:.2f}ms"
                )
                
                return result
                
            except Exception as e:
                # Log error
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                current_app.logger.error(
                    f"API Error: {request.method} {request.path} "
                    f"Error: {str(e)} "
                    f"Time: {response_time:.2f}ms"
                )
                raise
        
        return decorated_function
    return decorator


def handle_exceptions():
    """
    Decorator to handle exceptions gracefully and return consistent error responses.
    
    Returns:
        Decorated function with exception handling
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ValidationError as e:
                return jsonify({
                    'error': 'Validation failed',
                    'details': e.messages
                }), 400
            except PermissionError:
                return jsonify({'error': 'Permission denied'}), 403
            except FileNotFoundError:
                return jsonify({'error': 'Resource not found'}), 404
            except ValueError as e:
                return jsonify({'error': f'Invalid value: {str(e)}'}), 400
            except Exception as e:
                current_app.logger.error(f"Unhandled exception in {f.__name__}: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        return decorated_function
    return decorator


def require_content_type(content_type='application/json'):
    """
    Decorator to require specific content type.
    
    Args:
        content_type: Required content type
        
    Returns:
        Decorated function with content type check
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.content_type != content_type:
                return jsonify({
                    'error': f'Content-Type must be {content_type}'
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
