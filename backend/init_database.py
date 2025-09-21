#!/usr/bin/env python3
"""
Database Initialization Script for XU-News-AI-RAG
=================================================

This script initializes the database and creates demo data.
Use this script to set up your development environment.

Usage:
    python init_database.py           # Initialize DB + create demo data
    python init_database.py --db-only # Initialize DB tables only
"""
import os
import sys
import argparse

# Add current directory to path
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import User, Document, Source, Tag, SearchHistory

def init_database(app):
    """Initialize database tables."""
    print("=" * 60)
    print("🔧 INITIALIZING DATABASE")
    print("=" * 60)
    
    try:
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return False

def create_demo_data(app):
    """Create demo user and sample data."""
    print("\n" + "=" * 60)
    print("📝 CREATING DEMO DATA")
    print("=" * 60)
    
    try:
        # Check if demo user already exists
        if User.query.filter_by(username='demo').first():
            print("⚠️  Demo user already exists! Skipping demo data creation.")
            print("   If you want to recreate demo data, please delete the existing 'demo' user first.")
            return True
            
        print("Creating demo user...")
        demo_user = User.create_user(
            username='demo',
            email='demo@xu-news-ai-rag.com',
            password='demo123456',
            first_name='Demo',
            last_name='User',
            is_verified=True
        )
        print("✓ Demo user created successfully!")
        
        print("Creating sample RSS source...")
        sample_source = Source.create_source(
            user_id=demo_user.id,
            name='TechCrunch',
            url='https://techcrunch.com/feed/',
            source_type='rss',
            description='Technology news and startup information',
            auto_tags=['tech', 'startup', 'news']
        )
        print("✓ Sample RSS source created successfully!")
        
        print("Creating sample documents...")
        # Create sample documents
        sample_doc1 = Document.create_document(
            user_id=demo_user.id,
            title='Welcome to XU-News-AI-RAG - Your AI-Powered Knowledge Base',
            content='''
            Welcome to XU-News-AI-RAG, an advanced AI-powered knowledge management system designed to revolutionize how you organize, search, and interact with information.

            🚀 **Core Features:**
            - **Intelligent Document Upload**: Support for CSV and XLSX files with automatic content extraction
            - **Smart RSS Integration**: Automated news collection from RSS feeds with intelligent categorization
            - **Advanced Semantic Search**: AI-powered search using state-of-the-art embedding models for contextual understanding
            - **Dynamic Tagging System**: Automatic and manual tagging with trending keyword analytics
            - **Real-time Processing**: Streaming uploads and background processing for seamless user experience

            🔍 **Search Capabilities:**
            - Semantic search with similarity scoring
            - Cross-reference reranking for improved results
            - External search integration when local results are insufficient
            - Search history tracking and analytics

            📊 **Analytics & Insights:**
            - Trending keywords dashboard
            - Document statistics and usage patterns
            - Search analytics and performance metrics
            - User activity tracking

            🛠️ **Technical Excellence:**
            - Flask-based REST API with JWT authentication
            - SQLAlchemy ORM with efficient database operations
            - FAISS vector storage for lightning-fast similarity search
            - Background task processing for optimal performance
            - Modern React frontend with Material-UI components

            Get started by uploading your documents, exploring the search functionality, or checking out the trending keywords on your dashboard!
            ''',
            summary='Comprehensive introduction to XU-News-AI-RAG system with detailed feature overview and technical capabilities.',
            source_type='manual',
            tags=['welcome', 'demo', 'introduction', 'features', 'ai', 'knowledge-base']
        )
        
        sample_doc2 = Document.create_document(
            user_id=demo_user.id,
            title='Getting Started Guide - Quick Start Instructions',
            content='''
            🚀 **Quick Start Guide for XU-News-AI-RAG**

            **1. Document Management:**
            - Navigate to the "Documents" tab to upload files
            - Supported formats: CSV, XLSX
            - For CSV/XLSX files, ensure columns: title, content, author, published_date, category, source_url, tags
            - Use batch operations for multiple document management

            **2. Search & Discovery:**
            - Use the search bar to find documents by content, not just titles
            - Try semantic queries like "artificial intelligence applications" or "machine learning techniques"
            - Click on trending keywords in the dashboard for quick searches
            - Filter results by tags and categories

            **3. RSS Sources:**
            - Add RSS feeds for automatic content collection
            - Configure auto-tagging for categorized content
            - Monitor source activity and statistics

            **4. Profile & Settings:**
            - Update your profile information in the Profile section
            - Customize your notification preferences
            - Review your search history and usage statistics

            **5. Advanced Tips:**
            - Use specific keywords in your searches for better results
            - Organize documents with consistent tagging
            - Explore the analytics dashboard for insights
            - Delete documents in batches when needed

            **Sample Commands for Testing:**
            - Try searching for "welcome" or "getting started"
            - Upload a sample document to test the functionality
            - Add a demo RSS feed to see automated content collection

            For technical setup and development information, check the project README.md file.
            ''',
            summary='Step-by-step guide for new users to get started with the XU-News-AI-RAG system.',
            source_type='manual',
            tags=['guide', 'tutorial', 'getting-started', 'instructions', 'help']
        )
        
        sample_doc3 = Document.create_document(
            user_id=demo_user.id,
            title='System Architecture & Technical Overview',
            content='''
            📋 **XU-News-AI-RAG Technical Architecture**

            **Backend Stack:**
            - Python 3.10+ with Flask web framework
            - SQLAlchemy ORM for database operations
            - JWT-based authentication and authorization
            - APScheduler for background task management
            - ThreadPoolExecutor for concurrent processing
            - FAISS vector database for similarity search
            - LangChain integration for AI processing

            **Frontend Stack:**
            - React 18 with modern hooks and functional components
            - Material-UI (MUI) for professional user interface
            - Redux Toolkit for state management
            - React Router for navigation
            - Formik & Yup for form handling and validation
            - Axios for API communication

            **AI & ML Components:**
            - Sentence Transformers for text embeddings
            - Cross-encoder models for result reranking
            - FAISS for efficient vector similarity search
            - Hugging Face transformers integration
            - Custom similarity scoring algorithms

            **Data Processing:**
            - CSV/XLSX processing with pandas for structured data
            - Streaming file uploads for large files
            - Background vector indexing
            - Real-time progress updates

            **Performance Features:**
            - In-memory caching for model management
            - File-based caching for embeddings
            - Background task processing
            - Streaming responses for large operations
            - Optimized database queries

            **Security & Authentication:**
            - JWT token-based authentication
            - Password strength validation
            - User session management
            - CORS configuration for cross-origin requests
            - Input validation and sanitization

            This architecture ensures scalability, performance, and maintainability while providing a smooth user experience.
            ''',
            summary='Detailed technical architecture and stack overview of the XU-News-AI-RAG system.',
            source_type='manual',
            tags=['architecture', 'technical', 'backend', 'frontend', 'ai', 'stack', 'documentation']
        )
        print("✓ Sample documents created successfully!")
        
        # Process sample documents through AI pipeline for semantic search
        print("Processing documents through AI pipeline...")
        try:
            from app.ai.langchain_service import LangChainService
            
            ai_config = {
                'EMBEDDINGS_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
                'VECTOR_STORE_PATH': 'data/vector_stores',
                'LLM_MODEL': 'qwen3:4b',
                'OLLAMA_BASE_URL': 'http://localhost:11434',
                'RERANKER_MODEL': 'cross-encoder/ms-marco-MiniLM-L-6-v2'
            }
            
            ai_pipeline = LangChainService(config=ai_config)
            
            # Process each document through AI pipeline
            for doc, doc_name in [(sample_doc1, "Welcome Document"), 
                                 (sample_doc2, "Getting Started Guide"), 
                                 (sample_doc3, "Technical Overview")]:
                try:
                    success = ai_pipeline.process_document(doc)
                    if success:
                        print(f"  ✓ {doc_name} processed through AI pipeline")
                    else:
                        print(f"  ⚠️  Failed to process {doc_name} through AI pipeline")
                except Exception as e:
                    print(f"  ⚠️  Error processing {doc_name}: {e}")
                    
        except Exception as e:
            print(f"⚠️  Error initializing AI pipeline: {e}")
            print("   Documents created but not processed for semantic search")
            print("   You can process them later using the admin interface")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        return False

