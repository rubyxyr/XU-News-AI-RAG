"""
Unit tests for database models.
"""
import pytest
from datetime import datetime
from app.models.user import User
from app.models.document import Document
from app.models.source import Source
from app.models.tag import Tag
from app.models.search_history import SearchHistory
from app import db


class TestUserModel:
    """Test User model functionality."""
    
    def test_create_user(self, app):
        """Test creating a new user."""
        with app.app_context():
            user = User(
                username='newuser',
                email='new@example.com'
            )
            user.set_password('Password123!')
            
            assert user.username == 'newuser'
            assert user.email == 'new@example.com'
            assert user.check_password('Password123!')
            assert not user.check_password('WrongPassword')
            
            db.session.add(user)
            db.session.commit()
            
            # Verify user was saved
            saved_user = User.query.filter_by(username='newuser').first()
            assert saved_user is not None
            assert saved_user.email == 'new@example.com'
    
    def test_user_unique_constraints(self, app, sample_user):
        """Test that username and email must be unique."""
        with app.app_context():
            # Try to create a user with duplicate username
            duplicate_user = User(
                username=sample_user.username,
                email='different@example.com'
            )
            duplicate_user.set_password('Password123!')
            
            db.session.add(duplicate_user)
            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()
            db.session.rollback()
            
            # Try to create a user with duplicate email
            duplicate_email_user = User(
                username='differentuser',
                email=sample_user.email
            )
            duplicate_email_user.set_password('Password123!')
            
            db.session.add(duplicate_email_user)
            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()
    
    def test_user_to_dict(self, app, sample_user):
        """Test user serialization."""
        with app.app_context():
            user_dict = sample_user.to_dict(include_sensitive=True)
            
            assert 'id' in user_dict
            assert 'username' in user_dict
            assert 'email' in user_dict
            assert 'password_hash' not in user_dict  # Should not expose password
            assert user_dict['username'] == sample_user.username
            assert user_dict['email'] == sample_user.email


class TestDocumentModel:
    """Test Document model functionality."""
    
    def test_create_document(self, app, sample_user):
        """Test creating a new document."""
        with app.app_context():
            document = Document(
                title='Test Document',
                content='Test content',
                user_id=sample_user.id,
                source_type='manual',
                source_url='https://example.com',
                published_date=datetime.utcnow()
            )
            
            db.session.add(document)
            db.session.commit()
            
            assert document.id is not None
            assert document.title == 'Test Document'
            assert document.content == 'Test content'
            assert document.user_id == sample_user.id
            
            # Test relationship
            assert document.owner.id == sample_user.id
    
    def test_document_with_tags(self, app, sample_user, sample_tags):
        """Test document-tag relationship."""
        with app.app_context():
            document = Document(
                title='Document with Tags',
                content='Content with tags',
                user_id=sample_user.id
            )
            
            # Add tags to document
            document.tags.extend(sample_tags[:2])  # Add first two tags
            
            db.session.add(document)
            db.session.commit()
            
            # Verify tags were added
            saved_doc = Document.query.filter_by(title='Document with Tags').first()
            assert len(saved_doc.tags) == 2
            assert sample_tags[0] in saved_doc.tags
            assert sample_tags[1] in saved_doc.tags
    
    def test_document_to_dict(self, app, sample_user):
        """Test document serialization."""
        with app.app_context():
            # Create document within test context to avoid DetachedInstanceError
            document = Document(
                title='Test Document',
                content='Test content for serialization',
                user_id=sample_user.id,
                source_type='manual',
                published_date=datetime.utcnow()
            )
            db.session.add(document)
            db.session.commit()
            
            doc_dict = document.to_dict()
            
            assert 'id' in doc_dict
            assert 'title' in doc_dict
            assert 'content' in doc_dict
            assert 'created_at' in doc_dict
            assert 'content_type' in doc_dict
            assert doc_dict['title'] == 'Test Document'


