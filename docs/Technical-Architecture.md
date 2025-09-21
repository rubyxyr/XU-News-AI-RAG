# XU-News-AI-RAG: Technical Architecture Document
## Personalized News Intelligent Knowledge Base

---

## 1. Technology Stack Overview

### 1.1 Core Technologies
```yaml
Frontend:
  Framework: React 18.2+
  State Management: Redux Toolkit
  UI Library: Material-UI (MUI)
  HTTP Client: Axios
  Authentication: JWT with react-router-dom guards

Backend:
  Framework: Flask 2.3+
  WSGI Server: Gunicorn
  Background Tasks: ThreadPoolExecutor for async operations
  Scheduling: APScheduler for RSS crawling and periodic tasks
  Authentication: Flask-JWT-Extended
  ORM: SQLAlchemy
  API Documentation: Flask-RESTX (Swagger)

AI & ML Stack:
  Orchestration: LangChain 0.0.350+
  LLM Runtime: Ollama
  Models:
    - LLM: qwen3:4b
    - Embeddings: all-MiniLM-L6-v2
    - Reranking: ms-marco-MiniLM-L-6-v2
  Vector Database: FAISS
  Model Management: HuggingFace Transformers

Data Storage:
  Primary Database: SQLite (dev), PostgreSQL (prod)
  Vector Storage: FAISS indices
  Cache: In-memory (Python dicts) + file-based model cache
  File Storage: Local filesystem with S3 compatibility

External Integrations:
  RSS Processing: feedparser
  Web Scraping: Scrapy, BeautifulSoup4, Selenium
  Search API: Google Custom Search API
  Email: SMTP with Jinja2 templates
  Monitoring: Prometheus + Grafana

Development Tools:
  Testing: pytest, Jest, Cypress
  Code Quality: Black, ESLint, SonarQube
  API Testing: Postman, pytest-httpx
  Documentation: Sphinx, JSDoc
```

### 1.2 Deployment Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Production Environment                    │
│                                                             │
│  ┌───────────────┐    ┌──────────────┐    ┌─────────────┐  │
│  │   Nginx       │───►│   Gunicorn   │───►│  Flask App  │  │
│  │ (Reverse Proxy│    │ (WSGI Server)│    │  (Backend)  │  │
│  │  Static Files)│    └──────────────┘    └─────────────┘  │
│  └───────────────┘                               │         │
│          │                                       │         │
│  ┌───────▼───────┐                        ┌──────▼──────┐  │
│  │  React Build  │                        │ThreadPool   │  │
│  │  (Static)     │                        │Executor +   │  │
│  └───────────────┘                        │APScheduler  │  │
│                                                   │         │
│  ┌─────────────────────────────────────────────────┼─────┐ │
│  │               Data Layer                        │     │ │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────┐   │     │ │
│  │  │PostgreSQL│  │In-Memory │  │ FAISS Index │   │     │ │
│  │  │   DB     │  │  Cache   │  │   Files     │   │     │ │
│  │  └──────────┘  └──────────┘  └─────────────┘   │     │ │
│  └─────────────────────────────────────────────────┼─────┘ │
│                                                   │         │
│  ┌─────────────────────────────────────────────────▼─────┐ │
│  │                   AI Services                        │ │
│  │  ┌──────────────┐  ┌─────────────────────────────────┐ │ │
│  │  │   Ollama     │  │      HuggingFace Models         │ │ │
│  │  │  qwen3:4b  │  │  all-MiniLM-L6-v2 (embeddings)  │ │ │
│  │  │              │  │  ms-marco-MiniLM-L-6-v2 (rerank)│ │ │
│  │  └──────────────┘  └─────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Component Architecture

### 2.1 Frontend Architecture

#### 2.1.1 React Application Structure
```
src/
├── components/           # Reusable UI components
│   ├── common/          # Generic components (Button, Modal, etc.)
│   ├── auth/            # Authentication components
│   ├── search/          # Search-related components
│   ├── content/         # Content management components
│   ├── analytics/       # Analytics and visualization components
│   └── Layout/          # Layout components (Header, Sidebar)
├── pages/               # Page-level components
│   ├── Auth/
│   ├── Dashboard/
│   ├── Search/
│   ├── Documents/
│   ├── Sources/
│   ├── Analytics/
│   ├── Settings/
│   ├── Profile/
│   └── NotFound/
├── store/               # Redux store configuration
│   ├── slices/          # Redux Toolkit slices
│   └── store.js         # Store configuration
├── services/            # API client services
│   ├── apiService.js
│   └── authService.js
├── hooks/               # Custom React hooks
├── utils/               # Utility functions
├── theme/               # MUI theme configuration
└── App.js               # Root component
```

#### 2.1.2 State Management Architecture
```javascript
// Redux Store Structure
{
  auth: {
    user: UserObject | null,
    token: string | null,
    isAuthenticated: boolean,
    loading: boolean,
    error: string | null
  },
  content: {
    documents: Document[],
    pagination: PaginationState,
    filters: FilterState,
    loading: boolean,
    error: string | null
  },
  search: {
    query: string,
    results: SearchResult[],
    history: SearchHistory[],
    suggestions: string[],
    loading: boolean,
    error: string | null
  },
  analytics: {
    keywords: KeywordAnalysis[],
    clusters: ClusterData[],
    usage: UsageStats,
    loading: boolean,
    error: string | null
  }
}
```

### 2.2 Backend Architecture