def main():
    """Main initialization function."""
    parser = argparse.ArgumentParser(
        description='Initialize XU-News-AI-RAG database and create demo data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init_database.py              # Full initialization (DB + demo data)
  python init_database.py --db-only    # Database tables only
        """
    )
    parser.add_argument('--db-only', action='store_true', 
                       help='Initialize database tables only (skip demo data)')
    
    args = parser.parse_args()
    
    print("🚀 XU-News-AI-RAG Database Initialization")
    print("   Version: 1.0")
    print("   Environment:", os.environ.get('FLASK_ENV', 'development'))
    
    # Create application
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    
    with app.app_context():
        success = True
        
        # Initialize database
        if not init_database(app):
            success = False
        
        # Create demo data if requested
        if success and not args.db_only:
            if not create_demo_data(app):
                success = False
        elif args.db_only:
            print("\n✓ Database-only initialization completed!")
        
        # Final status
        print("\n" + "=" * 60)
        if success:
            print("🎉 INITIALIZATION COMPLETED SUCCESSFULLY!")
            if not args.db_only:
                print("\n📋 Demo Account Details:")
                print("   Username: demo")
                print("   Password: demo123456")
                print("   Email: demo@xu-news-ai-rag.com")
                print("\n💡 Next Steps:")
                print("   1. Start the backend server: python app.py")
                print("   2. Start the frontend server: cd ../frontend && npm start")
                print("   3. Open http://localhost:3000 in your browser")
                print("   4. Login with the demo account credentials")
        else:
            print("❌ INITIALIZATION FAILED!")
            print("   Please check the error messages above and try again.")
            sys.exit(1)
        print("=" * 60)

if __name__ == '__main__':
    main()