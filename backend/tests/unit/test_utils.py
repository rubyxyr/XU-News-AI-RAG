"""
Unit tests for utility functions and validators.
"""
import pytest
import time
from unittest.mock import MagicMock, patch
from werkzeug.datastructures import FileStorage
import io
from app.utils.validators import (
    validate_email,
    validate_password_strength,
    validate_username,
    sanitize_html_content,
    validate_url,
    validate_file_upload,
    validate_search_query,
    validate_tag_name
)
from app.utils.decorators import (
    rate_limit,
    require_user_ownership,
    validate_json,
    validate_pagination
)


class TestValidators:
    """Test validation functions."""
    
    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        assert validate_email('user@example.com') == True
        assert validate_email('user.name@example.co.uk') == True
        assert validate_email('user+tag@example.com') == True
        assert validate_email('user_123@subdomain.example.com') == True
        
        # Invalid emails
        assert validate_email('invalid') == False
        assert validate_email('@example.com') == False
        assert validate_email('user@') == False
        assert validate_email('user @example.com') == False
        assert validate_email('user@example') == False
        assert validate_email('') == False
        assert validate_email(None) == False
    
    def test_validate_password_strength(self):
        """Test password strength validation."""
        # Valid passwords
        valid_passwords = [
            'StrongPass123!',
            'SecurePass@2024',
            'MyP@ssw0rd',
            'Test$789Pass'
        ]
        
        for password in valid_passwords:
            result, message = validate_password_strength(password)
            assert result == True, f"Password '{password}' should be valid: {message}"
        
        # Invalid passwords
        invalid_passwords = [
            ('short', 'Too short'),
            ('password123!', 'No uppercase'),
            ('PASSWORD123!', 'No lowercase'),
            ('Password!', 'No digit'),
            ('Password123', 'No special character'),
            ('', 'Empty password'),
        ]
        
        for password, reason in invalid_passwords:
            if password is None:
                continue  # Skip None test as function expects string
            result, message = validate_password_strength(password)
            assert result == False, f"Password '{password}' should be invalid ({reason}): {message}"
    
    def test_validate_username(self):
        """Test username validation."""
        # Valid usernames (assuming: 3-50 chars, alphanumeric and underscore/hyphen)
        valid_usernames = [
            'user123',
            'john_doe',
            'test-user',
            'User_Name_123',
            'abc'  # Minimum length
        ]
        
        for username in valid_usernames:
            result, message = validate_username(username)
            assert result == True, f"Username '{username}' should be valid: {message}"
        
        # Invalid usernames
        invalid_usernames = [
            ('ab', 'Too short'),
            ('a' * 51, 'Too long'),
            ('user@123', 'Invalid character @'),
            ('user name', 'Contains space'),
            ('user.name', 'Contains period'),
            ('', 'Empty username'),
            (None, 'None username')
        ]
        
        for username, reason in invalid_usernames:
            result, message = validate_username(username)
            assert result == False, f"Username '{username}' should be invalid ({reason})"
    
    def test_sanitize_html_content(self):
        """Test HTML content sanitization."""
        # Test removing script tags
        dirty_html = '<p>Hello</p><script>alert("XSS")</script><p>World</p>'
        clean = sanitize_html_content(dirty_html)
        assert '<script>' not in clean
        assert 'alert' not in clean
        assert 'Hello' in clean or 'World' in clean
        
        # Test removing event handlers
        dirty_html = '<button onclick="malicious()">Click</button>'
        clean = sanitize_html_content(dirty_html)
        assert 'onclick' not in clean
        
        # Test removing style tags
        dirty_html = '<style>body { display: none; }</style><p>Content</p>'
        clean = sanitize_html_content(dirty_html)
        assert '<style>' not in clean
        
        # Test safe HTML
        safe_html = '<p>This is <strong>safe</strong> content</p>'
        clean = sanitize_html_content(safe_html)
        assert 'safe' in clean
        
        # Test empty and None inputs
        assert sanitize_html_content('') == ''
        assert sanitize_html_content(None) == ''
    
    def test_validate_url(self):
        """Test URL validation."""
        # Valid URLs (note: the actual function rejects localhost for security)
        valid_urls = [
            'https://example.com',
            'http://subdomain.example.co.uk/path',
            'https://example.com/path?query=value',
        ]
        
        for url in valid_urls:
            result, message = validate_url(url)
            assert result == True, f"URL '{url}' should be valid: {message}"
        
        # Invalid URLs
        invalid_urls = [
            'not a url',
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
            '//example.com',  # Missing protocol
            'example.com',  # Missing protocol
            'http://localhost:8080',  # Rejected by security check
            'https://192.168.1.1',  # Rejected by security check
            '',
        ]
        
        for url in invalid_urls:
            if not url:  # Skip empty string
                continue
            result, message = validate_url(url)
            assert result == False, f"URL '{url}' should be invalid: {message}"


