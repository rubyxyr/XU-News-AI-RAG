"""
Main application entry point for XU-News-AI-RAG backend.
"""
import os
from flask import Flask
from flask_migrate import upgrade

from app import create_app, db
from app.models import User, Document, Source, Tag, SearchHistory


# Create application
app = create_app(os.environ.get('FLASK_ENV', 'development'))


@app.cli.command()
def init_db():
    """Initialize database with tables."""
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")


@app.cli.command()
def reset_db():
    """Reset database (drop all tables and recreate)."""
    print("Dropping all tables...")
    db.drop_all()
    print("Creating database tables...")
    db.create_all()
    print("Database reset successfully!")


@app.cli.command()
def create_admin():
    """Create admin user."""
    from getpass import getpass
    
    username = input("Admin username: ").strip()
    if not username:
        print("Username required!")
        return
    
    email = input("Admin email: ").strip()
    if not email:
        print("Email required!")
        return
    
    password = getpass("Admin password: ")
    if not password:
        print("Password required!")
        return
    
    # Check if user exists
    if User.query.filter_by(username=username).first():
        print(f"User {username} already exists!")
        return
    
    if User.query.filter_by(email=email).first():
        print(f"Email {email} already registered!")
        return
    
    # Create admin user
    try:
        admin_user = User.create_user(
            username=username,
            email=email,
            password=password,
            is_admin=True,  # Add admin flag if you implement it
            is_verified=True
        )
        
        print(f"Admin user '{username}' created successfully!")
        print(f"User ID: {admin_user.id}")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")


@app.cli.command()
def cleanup_data():
    """Clean up old data (search history, temporary files, etc.)."""
    try:
        # Clean up old search history (older than 90 days)
        removed_searches = SearchHistory.cleanup_old_searches(days=90)
        print(f"Removed {removed_searches} old search records")
        
        # Update tag usage counts
        Tag.update_all_usage_counts()
        print("Updated tag usage counts")
        
        # Clean up unused tags
        removed_tags = Tag.cleanup_unused_tags(min_usage=0)
        print(f"Removed {removed_tags} unused tags")
        
        print("Data cleanup completed!")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")


if __name__ == '__main__':
    # Run development server
    app.run(
        host='127.0.0.1',
        port=int(os.environ.get('PORT', 8091)),
        debug=True
    )
