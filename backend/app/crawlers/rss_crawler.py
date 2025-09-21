"""
RSS Feed Crawler for automated news collection.
"""
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import feedparser
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import hashlib
import re

from app import db
from app.models import Document, Source
from app.utils.validators import sanitize_html_content, validate_url
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class RSSCrawler:
    """
    RSS Feed Crawler with intelligent content extraction and processing.
    """
    
    def __init__(self, config=None):
        """
        Initialize RSS Crawler.
        
        Args:
            config: Configuration dictionary with crawler settings
        """
        self.config = config or {}
        self.user_agent = self.config.get(
            'CRAWLER_USER_AGENT', 
            'XU-News-AI-RAG-Bot/1.0'
        )
        self.delay = self.config.get('CRAWLER_DELAY', 1)  # seconds between requests
        self.timeout = self.config.get('CRAWLER_TIMEOUT', 30)  # request timeout
        self.max_retries = 3
        self.email_service = EmailService(config)
        self._ai_pipeline = None  # Lazy initialization
        
        # Headers for HTTP requests
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/rss+xml, application/xml, text/xml, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        }
        
        logger.info("RSS Crawler initialized")
    
    def _get_ai_pipeline(self):
        """
        Get or create AI processing pipeline for document processing.
        Uses lazy initialization to avoid loading AI models during crawler initialization.
        
        Returns:
            LangChainService instance or None if initialization fails
        """
        if self._ai_pipeline is None:
            try:
                from app.ai.langchain_service import LangChainService
                
                # Use configuration from crawler config or defaults
                ai_config = {
                    'EMBEDDINGS_MODEL': self.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
                    'VECTOR_STORE_PATH': self.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
                    'LLM_MODEL': self.config.get('LLM_MODEL', 'qwen3:4b'),
                    'OLLAMA_BASE_URL': self.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
                    'RERANKER_MODEL': self.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                }
                
                self._ai_pipeline = LangChainService(config=ai_config)
                logger.info("AI processing pipeline initialized for crawler")
                
            except Exception as e:
                logger.error(f"Failed to initialize AI pipeline for crawler: {e}")
                self._ai_pipeline = None
        
        return self._ai_pipeline
    
    def crawl_source(self, source: Source) -> Tuple[bool, int, Optional[str]]:
        """
        Crawl a single RSS source and extract articles.
        
        Args:
            source: Source model instance to crawl
            
        Returns:
            Tuple of (success, articles_count, error_message)
        """
        try:
            logger.info(f"Starting crawl for source: {source.name} ({source.url})")
            
            # Validate source URL
            is_valid, validation_message = validate_url(source.url)
            if not is_valid:
                error_msg = f"Invalid source URL: {validation_message}"
                logger.error(error_msg)
                return False, 0, error_msg
            
            # Fetch and parse RSS feed
            feed_data = self._fetch_rss_feed(source.url)
            if not feed_data:
                error_msg = "Failed to fetch RSS feed"
                logger.error(error_msg)
                return False, 0, error_msg
            
            # Parse feed
            feed = feedparser.parse(feed_data)
            if feed.bozo and not feed.entries:
                error_msg = f"Invalid RSS feed format: {getattr(feed, 'bozo_exception', 'Unknown error')}"
                logger.error(error_msg)
                return False, 0, error_msg
            
            # Process entries
            articles_processed = 0
            max_articles = source.crawl_settings.get('max_articles_per_crawl', 5)
            
            for entry in feed.entries[:max_articles]:
                try:
                    if self._process_rss_entry(entry, source):
                        articles_processed += 1
                    
                    # Rate limiting
                    if self.delay > 0:
                        time.sleep(self.delay)
                        
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {e}")
                    continue
            
            # Update source statistics
            source.update_crawl_stats(
                success=True,
                articles_count=articles_processed,
                error=None
            )
            
            # Send email notification if configured and articles were found
            if articles_processed > 0 and source.crawl_settings.get('email_notifications', True):
                self._send_notification_email(source, articles_processed)
            
            logger.info(f"Successfully crawled {articles_processed} articles from {source.name}")
            return True, articles_processed, None
            
        except Exception as e:
            error_msg = f"Crawling failed for {source.name}: {str(e)}"
            logger.error(error_msg)
            source.update_crawl_stats(success=False, error=error_msg)
            return False, 0, error_msg
    
    def _fetch_rss_feed(self, url: str) -> Optional[str]:
        """
        Fetch RSS feed content with retries and error handling.
        
        Args:
            url: RSS feed URL
            
        Returns:
            Feed content as string or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Fetching RSS feed: {url} (attempt {attempt + 1})")
                
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=True
                )
                
                # Check response status
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 304:
                    logger.info(f"RSS feed not modified: {url}")
                    return None
                elif response.status_code in [403, 429]:
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    logger.warning(f"Rate limited or forbidden, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error for {url} (attempt {attempt + 1})")
                time.sleep(2 ** attempt)
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break
        
        return None
    
    def _process_rss_entry(self, entry, source: Source) -> bool:
        """
        Process a single RSS entry and create document.
        
        Args:
            entry: RSS feed entry from feedparser
            source: Source model instance
            
        Returns:
            True if article was processed and created, False otherwise
        """
        try:
            # Extract basic information
            title = self._clean_text(getattr(entry, 'title', ''))
            link = getattr(entry, 'link', '')
            
            if not title or not link:
                logger.debug("Skipping entry with missing title or link")
                return False
            
            # Check if article already exists (using URL hash)
            url_hash = hashlib.md5(link.encode()).hexdigest()
            existing_doc = Document.query.filter_by(
                user_id=source.user_id,
                vector_id=f"rss_{source.id}_{url_hash}"
            ).first()
            
            if existing_doc:
                logger.debug(f"Article already exists: {title}")
                return False
            
            # Extract content
            content = self._extract_content(entry, link, source)
            if not content or len(content) < 100:  # Skip very short articles
                logger.debug(f"Skipping article with insufficient content: {title}")
                return False
            
            # Extract metadata
            published_date = self._extract_published_date(entry)
            author = self._extract_author(entry)
            summary = self._extract_summary(entry, content)
            
            # Generate tags
            tags = self._generate_tags(entry, source, title, content)
            
            # Create document
            document = Document.create_document(
                user_id=source.user_id,
                title=title,
                content=content,
                summary=summary,
                source_url=link,
                source_type='rss',
                source_name=source.name,
                author=author,
                published_date=published_date,
                tags=tags,
                vector_id=f"rss_{source.id}_{url_hash}"
            )
            
            # Process document through AI pipeline for semantic search
            try:
                ai_pipeline = self._get_ai_pipeline()
                if ai_pipeline:
                    success = ai_pipeline.process_document(document)
                    if success:
                        logger.info(f"Document processed through AI pipeline: {title}")
                    else:
                        logger.warning(f"Failed to process document through AI pipeline: {title}")
                else:
                    logger.warning("AI pipeline not available, document not processed for semantic search")
            except Exception as e:
                logger.error(f"Error processing document through AI pipeline: {e}")
                # Don't fail the entire crawling process if AI processing fails
            
            logger.info(f"Created document: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing RSS entry: {e}")
            return False
    
    def _extract_content(self, entry, link: str, source: Source) -> Optional[str]:
        """
        Extract full content from RSS entry, with fallback to web scraping.
        
        Args:
            entry: RSS feed entry
            link: Article URL
            source: Source configuration
            
        Returns:
            Extracted content or None
        """
        # Try to get content from RSS entry first
        content = ""
        
        # Check various content fields in RSS
        content_fields = ['content', 'summary', 'description']
        for field in content_fields:
            if hasattr(entry, field):
                field_content = getattr(entry, field)
                if isinstance(field_content, list) and field_content:
                    field_content = field_content[0].value if hasattr(field_content[0], 'value') else str(field_content[0])
                elif hasattr(field_content, 'value'):
                    field_content = field_content.value
                else:
                    field_content = str(field_content) if field_content else ""
                
                if field_content and len(field_content) > len(content):
                    content = field_content
        
        # Clean HTML content
        content = sanitize_html_content(content) if content else ""
        
        # If content is insufficient, try web scraping
        if len(content) < 200 and source.crawl_settings.get('extract_content', True):
            try:
                scraped_content = self._scrape_full_content(link)
                if scraped_content and len(scraped_content) > len(content):
                    content = scraped_content
            except Exception as e:
                logger.debug(f"Failed to scrape full content from {link}: {e}")
        
        return content if len(content) >= 100 else None
    
    def _scrape_full_content(self, url: str) -> Optional[str]:
        """
        Scrape full article content from URL.
        
        Args:
            url: Article URL
            
        Returns:
            Scraped content or None
        """
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Try to find main content using common selectors
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                'main',
                '.main-content',
                '#main-content',
                '.story-body',
                '.article-body'
            ]
            
            content = None
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator=' ', strip=True)
                    if len(content) > 200:  # Found substantial content
                        break
            
            # Fallback to body content
            if not content or len(content) < 200:
                body = soup.find('body')
                if body:
                    content = body.get_text(separator=' ', strip=True)
            
            # Clean up content
            if content:
                # Remove extra whitespace
                content = re.sub(r'\s+', ' ', content).strip()
                # Remove common footer text
                content = re.sub(r'(subscribe|newsletter|follow us).*$', '', content, flags=re.IGNORECASE)
                
            return content if content and len(content) >= 100 else None
            
        except Exception as e:
            logger.debug(f"Error scraping content from {url}: {e}")
            return None
    
    def _extract_published_date(self, entry) -> Optional[datetime]:
        """Extract published date from RSS entry."""
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        return datetime(*time_struct[:6], tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        continue
        
        # Try string date fields
        string_date_fields = ['published', 'updated', 'created']
        for field in string_date_fields:
            if hasattr(entry, field):
                date_string = getattr(entry, field)
                if date_string:
                    try:
                        from dateutil import parser
                        return parser.parse(date_string).replace(tzinfo=timezone.utc)
                    except Exception:
                        continue
        
        return None
    
    def _extract_author(self, entry) -> Optional[str]:
        """Extract author from RSS entry."""
        author_fields = ['author', 'creator', 'publisher']
        
        for field in author_fields:
            if hasattr(entry, field):
                author = getattr(entry, field)
                if author:
                    return self._clean_text(str(author))
        
        return None
    
    def _extract_summary(self, entry, content: str) -> Optional[str]:
        """Extract or generate summary from RSS entry."""
        # Try to get summary from RSS first
        if hasattr(entry, 'summary'):
            summary = sanitize_html_content(entry.summary)
            if summary and len(summary) > 50:
                return summary[:500]  # Limit summary length
        
        # Generate summary from content
        if content:
            sentences = content.split('.')[:3]  # First 3 sentences
            summary = '. '.join(sentences)
            if summary:
                return summary[:500]
        
        return None
    
    def _generate_tags(self, entry, source: Source, title: str, content: str) -> List[str]:
        """Generate tags for the article."""
        tags = []
        
        # Add auto-tags from source configuration
        if source.auto_tags:
            tags.extend(source.auto_tags)
        
        # Extract tags from RSS entry
        if hasattr(entry, 'tags'):
            entry_tags = entry.tags
            if isinstance(entry_tags, list):
                for tag in entry_tags:
                    if hasattr(tag, 'term'):
                        tags.append(tag.term.lower())
                    else:
                        tags.append(str(tag).lower())
        
        # Simple keyword extraction (in real implementation, use NLP)
        keywords = self._extract_keywords(title + " " + content[:500])
        tags.extend(keywords[:5])  # Add top 5 keywords
        
        # Clean and deduplicate tags
        clean_tags = []
        seen_tags = set()
        for tag in tags:
            clean_tag = re.sub(r'[^a-zA-Z0-9\s-]', '', str(tag)).strip().lower()
            if clean_tag and len(clean_tag) > 2 and clean_tag not in seen_tags:
                clean_tags.append(clean_tag)
                seen_tags.add(clean_tag)
        
        return clean_tags[:10]  # Limit to 10 tags
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Simple keyword extraction (placeholder for more sophisticated NLP)."""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our',
            'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its'
        }
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_freq = {}
        
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top words by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words if freq > 1][:10]
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove HTML entities
        text = BeautifulSoup(text, 'html.parser').get_text()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _send_notification_email(self, source: Source, articles_count: int):
        """Send email notification about successful crawling."""
        try:
            if self.email_service:
                subject = f"XU-News-AI-RAG: New articles from {source.name}"
                body = f"""
                Hello,
                
                We've successfully collected {articles_count} new articles from your RSS source "{source.name}".
                
                Source URL: {source.url}
                Articles collected: {articles_count}
                Last crawled: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                You can view and search these articles in your knowledge base at your XU-News-AI-RAG dashboard.
                
                Best regards,
                XU-News-AI-RAG System
                """
                
                user = source.owner  # Assuming the relationship exists
                if user and user.email:
                    self.email_service.send_email(
                        to_email=user.email,
                        subject=subject,
                        body=body
                    )
                    logger.info(f"Sent notification email to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
    
    def crawl_all_due_sources(self, user_id: Optional[int] = None) -> Dict[str, int]:
        """
        Crawl all sources that are due for crawling.
        
        Args:
            user_id: Optional user ID to limit crawling to specific user
            
        Returns:
            Dictionary with crawling statistics
        """
        try:
            # Get sources that are due for crawling
            due_sources = Source.get_due_sources(user_id)
            
            stats = {
                'total_sources': len(due_sources),
                'successful': 0,
                'failed': 0,
                'total_articles': 0,
                'errors': []
            }
            
            for source in due_sources:
                success, articles_count, error = self.crawl_source(source)
                
                if success:
                    stats['successful'] += 1
                    stats['total_articles'] += articles_count
                else:
                    stats['failed'] += 1
                    if error:
                        stats['errors'].append(f"{source.name}: {error}")
                
                # Rate limiting between sources
                if self.delay > 0:
                    time.sleep(self.delay)
            
            logger.info(f"Crawling completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in crawl_all_due_sources: {e}")
            return {
                'total_sources': 0,
                'successful': 0,
                'failed': 1,
                'total_articles': 0,
                'errors': [str(e)]
            }