class TestSourceModel:
    """Test Source model functionality."""
    
    def test_create_source(self, app, sample_user):
        """Test creating a new source."""
        with app.app_context():
            source = Source(
                name='Test Source',
                url='https://test.com/rss',
                source_type='rss',
                user_id=sample_user.id,
                is_active=True,
                update_frequency=30
            )
            
            db.session.add(source)
            db.session.commit()
            
            assert source.id is not None
            assert source.name == 'Test Source'
            assert source.url == 'https://test.com/rss'
            assert source.is_active == True
            assert source.update_frequency == 30
    
    def test_source_deactivation(self, app, sample_user):
        """Test source activation/deactivation."""
        with app.app_context():
            # Create source within test context to avoid DetachedInstanceError
            source = Source(
                name='Test Source',
                url='https://test.com/rss',
                source_type='rss',
                user_id=sample_user.id,
                is_active=True
            )
            db.session.add(source)
            db.session.commit()
            source_id = source.id
            
            # Initially active
            assert source.is_active == True
            
            # Deactivate
            source.is_active = False
            db.session.commit()
            
            # Verify deactivation
            updated_source = Source.query.get(source_id)
            assert updated_source.is_active == False
    
    def test_source_to_dict(self, app, sample_user):
        """Test source serialization."""
        with app.app_context():
            # Create source within test context to avoid DetachedInstanceError
            source = Source(
                name='Test Source Serialization',
                url='https://test-serialize.com/rss',
                source_type='rss',
                user_id=sample_user.id,
                is_active=True
            )
            db.session.add(source)
            db.session.commit()
            
            source_dict = source.to_dict()
            
            assert 'id' in source_dict
            assert 'name' in source_dict
            assert 'url' in source_dict
            assert 'source_type' in source_dict
            assert 'is_active' in source_dict
            assert source_dict['name'] == 'Test Source Serialization'


class TestTagModel:
    """Test Tag model functionality."""
    
    def test_create_tag(self, app):
        """Test creating a new tag."""
        with app.app_context():
            tag = Tag(name='newtag')
            
            db.session.add(tag)
            db.session.commit()
            
            assert tag.id is not None
            assert tag.name == 'newtag'
            
            # Verify tag was saved
            saved_tag = Tag.query.filter_by(name='newtag').first()
            assert saved_tag is not None
    
    def test_tag_unique_constraint(self, app):
        """Test that tag names must be unique."""
        with app.app_context():
            tag1 = Tag(name='uniquetag')
            db.session.add(tag1)
            db.session.commit()
            
            # Try to create duplicate tag
            tag2 = Tag(name='uniquetag')
            db.session.add(tag2)
            
            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()
    
    def test_tag_documents_relationship(self, app, sample_tags, sample_user):
        """Test tag-document relationship."""
        with app.app_context():
            # Create documents with tags
            doc1 = Document(
                title='Doc 1',
                content='Content 1',
                user_id=sample_user.id
            )
            doc1.tags.append(sample_tags[0])
            
            doc2 = Document(
                title='Doc 2', 
                content='Content 2',
                user_id=sample_user.id
            )
            doc2.tags.append(sample_tags[0])
            
            db.session.add_all([doc1, doc2])
            db.session.commit()
            
            # Verify tag has both documents
            tag = Tag.query.get(sample_tags[0].id)
            assert len(tag.documents) == 2


class TestSearchHistoryModel:
    """Test SearchHistory model functionality."""
    
    def test_create_search_history(self, app, sample_user):
        """Test creating search history entry."""
        with app.app_context():
            search = SearchHistory(
                user_id=sample_user.id,
                query='test search query',
                results_count=5,
                query_type='semantic'
            )
            
            db.session.add(search)
            db.session.commit()
            
            assert search.id is not None
            assert search.query == 'test search query'
            assert search.results_count == 5
            assert search.query_type == 'semantic'
            assert search.user_id == sample_user.id
    
    def test_search_history_timestamps(self, app, sample_user):
        """Test that timestamps are automatically set."""
        with app.app_context():
            search = SearchHistory(
                user_id=sample_user.id,
                query='timestamp test',
                results_count=0
            )
            
            db.session.add(search)
            db.session.commit()
            
            assert search.created_at is not None
            assert isinstance(search.created_at, datetime)
    
    def test_user_search_history_relationship(self, app, sample_user):
        """Test user-search history relationship."""
        with app.app_context():
            # Create multiple search entries
            searches = [
                SearchHistory(
                    user_id=sample_user.id,
                    query=f'query {i}',
                    results_count=i
                )
                for i in range(3)
            ]
            
            db.session.add_all(searches)
            db.session.commit()
            
            # Verify user has all search entries
            user = User.query.get(sample_user.id)
            assert len(user.search_history.all()) == 3