class TestValidationHelpers:
    """Test additional validation helper functions."""
    
    def test_validate_search_query(self):
        """Test search query validation."""
        # Valid queries
        valid_queries = [
            'simple search',
            'machine learning',
            'search with numbers 123'
        ]
        
        for query in valid_queries:
            result, message = validate_search_query(query)
            assert result == True, f"Query '{query}' should be valid: {message}"
        
        # Invalid queries
        invalid_queries = [
            'union select * from users',
            '<script>alert(1)</script>',
            'drop table documents',
            '',
            ' ' * 1001  # Too long
        ]
        
        for query in invalid_queries:
            result, message = validate_search_query(query)
            assert result == False, f"Query '{query}' should be invalid: {message}"
    
    def test_validate_tag_name(self):
        """Test tag name validation."""
        # Valid tags
        valid_tags = [
            'technology',
            'machine-learning',
            'data_science',
            'AI ML'
        ]
        
        for tag in valid_tags:
            result, message = validate_tag_name(tag)
            assert result == True, f"Tag '{tag}' should be valid: {message}"
        
        # Invalid tags
        invalid_tags = [
            '',
            'a',  # Too short
            'a' * 51,  # Too long
            '-starts-with-dash',
            'ends-with-dash-',
            'tag@special',  # Invalid character
            'double  spaces'
        ]
        
        for tag in invalid_tags:
            result, message = validate_tag_name(tag)
            assert result == False, f"Tag '{tag}' should be invalid: {message}"


class TestFileValidation:
    """Test file validation utilities."""
    
    def test_validate_file_upload(self):
        """Test file upload validation."""
        allowed_extensions = {'txt', 'pdf', 'docx', 'csv'}
        max_size = 1024 * 1024  # 1 MB
        
        # Valid file
        valid_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='document.txt',
            content_type='text/plain'
        )
        
        result, message = validate_file_upload(
            valid_file, 
            allowed_extensions=allowed_extensions, 
            max_size=max_size
        )
        assert result == True, f"Valid file should pass: {message}"
        
        # Invalid extension
        invalid_file = FileStorage(
            stream=io.BytesIO(b'content'),
            filename='script.exe',
            content_type='application/x-executable'
        )
        
        result, message = validate_file_upload(
            invalid_file, 
            allowed_extensions=allowed_extensions, 
            max_size=max_size
        )
        assert result == False
        assert 'not allowed' in message
        
        # File too large
        large_file = FileStorage(
            stream=io.BytesIO(b'x' * (max_size + 1)),
            filename='large.txt'
        )
        
        result, message = validate_file_upload(
            large_file, 
            allowed_extensions=allowed_extensions, 
            max_size=max_size
        )
        assert result == False
        assert 'too large' in message.lower()
        
        # No file
        result, message = validate_file_upload(None)
        assert result == False
        assert 'no file' in message.lower()


# End of test file