#### 2.2.1 Flask Application Structure
```
backend/
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── api/                # API blueprints
│   │   ├── auth.py
│   │   ├── content.py
│   │   ├── search.py
│   │   ├── sources.py
│   │   └── analytics.py
│   ├── models/             # SQLAlchemy models
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── source.py
│   │   ├── tag.py
│   │   └── search_history.py
│   ├── services/           # Business logic services
│   │   └── email_service.py
│   ├── ai/                 # AI processing modules
│   │   ├── langchain_service.py
│   │   ├── embeddings.py
│   │   └── vector_store.py
│   ├── crawlers/           # Data acquisition modules
│   │   ├── rss_crawler.py
│   │   ├── web_scraper.py
│   │   ├── scheduler.py
│   │   └── proxy_manager.py
│   └── utils/              # Utility functions
│       ├── decorators.py
│       └── validators.py
├── tests/                  # Test modules
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── config.py               # Configuration management
├── app.py                  # Main application entry point
└── requirements.txt        # Python dependencies
```

#### 2.2.2 Database Models (SQLAlchemy)
```python
# User Model
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic')
    sources = db.relationship('Source', backref='owner', lazy='dynamic')
    search_history = db.relationship('SearchHistory', backref='user', lazy='dynamic')

# Document Model
class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    source_url = db.Column(db.String(1000))
    source_type = db.Column(db.String(50))
    published_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Vector storage metadata
    vector_id = db.Column(db.String(255))  # FAISS vector ID
    embedding_model = db.Column(db.String(100))
    
    # Relationships
    tags = db.relationship('Tag', secondary=document_tags, lazy='subquery',
                          backref=db.backref('documents', lazy=True))

# Tag Model
class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Association table for many-to-many relationship
document_tags = db.Table('document_tags',
    db.Column('document_id', db.Integer, db.ForeignKey('documents.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)
```

### 2.3 AI Pipeline Architecture

#### 2.3.1 LangChain Integration
```python
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker

class AIProcessingPipeline:
    def __init__(self):
        # Initialize embeddings model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize LLM
        self.llm = Ollama(
            model="qwen3:4b",
            base_url="http://localhost:11434",
            temperature=0.3
        )
        
        # Initialize reranker
        self.reranker = CrossEncoderReranker(
            model=CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2"),
            top_k=10
        )
        
    def process_document(self, document_content: str, metadata: dict):
        """Process a document into vector embeddings"""
        # Split text into chunks
        chunks = self.text_splitter.split_text(document_content)
        
        # Create document objects
        documents = [
            Document(page_content=chunk, metadata={**metadata, 'chunk_id': i})
            for i, chunk in enumerate(chunks)
        ]
        
        return documents
    
    def create_vector_store(self, documents: List[Document], user_id: str):
        """Create or update FAISS vector store"""
        vector_store_path = f"data/vector_stores/user_{user_id}"
        
        if os.path.exists(vector_store_path):
            # Load existing vector store
            vector_store = FAISS.load_local(
                vector_store_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            # Add new documents
            vector_store.add_documents(documents)
        else:
            # Create new vector store
            vector_store = FAISS.from_documents(documents, self.embeddings)
        
        # Save updated vector store
        vector_store.save_local(vector_store_path)
        return vector_store
    
    def semantic_search(self, query: str, user_id: str, k: int = 10):
        """Perform semantic search with reranking"""
        vector_store_path = f"data/vector_stores/user_{user_id}"
        
        if not os.path.exists(vector_store_path):
            return []
        
        # Load vector store
        vector_store = FAISS.load_local(
            vector_store_path, 
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Create retriever with reranking
        base_retriever = vector_store.as_retriever(search_kwargs={"k": k * 2})
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.reranker,
            base_retriever=base_retriever
        )
        
        # Retrieve relevant documents
        docs = compression_retriever.get_relevant_documents(query)
        
        return docs
    
    def generate_response(self, query: str, context_docs: List[Document]):
        """Generate response using LLM with retrieved context"""
        # Prepare context
        context = "\n\n".join([doc.page_content for doc in context_docs[:5]])
        
        # Create prompt
        prompt = f"""
        Based on the following context, please answer the question.
        If the context doesn't contain enough information, say so.
        
        Context:
        {context}
        
        Question: {query}
        
        Answer:
        """
        
        # Generate response
        response = self.llm(prompt)
        return response
```

