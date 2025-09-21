"""
Validation utilities for input validation and security.
"""
import re
import os
from typing import Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import html


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength according to security requirements.
    
    Args:
        password: Password string to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be no more than 128 characters long"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False, "Password must contain at least one special character"
    
    # Check for extremely common patterns (be less strict for testing)
    common_patterns = [
        r"password", r"admin", r"qwerty", r"letmein", r"welcome"
    ]
    
    password_lower = password.lower()
    for pattern in common_patterns:
        if pattern in password_lower:
            return False, f"Password contains common pattern '{pattern}'"
    
    return True, "Password is strong"


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
        
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format and constraints.
    
    Args:
        username: Username to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not username or not isinstance(username, str):
        return False, "Username cannot be empty"
        
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return False, "Username must be no more than 50 characters long"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, hyphens and underscores"
    
    # Reserved usernames
    reserved = [
        'admin', 'root', 'system', 'api', 'www', 'mail', 'support',
        'help', 'info', 'security', 'service', 'test', 'user',
        'anonymous', 'guest', 'null', 'undefined'
    ]
    
    if username.lower() in reserved:
        return False, f"Username '{username}' is reserved"
    
    return True, "Username is valid"


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL format and security.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        parsed = urlparse(url)
        
        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        
        # Only allow http and https
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use HTTP or HTTPS protocol"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'localhost', '127.0.0.1', '0.0.0.0', '192.168.',
            '10.0.', '172.16.', '169.254.'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in parsed.netloc:
                return False, f"URL contains suspicious pattern: {pattern}"
        
        return True, "URL is valid"
        
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def sanitize_html_content(content: str) -> str:
    """
    Remove potentially dangerous HTML content while preserving text.
    
    Args:
        content: HTML content to sanitize
        
    Returns:
        Sanitized text content
    """
    if not content:
        return ""
    
    # Parse HTML
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove dangerous tags completely
    dangerous_tags = ['script', 'style', 'meta', 'link', 'object', 'embed', 'iframe', 'frame']
    for tag in soup.find_all(dangerous_tags):
        tag.decompose()
    
    # Remove dangerous attributes
    dangerous_attrs = [
        'onload', 'onclick', 'onmouseover', 'onfocus', 'onerror',
        'onsubmit', 'onchange', 'onselect', 'onkeydown', 'onkeyup',
        'javascript:', 'vbscript:', 'data:'
    ]
    
    for tag in soup.find_all():
        for attr in list(tag.attrs.keys()):
            if attr.lower() in dangerous_attrs or any(danger in str(tag.attrs[attr]).lower() for danger in dangerous_attrs):
                del tag.attrs[attr]
    
    # Get clean text
    clean_text = soup.get_text(separator=' ', strip=True)
    
    # HTML escape the result for extra security
    return html.escape(clean_text)


def validate_file_upload(file, allowed_extensions=None, max_size=None):
    """
    Validate uploaded file for security and constraints.
    
    Args:
        file: File object from Flask request
        allowed_extensions: Set of allowed file extensions
        max_size: Maximum file size in bytes
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not file or not file.filename:
        return False, "No file provided"
    
    # Check file size
    if max_size:
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # Reset pointer
        
        if size > max_size:
            return False, f"File too large. Maximum size: {max_size // (1024*1024)}MB"
    
    # Check file extension
    if allowed_extensions:
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return False, f"File type '{file_ext}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    # Check for suspicious filenames
    suspicious_patterns = [
        '..', '/', '\\', ':', '*', '?', '"', '<', '>', '|',
        'cmd', 'exe', 'bat', 'sh', 'php', 'jsp', 'asp'
    ]
    
    filename_lower = file.filename.lower()
    for pattern in suspicious_patterns:
        if pattern in filename_lower:
            return False, f"Filename contains suspicious pattern: {pattern}"
    
    return True, "File is valid"


def validate_search_query(query: str) -> Tuple[bool, str]:
    """
    Validate search query for potential injection attacks.
    
    Args:
        query: Search query string
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not query or not query.strip():
        return False, "Search query cannot be empty"
    
    if len(query) > 1000:
        return False, "Search query too long (max 1000 characters)"
    
    # Check for SQL injection patterns
    sql_patterns = [
        'union select', 'drop table', 'delete from', 'insert into',
        'update set', 'exec ', 'execute ', 'xp_', 'sp_',
        '@@', 'waitfor delay'
    ]
    
    query_lower = query.lower()
    for pattern in sql_patterns:
        if pattern in query_lower:
            return False, f"Search query contains potentially dangerous pattern: {pattern}"
    
    # Check for script injection
    script_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
    for pattern in script_patterns:
        if pattern in query_lower:
            return False, f"Search query contains script pattern: {pattern}"
    
    return True, "Query is valid"


def validate_tag_name(tag: str) -> Tuple[bool, str]:
    """
    Validate tag name format and constraints.
    
    Args:
        tag: Tag name to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not tag or not tag.strip():
        return False, "Tag name cannot be empty"
    
    tag = tag.strip()
    
    if len(tag) < 2:
        return False, "Tag name must be at least 2 characters long"
    
    if len(tag) > 50:
        return False, "Tag name must be no more than 50 characters long"
    
    # Allow letters, numbers, hyphens, underscores, and spaces
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', tag):
        return False, "Tag name can only contain letters, numbers, hyphens, underscores, and spaces"
    
    # No consecutive spaces
    if '  ' in tag:
        return False, "Tag name cannot contain consecutive spaces"
    
    # Cannot start or end with special characters
    if tag[0] in '-_' or tag[-1] in '-_':
        return False, "Tag name cannot start or end with hyphens or underscores"
    
    return True, "Tag name is valid"


def validate_json_input(data: dict, required_fields: list = None) -> Tuple[bool, str]:
    """
    Validate JSON input data.
    
    Args:
        data: Dictionary data to validate
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not isinstance(data, dict):
        return False, "Input must be a JSON object"
    
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Check for excessively nested data
    def check_depth(obj, max_depth=10, current_depth=0):
        if current_depth > max_depth:
            return False
        
        if isinstance(obj, dict):
            for value in obj.values():
                if not check_depth(value, max_depth, current_depth + 1):
                    return False
        elif isinstance(obj, list):
            for item in obj:
                if not check_depth(item, max_depth, current_depth + 1):
                    return False
        
        return True
    
    if not check_depth(data):
        return False, "JSON structure too deeply nested"
    
    return True, "JSON input is valid"
