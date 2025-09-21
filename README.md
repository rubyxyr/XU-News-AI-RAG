# XU-News-AI-RAG: Personalized News Intelligent Knowledge Base

A comprehensive, production-ready AI-powered knowledge management system that automatically collects, processes, and organizes news content while providing intelligent semantic search capabilities. Enhanced with modern UI/UX, robust error handling, and optimized performance.

## 🚀 Features

### Core Functionality
- **Automated Content Collection**: RSS feed crawling, web scraping, and intelligent proxy support
- **AI-Powered Search**: Enhanced semantic search with fixed similarity scoring and result reranking
- **Knowledge Base Management**: Document organization, tagging, batch operations, and metadata management
- **User Authentication**: JWT-based secure authentication with complete profile management
- **Analytics Dashboard**: Trending keywords analysis, content clustering, and usage insights
- **Email Notifications** (Optional): Customizable alerts for new content additions when SMTP is configured
- **Streaming File Processing**: Real-time progress updates for document uploads and bulk imports

### Enhanced User Experience
- **Modern UI/UX**: Streamlined interface with Material-UI components and responsive design
- **Unified Search**: Auto-fill search functionality with URL parameter support
- **Profile Management**: Complete user profile editing with real-time validation
- **Background Processing**: Asynchronous operations for better performance
- **Error Handling**: Comprehensive error management with user-friendly messages
- **Accessibility**: Enhanced keyboard navigation and screen reader support

### AI Integration & Improvements
- **Large Language Model**: Ollama qwen3:4b for content analysis and generation
- **Embeddings**: all-MiniLM-L6-v2 for vector generation and semantic search
- **Reranking**: ms-marco-MiniLM-L-6-v2 for optimized search result ordering
- **LangChain Framework**: Comprehensive AI pipeline orchestration with background processing
- **Vector Database**: FAISS with optimized similarity scoring and efficient cleanup
- **Fixed AI Pipeline**: Corrected distance-to-similarity conversion for accurate search results
- **Structured Data Processing**: Specialized CSV/XLSX file processing with automatic tag extraction and content organization
- **Background AI Operations**: Asynchronous vector database operations for better performance

### Technical Stack
- **Backend**: Flask 2.3+ with SQLAlchemy ORM and APScheduler for task scheduling
- **Frontend**: React 18+ with Material-UI components
- **Database**: SQLite (development) / PostgreSQL (production)
- **Caching**: In-memory caching (Python dictionaries and file-based model cache)
- **Background Tasks**: ThreadPoolExecutor for asynchronous operations
- **AI Framework**: LangChain with HuggingFace Transformers
- **Deployment**: Docker containers with docker-compose

## 📋 Prerequisites

### System Requirements
- Python 3.9+
- Node.js 18+
- Ollama (for LLM integration)
- Git

### Hardware Recommendations
- **Minimum**: 8GB RAM, 2 CPU cores, 10GB storage
- **Recommended**: 16GB RAM, 4 CPU cores, 50GB storage (for better AI performance)

## 🛠️ Installation & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd ai_rag
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Environment Configuration
Create a `.env` file in the backend directory:
```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///app.db

# AI Model Configuration
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
LLM_MODEL=qwen3:4b

# Email Configuration (OPTIONAL - only needed for email notifications)
# Leave these commented out if you don't want email notifications
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-app-password

# External APIs (optional)
GOOGLE_SEARCH_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id

# File Storage
UPLOAD_FOLDER=../data/uploads
VECTOR_STORE_PATH=../data/vector_stores
MAX_CONTENT_LENGTH=16777216

# Security
CORS_ORIGINS=http://localhost:3000
```

#### Initialize Database
```bash
# Full initialization: database tables + demo data + AI processing
python init_database.py

# Or just create database tables without demo data
python init_database.py --db-only

# Get help and see all options
python init_database.py --help
```

**What the initialization script does:**
- ✅ Creates all database tables
- ✅ Creates demo user account: `demo` / `demo123456`
- ✅ Creates sample RSS source (TechCrunch)
- ✅ Creates 3 sample documents with comprehensive content
- ✅ Processes documents through AI pipeline for immediate semantic search
- ✅ Provides detailed progress feedback and error handling


#### Quick Start: Add Sample Documents (Optional)
If you want to quickly populate the database with some sample documents for testing, you can use the crawler CLI tool:

```bash
# List all sources
# Fetch the source id that you created if you aleady ran python init_database.py.   
python crawler_cli.py list-sources

# This will crawl the demo RSS source (TechCrunch) created during database initialization
python crawler_cli.py crawl-source --source-id 1

```