#### 2.3.2 Vector Store Management
```python
class VectorStoreManager:
    def __init__(self, embeddings_model):
        self.embeddings = embeddings_model
        self.base_path = "data/vector_stores"
        
    def get_user_store_path(self, user_id: str) -> str:
        return os.path.join(self.base_path, f"user_{user_id}")
    
    def create_user_store(self, user_id: str, documents: List[Document]):
        """Create new vector store for user"""
        store_path = self.get_user_store_path(user_id)
        os.makedirs(os.path.dirname(store_path), exist_ok=True)
        
        vector_store = FAISS.from_documents(documents, self.embeddings)
        vector_store.save_local(store_path)
        
        return vector_store
    
    def load_user_store(self, user_id: str) -> Optional[FAISS]:
        """Load existing vector store for user"""
        store_path = self.get_user_store_path(user_id)
        
        if not os.path.exists(store_path):
            return None
            
        try:
            return FAISS.load_local(
                store_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            logger.error(f"Failed to load vector store for user {user_id}: {e}")
            return None
    
    def add_documents_to_store(self, user_id: str, documents: List[Document]):
        """Add documents to existing vector store"""
        vector_store = self.load_user_store(user_id)
        
        if vector_store is None:
            vector_store = self.create_user_store(user_id, documents)
        else:
            vector_store.add_documents(documents)
            store_path = self.get_user_store_path(user_id)
            vector_store.save_local(store_path)
        
        return vector_store
    
    def delete_documents_from_store(self, user_id: str, document_ids: List[str]):
        """Remove documents from vector store"""
        vector_store = self.load_user_store(user_id)
        
        if vector_store is None:
            return
        
        # FAISS doesn't support direct deletion, so we need to rebuild
        # This is a known limitation that would be addressed in production
        # with a more sophisticated vector database like Pinecone or Weaviate
        
        # For now, we'll mark documents as deleted in metadata
        # and filter them during search
        pass
    
    def search_similar(self, user_id: str, query: str, k: int = 10) -> List[Tuple[Document, float]]:
        """Search for similar documents"""
        vector_store = self.load_user_store(user_id)
        
        if vector_store is None:
            return []
        
        # Perform similarity search with scores
        docs_and_scores = vector_store.similarity_search_with_score(query, k=k)
        return docs_and_scores
```

### 2.4 Data Acquisition Architecture

#### 2.4.1 RSS Feed Crawler
```python
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class RSSCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'XU-News-AI-RAG/1.0 (+https://example.com/bot-info)'
        })
        
    def fetch_feed(self, feed_url: str) -> Optional[Dict]:
        """Fetch and parse RSS feed"""
        try:
            response = self.session.get(feed_url, timeout=30)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"Feed {feed_url} has parsing issues: {feed.bozo_exception}")
            
            return feed
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_url}: {e}")
            return None
    
    def extract_articles(self, feed: Dict, since: Optional[datetime] = None) -> List[Dict]:
        """Extract articles from parsed feed"""
        articles = []
        
        if since is None:
            since = datetime.now() - timedelta(days=1)  # Default to last 24 hours
        
        for entry in feed.entries:
            try:
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                
                # Skip old articles
                if pub_date and pub_date < since:
                    continue
                
                # Extract content
                content = ""
                if hasattr(entry, 'content'):
                    content = entry.content[0].value
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                
                # Clean HTML from content
                content = self.clean_html(content)
                
                article = {
                    'title': entry.title,
                    'content': content,
                    'source_url': entry.link,
                    'published_date': pub_date,
                    'source_type': 'rss',
                    'author': getattr(entry, 'author', ''),
                    'source_name': feed.feed.get('title', ''),
                    'summary': getattr(entry, 'summary', '')[:500] if hasattr(entry, 'summary') else ''
                }
                
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Failed to process entry: {e}")
                continue
        
        return articles
    
    def clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract text"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text and clean whitespace
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
```

#### 2.4.2 Web Scraper
```python
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class NewsSpider(scrapy.Spider):
    name = 'news_spider'
    
    def __init__(self, urls=None, *args, **kwargs):
        super(NewsSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls if urls else []
        
        # Setup Selenium WebDriver for JavaScript-heavy sites
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def parse(self, response):
        """Parse article page"""
        try:
            # Extract article content using multiple selectors
            title_selectors = [
                'h1',
                '.headline',
                '.title',
                '[class*="title"]',
                '[class*="headline"]'
            ]
            
            content_selectors = [
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                '[class*="article"]',
                '[class*="content"]'
            ]
            
            # Extract title
            title = None
            for selector in title_selectors:
                title_element = response.css(selector + '::text').get()
                if title_element:
                    title = title_element.strip()
                    break
            
            # Extract content
            content = None
            for selector in content_selectors:
                content_elements = response.css(selector + ' p::text').getall()
                if content_elements:
                    content = ' '.join(content_elements)
                    break
            
            # Extract metadata
            published_date = response.css('time::attr(datetime)').get()
            author = response.css('.author::text').get()
            
            if title and content:
                yield {
                    'title': title,
                    'content': content,
                    'source_url': response.url,
                    'published_date': published_date,
                    'author': author,
                    'source_type': 'web_scraping'
                }
        
        except Exception as e:
            self.logger.error(f"Failed to parse {response.url}: {e}")
    
    def closed(self, reason):
        """Clean up WebDriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()

class WebScrapingService:
    def __init__(self):
        self.process = None
        
    def scrape_urls(self, urls: List[str]) -> List[Dict]:
        """Scrape articles from list of URLs"""
        settings = get_project_settings()
        settings.update({
            'ROBOTSTXT_OBEY': True,
            'DOWNLOAD_DELAY': 1,
            'RANDOMIZE_DOWNLOAD_DELAY': True,
            'CONCURRENT_REQUESTS': 1,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        })
        
        process = CrawlerProcess(settings)
        
        # Collect results
        results = []
        
        def collect_results(item, response, spider):
            results.append(item)
        
        # Connect signal
        from scrapy import signals
        from pydispatch import dispatcher
        dispatcher.connect(collect_results, signal=signals.item_scraped)
        
        # Run spider
        process.crawl(NewsSpider, urls=urls)
        process.start()
        
        return results
```

#### 2.4.3 Background Task & Scheduler Service (Actual Implementation)
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from concurrent.futures import ThreadPoolExecutor
import threading

# Global background executor for async operations (content.py)
_background_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='vector-cleanup')

