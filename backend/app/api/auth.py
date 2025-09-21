"""
Authentication API endpoints for user registration, login, and profile management.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from marshmallow import Schema, fields, validate, ValidationError
from werkzeug.exceptions import BadRequest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import User
from app.utils.validators import validate_password_strength
from app.utils.decorators import validate_json

bp = Blueprint('auth', __name__)

# Validation Schemas
class UserRegistrationSchema(Schema):
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error='Username can only contain letters, numbers, hyphens and underscores')
        ]
    )
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    first_name = fields.Str(validate=validate.Length(max=50))
    last_name = fields.Str(validate=validate.Length(max=50))


class UserLoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    rememberMe = fields.Bool(missing=False)  # Optional field with default False


class UserProfileUpdateSchema(Schema):
    first_name = fields.Str(validate=validate.Length(max=50))
    last_name = fields.Str(validate=validate.Length(max=50))
    bio = fields.Str(validate=validate.Length(max=500))
    notification_preferences = fields.Dict()


class PasswordChangeSchema(Schema):
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8))


# JWT blacklist (in production, use Redis)
blacklisted_tokens = set()


@bp.route('/register', methods=['POST'])
@validate_json(UserRegistrationSchema)
def register(validated_data):
    """Register a new user."""
    try:
        # Validate password strength
        is_strong, message = validate_password_strength(validated_data['password'])
        if not is_strong:
            return jsonify({'error': message}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=validated_data['username']).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        if User.query.filter_by(email=validated_data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create new user
        user = User.create_user(**validated_data)
        
        # Generate tokens
        tokens = user.generate_tokens()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(include_sensitive=True),
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token']
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'User already exists'}), 409
    except Exception as e:
        current_app.logger.error(f"Registration error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500


@bp.route('/login', methods=['POST'])
@validate_json(UserLoginSchema)
def login(validated_data):
    """User login endpoint."""
    try:
        # Find user by username or email
        user = User.query.filter(
            db.or_(
                User.username == validated_data['username'],
                User.email == validated_data['username']
            )
        ).first()
        
        if not user or not user.check_password(validated_data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 401
        
        # Update last login
        user.update_last_login()
        
        # Generate tokens with remember me option
        remember_me = validated_data.get('rememberMe', False)
        tokens = user.generate_tokens(remember_me=remember_me)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(include_sensitive=True),
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token']
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint."""
    try:
        # Get current token
        token = get_jwt()
        jti = token['jti']  # JWT ID
        
        # Add token to blacklist (in production, use Redis with expiration)
        blacklisted_tokens.add(jti)
        
        return jsonify({'message': 'Successfully logged out'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    try:
        current_user_id = int(get_jwt_identity())
        current_app.logger.info(f"Token refresh attempt for user ID: {current_user_id}")
        
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            current_app.logger.warning(f"Token refresh failed - User not found or inactive: {current_user_id}")
            return jsonify({'error': 'User not found or inactive'}), 404
        
        # Check if refresh token is blacklisted
        current_token = get_jwt()
        if current_token['jti'] in blacklisted_tokens:
            current_app.logger.warning(f"Token refresh failed - Token blacklisted: {current_token['jti'][:20]}...")
            return jsonify({'error': 'Token has been revoked'}), 401
        
        # Create new access token with same expiration logic as login
        additional_claims = {
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active
        }
        
        # Use default access token expiration (1 hour)
        new_token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims
        )
        
        current_app.logger.info(f"Token refresh successful for user: {user.username}")
        return jsonify({
            'access_token': new_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500


@bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if the current access token is valid."""
    try:
        current_user_id = int(get_jwt_identity())
        current_app.logger.info(f"Token verification attempt for user ID: {current_user_id}")
        
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            current_app.logger.warning(f"Token verification failed - User not found or inactive: {current_user_id}")
            return jsonify({'error': 'User not found or inactive'}), 404
        
        current_app.logger.info(f"Token verification successful for user: {user.username}")
        return jsonify({
            'valid': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token verification error: {e}")
        return jsonify({'error': 'Token verification failed'}), 500


@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user statistics
        stats = user.get_stats()
        
        return jsonify({
            'user': user.to_dict(include_sensitive=True),
            'stats': stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500


@bp.route('/profile', methods=['PUT'])
@jwt_required()
@validate_json(UserProfileUpdateSchema)
def update_profile(validated_data):
    """Update user profile."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update profile
        user.update_profile(**validated_data)
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Profile update error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Profile update failed'}), 500


@bp.route('/change-password', methods=['POST'])
@jwt_required()
@validate_json(PasswordChangeSchema)
def change_password(validated_data):
    """Change user password."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not user.check_password(validated_data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Validate new password strength
        is_strong, message = validate_password_strength(validated_data['new_password'])
        if not is_strong:
            return jsonify({'error': message}), 400
        
        # Update password
        user.set_password(validated_data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Password change error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Password change failed'}), 500


@bp.route('/activity', methods=['GET'])
@jwt_required()
def get_user_activity():
    """Get user's recent activity."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50
        
        activity = user.get_recent_activity(limit=limit)
        
        return jsonify({
            'activity': activity,
            'count': len(activity)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get activity error: {e}")
        return jsonify({'error': 'Failed to get activity'}), 500


# JWT token blacklist checker - moved to app initialization to avoid context issues
def check_if_token_revoked(jwt_header, jwt_payload):
    """Check if token is in blacklist."""
    jti = jwt_payload['jti']
    return jti in blacklisted_tokens


# Error handlers for JWT
@bp.errorhandler(ValidationError)
def handle_validation_error(e):
    """Handle marshmallow validation errors."""
    return jsonify({'error': 'Validation failed', 'details': e.messages}), 400


@bp.errorhandler(BadRequest)
def handle_bad_request(e):
    """Handle bad request errors."""
    return jsonify({'error': 'Bad request', 'message': str(e)}), 400