**Note**: The crawler CLI provides additional commands for managing sources and crawling:
```bash
# See all available commands
python crawler_cli.py --help

# List all sources  
python crawler_cli.py list-sources

# Add a new RSS source
python crawler_cli.py add-source --name "Example News" --url "https://example.com/rss" --type rss
```

You can also schedule crawlers to crawl information
```bash
# this rss crawler will crawl information every 5 minutes
python run_rss_only.py 

```

### 3. AI Models Setup

#### Install Ollama
```bash
# On macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# On Windows - download from https://ollama.ai/
```

#### Pull Required Models
```bash
# Pull the LLM model
ollama pull qwen3:4b

# Start Ollama service
ollama serve  # Keep this running in a separate terminal
```

#### Verify Model Installation
```bash
# Test the model
ollama run qwen3:4b "Hello, how are you?"
```

### 4. Frontend Setup

#### Install Node Dependencies
```bash
cd ../frontend
npm install
```

#### Environment Configuration
Create a `.env` file in the frontend directory:
```bash
REACT_APP_API_URL=http://localhost:8091
REACT_APP_APP_NAME=XU-News-AI-RAG
```

### 5. Caching (Built-in)

The application uses in-memory caching with Python dictionaries and file-based model caching. No external cache server is required for basic functionality.

**Note**: For production scaling with multiple server instances, consider implementing Redis or Memcached for shared caching.

## 🚀 Running the Application

### Development Environment

#### Terminal 1: Backend API
```bash
cd backend
source venv/bin/activate
python app.py
# API will be available at http://localhost:8091
```

#### Terminal 2: Frontend
```bash
cd frontend
npm start
# Frontend will be available at http://localhost:3000
```

#### Terminal 3: Ollama Service
```bash
ollama serve
# LLM service will be available at http://localhost:11434
```


## 📖 Usage Guide

### 1. User Registration and Login
1. Navigate to http://localhost:3000
2. Click "Sign Up" to create a new account 
![Sign up](docs/sign_up.png)
3. Login with credentials (no email verification required unless SMTP is configured)
![Login](docs/login.png)

**Note:** Email verification is only required if you configure SMTP settings. For development, you can skip email configuration entirely.

### 2. Document Management
#### Upload Documents
1. Go to "Documents" page 
2. Click "Upload Document" button
3. Drag & drop files or browse (supports CSV and XLSX files only). You can use the "news_sample.csv" file in this project we already generated for you to try this "Upload" function. 
![Document upload](docs/upload_document.png)
4. Files process with real-time progress updates and streaming feedback
5. CSV/XLSX files automatically extract tags from dedicated columns and merge with user-provided tags

#### Manage Documents
1. View all documents in "Documents" page with improved layout 
![Document list](docs/document_list.png) 
![Document details](docs/document_details.png)
2. Use enhanced filters: date range, source type, tags, or text search
3. Select multiple documents for batch operations
4. Edit metadata, add/remove tags with instant updates 
![Edit document](docs/edit_document.png)
5. Delete individual documents or batch delete with background cleanup 
![Delete document](docs/delete_document.png)

### 3. RSS Source Configuration
1. Navigate to "Sources" → "RSS Feeds"
2. Click "Add Source"
3. Enter RSS feed URL and configuration:
   - **Name**: Display name for the source
   - **URL**: RSS feed URL
   - **Update Frequency**: How often to check (minutes)
   - **Auto Tags**: Tags to apply automatically
   - **Settings**: Advanced crawling options

4. Activate source for automatic crawling 
![Source info](docs/source_info.png)

**Email Notifications:** If SMTP is configured, you'll receive email notifications when new articles are collected. Without SMTP configuration, the system logs notifications but doesn't send actual emails (which is perfectly fine for development).

### 4. Enhanced Semantic Search
1. **Dashboard Search**: Use the main search bar for quick queries with auto-redirect to results 
![Dashboard search](docs/search.png)
2. **Search Page**: Access via navigation for advanced search functionality
3. **Auto-fill Feature**: Search terms from dashboard automatically populate in search page
4. **URL Parameters**: Share searches with direct URL links (e.g., `?q=AI%20trends`)

#### Search Capabilities:
- Natural language queries with improved similarity scoring:
  - "What are the latest AI developments?"
  - "Articles about startup funding trends" 
  - "Machine learning research papers"

- **Enhanced Filtering**:
  - Date range with calendar picker
  - Source type (RSS, uploads, web scraping)
  - Tags with autocomplete
  - Content type and relevance scoring

- **Search Features**:
  - Real-time suggestions
  - Search history
  - Clickable tag navigation
  - Results with similarity scores (0-100%)