class SchedulerService:
    def __init__(self, app, db, ai_pipeline):
        self.app = app
        self.db = db
        self.ai_pipeline = ai_pipeline
        self.scheduler = BackgroundScheduler()
        self.rss_crawler = RSSCrawler()
        self.web_scraper = WebScrapingService()
        
    def start(self):
        """Start the scheduler"""
        # Schedule RSS feed updates every 30 minutes
        self.scheduler.add_job(
            func=self.update_rss_feeds,
            trigger=IntervalTrigger(minutes=30),
            id='rss_update',
            name='Update RSS feeds',
            replace_existing=True
        )
        
        # Schedule web scraping daily at 2 AM
        self.scheduler.add_job(
            func=self.run_web_scraping,
            trigger=CronTrigger(hour=2, minute=0),
            id='web_scraping',
            name='Daily web scraping',
            replace_existing=True
        )
        
        # Schedule database cleanup weekly
        self.scheduler.add_job(
            func=self.cleanup_old_data,
            trigger=CronTrigger(day_of_week=0, hour=3, minute=0),
            id='database_cleanup',
            name='Weekly database cleanup',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def update_rss_feeds(self):
        """Update all active RSS feeds"""
        with self.app.app_context():
            try:
                active_sources = Source.query.filter_by(
                    source_type='rss',
                    is_active=True
                ).all()
                
                for source in active_sources:
                    logger.info(f"Updating RSS feed: {source.name}")
                    
                    # Fetch feed
                    feed = self.rss_crawler.fetch_feed(source.url)
                    if not feed:
                        continue
                    
                    # Extract articles
                    articles = self.rss_crawler.extract_articles(feed)
                    
                    # Process articles
                    for article_data in articles:
                        self.process_article(article_data, source.user_id)
                
                self.db.session.commit()
                logger.info(f"RSS update completed. Processed {len(active_sources)} sources")
                
            except Exception as e:
                logger.error(f"RSS update failed: {e}")
                self.db.session.rollback()
    
    def process_article(self, article_data: Dict, user_id: int):
        """Process and store article"""
        try:
            # Check for duplicates
            existing = Document.query.filter_by(
                user_id=user_id,
                source_url=article_data.get('source_url')
            ).first()
            
            if existing:
                return
            
            # Create document
            document = Document(
                user_id=user_id,
                title=article_data['title'],
                content=article_data['content'],
                source_url=article_data.get('source_url'),
                source_type=article_data.get('source_type'),
                published_date=article_data.get('published_date'),
                summary=article_data.get('summary', '')
            )
            
            self.db.session.add(document)
            self.db.session.flush()  # Get document ID
            
            # Process with AI pipeline
            processed_docs = self.ai_pipeline.process_document(
                article_data['content'],
                {
                    'document_id': document.id,
                    'title': document.title,
                    'source_url': document.source_url,
                    'source_type': document.source_type
                }
            )
            
            # Add to vector store
            self.ai_pipeline.vector_store_manager.add_documents_to_store(
                str(user_id), processed_docs
            )
            
            # Send notification if enabled
            self.send_notification(user_id, document)
            
            logger.info(f"Processed article: {document.title}")
            
        except Exception as e:
            logger.error(f"Failed to process article: {e}")
            raise
    
    def send_notification(self, user_id: int, document: Document):
        """Send email notification for new content"""
        try:
            user = User.query.get(user_id)
            if not user or not user.email:
                return
            
            # TODO: Check user notification preferences
            
            from .notification_service import NotificationService
            notification_service = NotificationService()
            
            notification_service.send_new_content_notification(
                user.email,
                user.username,
                document
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

# Background Task Management (ThreadPoolExecutor Implementation)
def _remove_document_from_ai_pipeline_background(document_data, app_config, flask_app):
    """Schedule background vector cleanup task."""
    try:
        logging.info(f"[VECTOR_CLEANUP] Scheduling background cleanup for document {document_data.get('id')}")
        
        # Submit background task with Flask app context
        future = _background_executor.submit(
            _remove_document_from_ai_pipeline_sync, 
            document_data, 
            app_config,
            flask_app
        )
        
        logging.info(f"[VECTOR_CLEANUP] Background task scheduled successfully")
        return True
    except Exception as e:
        logging.error(f"[VECTOR_CLEANUP] Failed to schedule background task: {e}")
        return False

def cleanup_background_executor():
    """Cleanup function for application shutdown."""
    try:
        logging.info("Shutting down background vector cleanup executor...")
        _background_executor.shutdown(wait=True)
        logging.info("Background vector cleanup executor shutdown completed")
    except Exception as e:
        logging.error(f"Error shutting down background executor: {e}")

# Register cleanup on app shutdown
import atexit
atexit.register(cleanup_background_executor)
```

---

## 3. API Specification

### 3.1 Authentication API
```yaml
paths:
  /api/auth/register:
    post:
      summary: Register new user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                  minLength: 3
                  maxLength: 50
                email:
                  type: string
                  format: email
                password:
                  type: string
                  minLength: 8
              required:
                - username
                - email
                - password
      responses:
        201:
          description: User created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        400:
          description: Invalid input data
        409:
          description: User already exists

  /api/auth/login:
    post:
      summary: User login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                password:
                  type: string
              required:
                - username
                - password
      responses:
        200:
          description: Login successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        401:
          description: Invalid credentials

  /api/auth/refresh:
    post:
      summary: Refresh JWT token
      security:
        - BearerAuth: []
      responses:
        200:
          description: Token refreshed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokenResponse'
        401:
          description: Invalid or expired token

components:
  schemas:
    AuthResponse:
      type: object
      properties:
        access_token:
          type: string
        refresh_token:
          type: string
        user:
          $ref: '#/components/schemas/User'
    
    User:
      type: object
      properties:
        id:
          type: integer
        username:
          type: string
        email:
          type: string
        created_at:
          type: string
          format: date-time
        last_login:
          type: string
          format: date-time
```

### 3.2 Search API
```yaml
paths:
  /api/search/semantic:
    post:
      summary: Perform semantic search
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                  minLength: 1
                k:
                  type: integer
                  minimum: 1
                  maximum: 100
                  default: 10
                filters:
                  type: object
                  properties:
                    source_type:
                      type: string
                    date_from:
                      type: string
                      format: date
                    date_to:
                      type: string
                      format: date
                    tags:
                      type: array
                      items:
                        type: string
              required:
                - query
      responses:
        200:
          description: Search results
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      $ref: '#/components/schemas/SearchResult'
                  total:
                    type: integer
                  query_time:
                    type: number
                    format: float
                  has_external_results:
                    type: boolean

components:
  schemas:
    SearchResult:
      type: object
      properties:
        document_id:
          type: integer
        title:
          type: string
        content:
          type: string
        source_url:
          type: string
        source_type:
          type: string
        published_date:
          type: string
          format: date-time
        similarity_score:
          type: number
          format: float
        relevance_score:
          type: number
          format: float
        tags:
          type: array
          items:
            type: string
```

### 3.3 Content Management API
```yaml
paths:
  /api/documents:
    get:
      summary: List user documents
      security:
        - BearerAuth: []
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: per_page
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: source_type
          in: query
          schema:
            type: string
        - name: date_from
          in: query
          schema:
            type: string
            format: date
        - name: date_to
          in: query
          schema:
            type: string
            format: date
        - name: search
          in: query
          schema:
            type: string
      responses:
        200:
          description: Document list
          content:
            application/json:
              schema:
                type: object
                properties:
                  documents:
                    type: array
                    items:
                      $ref: '#/components/schemas/Document'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

    post:
      summary: Create new document
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                title:
                  type: string
                  minLength: 1
                  maxLength: 500
                content:
                  type: string
                  minLength: 1
                source_url:
                  type: string
                  format: uri
                tags:
                  type: array
                  items:
                    type: string
              required:
                - title
                - content
      responses:
        201:
          description: Document created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'

  /api/documents/{id}:
    get:
      summary: Get document by ID
      security:
        - BearerAuth: []
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        200:
          description: Document details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'
        404:
          description: Document not found

    put:
      summary: Update document
      security:
        - BearerAuth: []
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                title:
                  type: string
                  minLength: 1
                  maxLength: 500
                content:
                  type: string
                  minLength: 1
                tags:
                  type: array
                  items:
                    type: string
      responses:
        200:
          description: Document updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'

    delete:
      summary: Delete document
      security:
        - BearerAuth: []
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        204:
          description: Document deleted
        404:
          description: Document not found

components:
  schemas:
    Document:
      type: object
      properties:
        id:
          type: integer
        title:
          type: string
        content:
          type: string
        summary:
          type: string
        source_url:
          type: string
        source_type:
          type: string
        published_date:
          type: string
          format: date-time
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        tags:
          type: array
          items:
            type: string
    
    Pagination:
      type: object
      properties:
        page:
          type: integer
        per_page:
          type: integer
        total:
          type: integer
        pages:
          type: integer
        has_prev:
          type: boolean
        has_next:
          type: boolean
```

---

## 4. Deployment Configuration

### 4.1 Docker Configuration
```dockerfile
# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

```dockerfile
# Frontend Dockerfile
FROM node:18-alpine as build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Build application
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 4.2 Docker Compose Configuration
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - REACT_APP_API_URL=http://localhost:5000/api

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    depends_on:
      - db
      - ollama
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/xurag
      - OLLAMA_BASE_URL=http://ollama:11434
      - JWT_SECRET_KEY=your-secret-key
      - MAIL_SERVER=smtp.gmail.com
      - MAIL_PORT=587
      - MAIL_USERNAME=your-email@gmail.com
      - MAIL_PASSWORD=your-app-password
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=xurag
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"


  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_ORIGINS=*
    command: serve

  # Note: Background tasks and scheduling are handled within the main Flask application
  # using ThreadPoolExecutor and APScheduler - no separate containers needed

volumes:
  postgres_data:
  ollama_data:
```

### 4.3 Environment Configuration
```python
# config.py
import os
from datetime import timedelta

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Redis (for caching)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Background Tasks
    BACKGROUND_TASK_MAX_WORKERS = 4
    BACKGROUND_TASK_TIMEOUT = 300
    
    # Scheduler Configuration
    SCHEDULER_TIMEZONE = 'UTC'
    SCHEDULER_MAX_WORKERS = 2
    
    # AI Models
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL') or 'http://localhost:11434'
    EMBEDDINGS_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
    RERANKER_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
    LLM_MODEL = 'qwen3:4b'
    
    # File Storage
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'data/uploads'
    VECTOR_STORE_PATH = os.environ.get('VECTOR_STORE_PATH') or 'data/vector_stores'
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # External APIs
    GOOGLE_SEARCH_API_KEY = os.environ.get('GOOGLE_SEARCH_API_KEY')
    GOOGLE_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
    
    # Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
```

---

## 5. Testing Strategy

### 5.1 Backend Testing Architecture
```python
# conftest.py - pytest fixtures
import pytest
from app import create_app, db
from app.models import User, Document
from tests.factories import UserFactory, DocumentFactory

@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(client):
    """Create authenticated user and return headers"""
    user = UserFactory()
    db.session.add(user)
    db.session.commit()
    
    response = client.post('/api/auth/login', json={
        'username': user.username,
        'password': 'password'
    })
    
    token = response.json['access_token']
    return {'Authorization': f'Bearer {token}'}

# Test example
class TestAuthAPI:
    def test_user_registration(self, client):
        """Test user registration"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }
        
        response = client.post('/api/auth/register', json=data)
        assert response.status_code == 201
        assert 'access_token' in response.json
    
    def test_user_login(self, client):
        """Test user login"""
        # Create user
        user = UserFactory()
        db.session.add(user)
        db.session.commit()
        
        data = {
            'username': user.username,
            'password': 'password'
        }
        
        response = client.post('/api/auth/login', json=data)
        assert response.status_code == 200
        assert 'access_token' in response.json

class TestSearchAPI:
    def test_semantic_search(self, client, auth_headers):
        """Test semantic search functionality"""
        # Create test documents
        user_id = 1  # From auth_headers fixture
        docs = DocumentFactory.create_batch(5, user_id=user_id)
        db.session.add_all(docs)
        db.session.commit()
        
        data = {
            'query': 'test search query',
            'k': 3
        }
        
        response = client.post(
            '/api/search/semantic', 
            json=data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert 'results' in response.json
        assert len(response.json['results']) <= 3
```

### 5.2 Frontend Testing Architecture
```javascript
// setupTests.js
import '@testing-library/jest-dom';
import { server } from './mocks/server';

// Mock API server setup
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Component test example
// components/__tests__/SearchInterface.test.js
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import SearchInterface from '../SearchInterface';
import searchSlice from '../../store/slices/searchSlice';

const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      search: searchSlice.reducer,
    },
    preloadedState: initialState,
  });
};

describe('SearchInterface', () => {
  test('renders search input and button', () => {
    const store = createTestStore();
    
    render(
      <Provider store={store}>
        <SearchInterface />
      </Provider>
    );
    
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
  });
  
  test('performs search when form is submitted', async () => {
    const store = createTestStore();
    
    render(
      <Provider store={store}>
        <SearchInterface />
      </Provider>
    );
    
    const searchInput = screen.getByPlaceholderText(/search/i);
    const searchButton = screen.getByRole('button', { name: /search/i });
    
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    fireEvent.click(searchButton);
    
    await waitFor(() => {
      expect(screen.getByText(/searching/i)).toBeInTheDocument();
    });
  });
});
```

### 5.3 Integration Testing
```python
# tests/integration/test_ai_pipeline.py
import pytest
from app.ai.langchain_service import AIProcessingPipeline
from app.models import User, Document

class TestAIPipeline:
    @pytest.fixture
    def ai_pipeline(self):
        return AIProcessingPipeline()
    
    def test_document_processing_workflow(self, ai_pipeline, app):
        """Test complete document processing workflow"""
        with app.app_context():
            # Create test user
            user = User(username='testuser', email='test@example.com')
            db.session.add(user)
            db.session.flush()
            
            # Test document content
            content = "This is a test document about artificial intelligence and machine learning."
            metadata = {
                'title': 'Test Document',
                'source_type': 'manual',
                'user_id': user.id
            }
            
            # Process document
            processed_docs = ai_pipeline.process_document(content, metadata)
            
            # Verify processing
            assert len(processed_docs) > 0
            assert all(doc.metadata['user_id'] == user.id for doc in processed_docs)
            
            # Test vector store creation
            vector_store = ai_pipeline.create_vector_store(processed_docs, str(user.id))
            assert vector_store is not None
            
            # Test semantic search
            results = ai_pipeline.semantic_search("artificial intelligence", str(user.id), k=5)
            assert len(results) > 0
            assert any("artificial intelligence" in doc.page_content.lower() for doc in results)
```

---

## 6. Security Implementation

### 6.1 Authentication & Authorization
```python
# utils/security.py
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import bcrypt
import re

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def require_user_ownership(f):
    """Decorator to ensure user can only access their own resources"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        current_user_id = get_jwt_identity()
        
        # Extract user_id from request (URL param, JSON body, etc.)
        user_id = None
        
        # Check URL parameters
        if 'user_id' in kwargs:
            user_id = kwargs['user_id']
        
        # Check if accessing document - verify ownership
        if 'id' in kwargs:
            from app.models import Document
            doc = Document.query.get(kwargs['id'])
            if doc:
                user_id = doc.user_id
        
        if user_id and str(user_id) != str(current_user_id):
            return jsonify({'error': 'Unauthorized access'}), 403
        
        return f(*args, **kwargs)
    
    return decorated

def sanitize_input(data: dict, allowed_fields: list) -> dict:
    """Sanitize input data by removing disallowed fields"""
    return {k: v for k, v in data.items() if k in allowed_fields}

def validate_file_upload(file):
    """Validate uploaded file"""
    if not file or file.filename == '':
        return False, "No file provided"
    
    # Check file size
    if len(file.read()) > current_app.config['MAX_CONTENT_LENGTH']:
        return False, "File too large"
    
    file.seek(0)  # Reset file pointer
    
    # Check file type
    allowed_extensions = {'txt', 'pdf', 'doc', 'docx', 'html', 'json', 'csv'}
    file_extension = file.filename.rsplit('.', 1)[-1].lower()
    
    if file_extension not in allowed_extensions:
        return False, f"File type {file_extension} not allowed"
    
    return True, "File is valid"
```

### 6.2 Input Validation & Sanitization
```python
# utils/validators.py
from marshmallow import Schema, fields, validate, ValidationError
from bs4 import BeautifulSoup
import html

class UserRegistrationSchema(Schema):
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error='Username contains invalid characters')
        ]
    )
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))

class DocumentSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    content = fields.Str(required=True, validate=validate.Length(min=1))
    source_url = fields.Url(allow_none=True)
    tags = fields.List(fields.Str(validate=validate.Length(max=50)), missing=[])

class SearchSchema(Schema):
    query = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    k = fields.Int(missing=10, validate=validate.Range(min=1, max=100))
    filters = fields.Dict(missing={})

def sanitize_html_content(content: str) -> str:
    """Remove potentially dangerous HTML content"""
    # Parse HTML
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove script and style tags
    for tag in soup(['script', 'style', 'meta', 'link']):
        tag.decompose()
    
    # Remove dangerous attributes
    dangerous_attrs = ['onload', 'onclick', 'onmouseover', 'onfocus', 'onerror']
    for tag in soup.find_all():
        for attr in dangerous_attrs:
            if attr in tag.attrs:
                del tag.attrs[attr]
    
    # Get clean text
    clean_text = soup.get_text(separator=' ', strip=True)
    
    # HTML escape the result
    return html.escape(clean_text)

def validate_search_query(query: str) -> bool:
    """Validate search query for potential injection attacks"""
    # Check for SQL injection patterns
    sql_patterns = [
        'union select', 'drop table', 'delete from', 'insert into',
        'update set', '--', ';', 'xp_', 'sp_'
    ]
    
    query_lower = query.lower()
    for pattern in sql_patterns:
        if pattern in query_lower:
            return False
    
    return True
```

---

## 7. Performance Optimization

### 7.1 Caching Strategy (Actual Implementation)

Our system uses **in-memory caching** instead of Redis for simplicity and to avoid external dependencies:

```python
# Actual caching implementations used in the project

# 1. Vector Store Caching (ai/vector_store.py) 
class VectorStoreManager:
    def __init__(self, embeddings_model):
        self.stores = {}  # In-memory cache for loaded stores
        
    def load_user_store(self, user_id: str):
        # Check cache first
        if user_id in self.stores:
            return self.stores[user_id]
        # Load and cache
        store = self._load_from_disk(user_id)
        self.stores[user_id] = store  # Cache it
        return store

# 2. JWT Blacklist (api/auth.py)
blacklisted_tokens = set()  # In-memory set for revoked tokens

def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return jti in blacklisted_tokens

# 3. Rate Limiting (utils/decorators.py) 
request_counts = {}  # In-memory dict with timestamps

def rate_limit(max_requests: int = 100, window: int = 3600):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            client_ip = request.remote_addr
            now = time.time()
            
            # Clean old entries and check rate
            if client_ip in request_counts:
                # Filter recent requests
                recent_requests = [t for t in request_counts[client_ip] 
                                 if now - t < window]
                request_counts[client_ip] = recent_requests
            else:
                request_counts[client_ip] = []
                
            # Check rate limit
            if len(request_counts[client_ip]) >= max_requests:
                return {'error': 'Rate limit exceeded'}, 429
                
            # Add current request
            request_counts[client_ip].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator

# 4. Model Caching (ai/embeddings.py)
class EmbeddingsManager:
    def __init__(self):
        self.model = None  # Cached model instance
        
    def get_embeddings_model(self, model_name: str):
        if self.model is None:
            # File-based caching via HuggingFace
            cache_folder = current_app.config.get('EMBEDDINGS_MODEL_CACHE_FOLDER')
            self.model = SentenceTransformer(model_name, cache_folder=cache_folder)
        return self.model

# 5. Web Scraper Robots.txt Cache (crawlers/web_scraper.py)
class WebScraper:
    def __init__(self):
        self.robots_cache = {}  # In-memory robots.txt cache
        
    def can_fetch(self, url: str, user_agent: str = '*'):
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Check cache first
        if base_url in self.robots_cache:
            rp = self.robots_cache[base_url]
        else:
            # Load and cache robots.txt
            rp = RobotFileParser()
            rp.set_url(f"{base_url}/robots.txt")
            rp.read()
            self.robots_cache[base_url] = rp  # Cache it
        
        return rp.can_fetch(user_agent, url)
```

#### Caching Types Used:
- **In-Memory Dictionaries**: Fast access for frequently used data
- **File-Based Model Cache**: HuggingFace transformers cache models locally
- **Python Sets**: Efficient for blacklisted tokens
- **Time-based Cleanup**: Automatic cleanup of expired entries

#### Benefits:
- ✅ **Zero Dependencies**: No external cache servers needed
- ✅ **Simple Deployment**: Everything runs in the Flask process
- ✅ **Fast Access**: In-memory access is very fast
- ✅ **Automatic Cleanup**: Built-in garbage collection

#### Limitations & Production Considerations:
- ❌ **Memory Usage**: All cache data stored in RAM
- ❌ **Single Instance**: Cache not shared between multiple app instances
- ❌ **No Persistence**: Cache lost on app restart

**Production Recommendation**: For scaling beyond single instance, implement Redis or Memcached for shared caching.

### 7.2 Database Optimization
```python
# Database optimization strategies
from sqlalchemy import event, Index
from sqlalchemy.engine import Engine
import time
import logging

# Query logging for performance monitoring
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # Log slow queries (>100ms)
        logging.warning(f"Slow query: {total:.2f}s - {statement[:100]}...")

# Optimized queries with proper indexing
class OptimizedQueries:
    @staticmethod
    def get_user_documents_paginated(user_id: int, page: int, per_page: int, filters: dict):
        """Optimized document retrieval with filters"""
        query = Document.query.filter_by(user_id=user_id)
        
        # Apply filters
        if filters.get('source_type'):
            query = query.filter(Document.source_type == filters['source_type'])
        
        if filters.get('date_from'):
            query = query.filter(Document.published_date >= filters['date_from'])
        
        if filters.get('date_to'):
            query = query.filter(Document.published_date <= filters['date_to'])
        
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            query = query.filter(
                db.or_(
                    Document.title.ilike(search_term),
                    Document.content.ilike(search_term)
                )
            )
        
        # Order by most recent first
        query = query.order_by(Document.created_at.desc())
        
        # Paginate
        return query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False,
            max_per_page=100
        )
    
    @staticmethod
    def get_user_search_history(user_id: int, limit: int = 10):
        """Get recent search history for user"""
        return SearchHistory.query.filter_by(user_id=user_id)\
            .order_by(SearchHistory.created_at.desc())\
            .limit(limit)\
            .all()

# Database indexes for performance
# Add these to your models or migration files
"""
CREATE INDEX idx_documents_user_id_created_at ON documents(user_id, created_at DESC);
CREATE INDEX idx_documents_user_id_source_type ON documents(user_id, source_type);
CREATE INDEX idx_documents_user_id_published_date ON documents(user_id, published_date);
CREATE INDEX idx_documents_title_content_gin ON documents USING gin(to_tsvector('english', title || ' ' || content));
CREATE INDEX idx_search_history_user_id_created_at ON search_history(user_id, created_at DESC);
"""
```

### 7.3 AI Model Optimization
```python
# ai/optimizations.py
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from typing import List, Dict, Any

class ModelManager:
    """Singleton pattern for managing AI models"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.models = {}
            self.executor = ThreadPoolExecutor(max_workers=4)
            self.initialized = True
    
    def get_model(self, model_name: str):
        """Get or load model with caching"""
        if model_name not in self.models:
            self.models[model_name] = self._load_model(model_name)
        return self.models[model_name]
    
    def _load_model(self, model_name: str):
        """Load model based on name"""
        if model_name == 'embeddings':
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer('all-MiniLM-L6-v2')
        elif model_name == 'reranker':
            from sentence_transformers import CrossEncoder
            return CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        # Add other models as needed

class BatchProcessor:
    """Efficient batch processing for embeddings"""
    
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self.model_manager = ModelManager()
    
    def generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings in batches for efficiency"""
        model = self.model_manager.get_model('embeddings')
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = model.encode(
                batch,
                batch_size=len(batch),
                show_progress_bar=False,
                convert_to_numpy=True
            )
            all_embeddings.append(batch_embeddings)
        
        return np.vstack(all_embeddings) if all_embeddings else np.array([])
    
    def rerank_batch(self, query: str, documents: List[str]) -> List[float]:
        """Batch reranking for efficiency"""
        model = self.model_manager.get_model('reranker')
        
        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]
        
        # Score in batches
        scores = model.predict(pairs, batch_size=self.batch_size)
        
        return scores.tolist()

class VectorStoreOptimizer:
    """Optimize vector store operations"""
    
    @staticmethod
    def optimize_faiss_index(index, nlist: int = 100):
        """Optimize FAISS index for faster searching"""
        import faiss
        
        # Convert to IVF (Inverted File) index for faster search
        if index.ntotal > 1000:  # Only for larger datasets
            quantizer = faiss.IndexFlatL2(index.d)
            ivf_index = faiss.IndexIVFFlat(quantizer, index.d, nlist)
            
            # Train the index
            vectors = index.reconstruct_n(0, index.ntotal)
            ivf_index.train(vectors)
            ivf_index.add(vectors)
            
            return ivf_index
        
        return index
    
    @staticmethod
    def compress_embeddings(embeddings: np.ndarray, target_dim: int = 256):
        """Compress embeddings using PCA for storage efficiency"""
        from sklearn.decomposition import PCA
        
        if embeddings.shape[1] > target_dim:
            pca = PCA(n_components=target_dim)
            compressed = pca.fit_transform(embeddings)
            return compressed, pca
        
        return embeddings, None
```

---

## Conclusion

This technical architecture document provides a comprehensive blueprint for implementing the XU-News-AI-RAG Personalized News Intelligent Knowledge Base. The architecture emphasizes:

1. **Scalability**: Modular design with microservices-inspired architecture
2. **Performance**: Optimized AI models, caching strategies, and database indexing
3. **Security**: Comprehensive authentication, input validation, and data protection
4. **Maintainability**: Clear separation of concerns and extensive testing strategies
5. **Reliability**: Fault-tolerant design with monitoring and backup procedures

The implementation follows industry best practices and provides a solid foundation for building a production-ready AI-powered knowledge management system. Regular reviews and updates of this architecture will ensure it continues to meet evolving requirements and incorporates new technological advances.

---
