"""
Pytest configuration and shared fixtures for all tests.
"""
import os
import sys
import pytest
from datetime import datetime

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User
from app.models.document import Document
from app.models.source import Source
from app.models.tag import Tag


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    # Create app with testing configuration
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean database before each test."""
    with app.app_context():
        # Clear all tables with more thorough cleanup
        db.session.remove()
        db.session.close()
        db.drop_all()
        db.create_all()
        db.session.commit()


@pytest.fixture
def runner(app):
    """Create a test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(client, request, app):
    """Create authenticated user and return authorization headers."""
    import time
    import random
    from app.models.user import User
    
    max_attempts = 3
    for attempt in range(max_attempts):
        # Generate unique username for each attempt
        unique_id = f"{int(time.time()*1000)}_{random.randint(1000, 9999)}"
        user_data = {
            'username': f'testuser_{unique_id}',
            'email': f'test_{unique_id}@example.com',
            'password': 'StrongTest123!'
        }
        
        # Force clean database state
        with app.app_context():
            try:
                # Explicit session cleanup
                db.session.expunge_all()
                db.session.rollback()
                
                # Check for and remove existing user
                existing = User.query.filter_by(username=user_data['username']).first()
                if existing:
                    db.session.delete(existing)
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                if attempt == max_attempts - 1:
                    print(f"Database cleanup failed: {e}")
        
        # Register the user
        response = client.post('/api/auth/register', json=user_data)
        
        if response.status_code == 201:
            # Success! Get the token and return
            token = response.json['access_token']
            return {'Authorization': f'Bearer {token}'}
        
        # Registration failed, debug and try again if we have attempts left
        if attempt == max_attempts - 1:
            # This was our last attempt, fail with full debug info
            print(f"Registration failed after {max_attempts} attempts")
            print(f"Final failure - Status: {response.status_code}")
            print(f"Response: {response.get_json()}")
            print(f"Attempted username: {user_data['username']}")
            print(f"Test: {request.node.name}")
            
            with app.app_context():
                try:
                    existing_users = User.query.all()
                    print(f"Existing users in DB: {[u.username for u in existing_users]}")
                except Exception as e:
                    print(f"Could not check existing users: {e}")
            
            # Fail the test
            assert False, f"Registration failed after {max_attempts} attempts: {response.get_json()}"
        else:
            # Try again with a small delay
            time.sleep(0.01)
            print(f"Registration attempt {attempt + 1} failed, retrying...")


@pytest.fixture
def sample_user(app):
    """Create a sample user in the database."""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username='sampleuser').first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
            
        user = User(
            username='sampleuser',
            email='sample@example.com'
        )
        user.set_password('StrongSample123!')
        db.session.add(user)
        db.session.commit()
        
        # Refresh the user to ensure it's properly bound
        db.session.refresh(user)
        return user


@pytest.fixture
def sample_document(app, sample_user):
    """Create a sample document in the database."""
    with app.app_context():
        document = Document(
            title='Sample Document',
            content='This is sample content for testing.',
            user_id=sample_user.id,
            source_type='manual',
            published_date=datetime.utcnow()
        )
        db.session.add(document)
        db.session.commit()
        return document


@pytest.fixture
def sample_source(app, sample_user):
    """Create a sample RSS source in the database."""
    with app.app_context():
        source = Source(
            name='Test RSS Feed',
            url='https://example.com/rss',
            source_type='rss',
            user_id=sample_user.id,
            is_active=True
        )
        db.session.add(source)
        db.session.commit()
        return source


@pytest.fixture
def sample_tags(app):
    """Create sample tags in the database."""
    with app.app_context():
        tags = [
            Tag(name='technology'),
            Tag(name='science'),
            Tag(name='business')
        ]
        for tag in tags:
            db.session.add(tag)
        db.session.commit()
        return tags