![Search 1](docs/search_with_model.png)
![Search 2](docs/search_with_web.png)
![Search 3](docs/ai_agent_analyze_web_search_1.png)
![Search 4](docs/ai_agent_analyze_web_search_2.png)
![Search 5](docs/ai_agent_analyze_web_search_3.png)
![Search 6](docs/search_result.png)

### 5. Analytics and Insights
1. **Dashboard Overview**: Quick stats and trending keywords at a glance
![Analytics dashboard](docs/analyze.png)
2. **Analytics Page**: Comprehensive analysis and visualizations
3. **Enhanced Features**:
   - Document growth over time with trend analysis
   - Source distribution with performance metrics
   - **Trending Keywords**: Real-time analysis of popular tags and topics
   - Content clustering with intelligent grouping
   - User activity patterns and search analytics

#### Dashboard Highlights:
- **Total Documents**: Current count with growth indicators
- **Active Sources**: RSS feeds and their status
- **Trending Keywords**: Top 10 keywords with usage statistics and color-coded chips
- **Recent Activity**: Latest system activities and updates

## 🔧 Configuration

### AI Model Configuration
```python
# config.py - AI settings
EMBEDDINGS_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
RERANKER_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
LLM_MODEL = 'qwen3:4b'
OLLAMA_BASE_URL = 'http://localhost:11434'
```

### Database Configuration
```python
# Development (SQLite)
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'

# Production (PostgreSQL)
SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/xu_news_ai_rag'
```

### Crawler Settings
```python
CRAWLER_DELAY = 1  # seconds between requests
CRAWLER_RESPECT_ROBOTS_TXT = True
CRAWLER_MAX_CONCURRENT_REQUESTS = 5
```

## 🧪 Testing

### Run Backend Tests
```bash
cd backend
source venv/bin/activate

# Run all tests
pytest 

```

### Run Frontend Tests
```bash
cd frontend

# Run all tests
npm test

# Full coverage report
npm run test:coverage

```

### API Testing with Postman
1. Import the Postman collection from `docs/api/postman_collection.json`
2. Set environment variables:
   - `base_url`: http://localhost:8091
   - `access_token`: (obtain from login)
3. Run the test suite

## 📊 Monitoring and Maintenance

### Health Checks
```bash
# Check API health
curl http://localhost:8091/health

# Check Ollama service
curl http://localhost:11434/api/version

```


### Database Maintenance
```bash
# Backup database
flask backup-db --output backup_$(date +%Y%m%d).sql

# Clean up old data
flask cleanup-data

# Update tag usage counts
flask update-tags
```

## 🔒 Security Considerations

### Authentication Security
- JWT tokens with configurable expiration
- Password strength validation
- Rate limiting on API endpoints
- CORS configuration for cross-origin requests

### Data Security
- Input sanitization and validation
- SQL injection prevention
- File upload security checks
- Content Security Policy headers

### Deployment Security
- Environment variable configuration
- HTTPS enforcement in production
- Database connection encryption
- API key management

## 🚨 Troubleshooting

### Common Issues & Solutions

#### Ollama Connection Error
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Restart Ollama service
ollama serve

# Check model availability
ollama list

# Pull required model if missing
ollama pull qwen3:4b
```

#### Frontend Build Issues
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear npm cache
npm cache clean --force

# If ESLint errors about missing components:
# Check that all Material-UI imports are correct
```

### Performance Optimization

#### AI Model Performance
- Ensure adequate RAM (8GB+ recommended)
- Use GPU acceleration if available
- Consider model quantization for smaller models
- Implement model caching and warm-up

#### Database Performance
- Add appropriate indexes for frequent queries
- Use connection pooling
- Consider upgrading to PostgreSQL for production
- Implement query optimization

#### Search Performance
- Pre-generate embeddings for large document sets
- Use FAISS index optimization
- Implement result caching
- Consider search result pagination

## 📈 Scaling Considerations

### Horizontal Scaling
- Use multiple backend workers with load balancer
- Consider implementing Redis or distributed caching for multi-instance deployments
- Consider microservices architecture for large deployments

### Database Scaling
- PostgreSQL with read replicas
- Connection pooling with PgBouncer
- Database sharding for very large datasets

### AI Model Scaling
- Dedicated model servers (e.g., multiple Ollama instances)
- Model versioning and A/B testing
- Batch processing for embeddings generation

## 🆘 Support

### Documentation
- [Architecture Overview](docs/Technical-Architecture.md)
- [PRD](docs/PRD.md)


---

**Built with ❤️ using Flask, React, and state-of-the-art AI technologies**
