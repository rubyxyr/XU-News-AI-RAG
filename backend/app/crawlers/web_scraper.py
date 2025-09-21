"""
Web Scraper with robots.txt compliance and intelligent content extraction.
"""
import logging
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup, Comment
import re
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from app import db
from app.models import Document, Source
from app.utils.validators import sanitize_html_content, validate_url
from app.crawlers.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)


class WebScraper:
    """
    Intelligent web scraper with robots.txt compliance and content extraction.
    """
    
    def __init__(self, config=None):
        """
        Initialize Web Scraper.
        
        Args:
            config: Configuration dictionary with scraper settings
        """
        self.config = config or {}
        self.user_agent = self.config.get(
            'CRAWLER_USER_AGENT',
            'XU-News-AI-RAG-Bot/1.0 (+https://github.com/xu-news-ai-rag)'
        )
        self.delay = self.config.get('CRAWLER_DELAY', 1)
        self.timeout = self.config.get('CRAWLER_TIMEOUT', 30)
        self.respect_robots = self.config.get('CRAWLER_RESPECT_ROBOTS_TXT', True)
        self.max_retries = 3
        self.max_redirects = 5
        
        # Initialize proxy manager
        self.proxy_manager = ProxyManager(config)
        self._ai_pipeline = None  # Lazy initialization
        
        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Robots.txt cache
        self.robots_cache = {}
        
        logger.info("Web Scraper initialized")
    
    def _get_ai_pipeline(self):
        """
        Get or create AI processing pipeline for document processing.
        Uses lazy initialization to avoid loading AI models during scraper initialization.
        
        Returns:
            LangChainService instance or None if initialization fails
        """
        if self._ai_pipeline is None:
            try:
                from app.ai.langchain_service import LangChainService
                
                # Use configuration from scraper config or defaults
                ai_config = {
                    'EMBEDDINGS_MODEL': self.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
                    'VECTOR_STORE_PATH': self.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
                    'LLM_MODEL': self.config.get('LLM_MODEL', 'qwen3:4b'),
                    'OLLAMA_BASE_URL': self.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
                    'RERANKER_MODEL': self.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                }
                
                self._ai_pipeline = LangChainService(config=ai_config)
                logger.info("AI processing pipeline initialized for web scraper")
                
            except Exception as e:
                logger.error(f"Failed to initialize AI pipeline for web scraper: {e}")
                self._ai_pipeline = None
        
        return self._ai_pipeline
    
    def scrape_url(self, url: str, source: Optional[Source] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Scrape content from a single URL.
        
        Args:
            url: URL to scrape
            source: Optional source configuration
            
        Returns:
            Tuple of (success, scraped_data, error_message)
        """
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Validate URL
            is_valid, validation_message = validate_url(url)
            if not is_valid:
                return False, None, f"Invalid URL: {validation_message}"
            
            # Check robots.txt compliance
            if self.respect_robots and not self._check_robots_permission(url):
                error_msg = "Scraping not allowed by robots.txt"
                logger.warning(f"{error_msg}: {url}")
                return False, None, error_msg
            
            # Get proxy if available
            proxy = self.proxy_manager.get_proxy() if self.proxy_manager else None
            
            # Fetch page content
            response = self._fetch_page(url, proxy)
            if not response:
                return False, None, "Failed to fetch page"
            
            # Parse and extract content
            scraped_data = self._extract_page_content(response, url, source)
            if not scraped_data:
                return False, None, "Failed to extract content"
            
            logger.info(f"Successfully scraped: {scraped_data.get('title', url)}")
            return True, scraped_data, None
            
        except Exception as e:
            error_msg = f"Scraping failed for {url}: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def _check_robots_permission(self, url: str) -> bool:
        """
        Check if scraping is allowed by robots.txt.
        
        Args:
            url: URL to check
            
        Returns:
            True if scraping is allowed, False otherwise
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check cache first
            if base_url in self.robots_cache:
                rp = self.robots_cache[base_url]
            else:
                # Fetch and parse robots.txt
                robots_url = urljoin(base_url, '/robots.txt')
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                try:
                    rp.read()
                    self.robots_cache[base_url] = rp
                except Exception as e:
                    logger.debug(f"Could not read robots.txt from {robots_url}: {e}")
                    # If we can't read robots.txt, assume scraping is allowed
                    return True
            
            # Check permission
            return rp.can_fetch(self.user_agent, url)
            
        except Exception as e:
            logger.debug(f"Error checking robots.txt for {url}: {e}")
            # If there's an error, assume scraping is allowed
            return True
    
    def _fetch_page(self, url: str, proxy: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Fetch page content with retries and error handling.
        
        Args:
            url: URL to fetch
            proxy: Optional proxy configuration
            
        Returns:
            Response object or None if failed
        """
        proxies = {'http': proxy['url'], 'https': proxy['url']} if proxy else None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Fetching page: {url} (attempt {attempt + 1})")
                
                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    proxies=proxies,
                    verify=True
                )
                
                # Check response status
                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 429]:
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"Rate limited or forbidden, waiting {wait_time}s")
                    
                    # Try different proxy if available
                    if self.proxy_manager:
                        proxy = self.proxy_manager.get_proxy()
                        proxies = {'http': proxy['url'], 'https': proxy['url']} if proxy else None
                    
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                time.sleep(2 ** attempt)
                continue
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error for {url} (attempt {attempt + 1})")
                time.sleep(2 ** attempt)
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break
        
        return None
    
    def _extract_page_content(self, response: requests.Response, url: str, source: Optional[Source] = None) -> Optional[Dict]:
        """
        Extract structured content from HTML response.
        
        Args:
            response: HTTP response object
            url: Original URL
            source: Optional source configuration
            
        Returns:
            Dictionary with extracted content or None
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            self._clean_soup(soup)
            
            # Extract title
            title = self._extract_title(soup, url)
            if not title:
                logger.debug(f"No title found for {url}")
                return None
            
            # Extract main content
            content = self._extract_main_content(soup, source)
            if not content or len(content) < 200:
                logger.debug(f"Insufficient content found for {url}")
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(soup, response)
            
            # Extract links
            links = self._extract_links(soup, url)
            
            # Generate summary
            summary = self._generate_summary(content)
            
            return {
                'title': title,
                'content': content,
                'summary': summary,
                'url': url,
                'metadata': metadata,
                'links': links,
                'scraped_at': datetime.now(),
                'word_count': len(content.split()),
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _clean_soup(self, soup: BeautifulSoup):
        """Remove unwanted HTML elements."""
        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()
        
        # Remove navigation, ads, and other non-content elements
        selectors_to_remove = [
            'nav', 'header', 'footer', 'aside',
            '.navigation', '.navbar', '.nav', '.menu',
            '.advertisement', '.ads', '.ad', '.advert',
            '.sidebar', '.widget', '.social', '.share',
            '.comments', '.comment-form', '.related-posts',
            '.newsletter', '.subscription', '.popup',
            '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]'
        ]
        
        for selector in selectors_to_remove:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove comments
        comments = soup.findAll(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
        
        # Remove elements with display:none or visibility:hidden
        for element in soup.find_all(style=re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden')):
            element.decompose()
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract page title."""
        # Try different title sources in order of preference
        title_sources = [
            ('meta[property="og:title"]', 'content'),
            ('meta[name="twitter:title"]', 'content'),
            ('title', 'text'),
            ('h1', 'text'),
            ('.title', 'text'),
            ('.post-title', 'text'),
            ('.article-title', 'text'),
        ]
        
        for selector, attr in title_sources:
            element = soup.select_one(selector)
            if element:
                if attr == 'content':
                    title = element.get('content')
                else:
                    title = element.get_text(strip=True)
                
                if title and len(title.strip()) > 0:
                    return self._clean_text(title)
        
        # Fallback to URL
        return urlparse(url).path.split('/')[-1] or 'Untitled'
    
    def _extract_main_content(self, soup: BeautifulSoup, source: Optional[Source] = None) -> Optional[str]:
        """Extract main content using various strategies."""
        content = ""
        
        # Use custom XPath selectors from source configuration
        if source and source.crawl_settings.get('xpath_selectors'):
            custom_selectors = source.crawl_settings['xpath_selectors']
            for selector in custom_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator=' ', strip=True)
                    if len(content) > 200:
                        break
        
        # If custom selectors didn't work, try common content selectors
        if not content or len(content) < 200:
            content_selectors = [
                'article',
                '[role="main"]',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                'main',
                '.main-content',
                '#main-content',
                '.story-body',
                '.article-body',
                '.post-body',
                '.content-body',
                '.text-content'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    element_content = element.get_text(separator=' ', strip=True)
                    if len(element_content) > len(content):
                        content = element_content
        
        # Fallback to body content
        if not content or len(content) < 200:
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)
        
        # Clean content
        if content:
            content = self._clean_text(content)
            
            # Remove common boilerplate text
            boilerplate_patterns = [
                r'cookies?\s+policy',
                r'privacy\s+policy',
                r'terms\s+(of\s+)?service',
                r'subscribe\s+to\s+our\s+newsletter',
                r'follow\s+us\s+on',
                r'share\s+this\s+article',
                r'related\s+articles?',
                r'you\s+may\s+also\s+like',
                r'advertisement',
            ]
            
            for pattern in boilerplate_patterns:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)
            
            # Remove extra whitespace
            content = re.sub(r'\s+', ' ', content).strip()
        
        return content if content and len(content) >= 200 else None
    
    def _extract_metadata(self, soup: BeautifulSoup, response: requests.Response) -> Dict:
        """Extract page metadata."""
        metadata = {}
        
        # Extract meta tags
        meta_mappings = {
            'description': ['meta[name="description"]', 'meta[property="og:description"]'],
            'keywords': ['meta[name="keywords"]'],
            'author': ['meta[name="author"]', 'meta[property="article:author"]'],
            'published_time': ['meta[property="article:published_time"]', 'meta[name="date"]'],
            'modified_time': ['meta[property="article:modified_time"]', 'meta[name="last-modified"]'],
            'section': ['meta[property="article:section"]', 'meta[name="section"]'],
            'language': ['meta[name="language"]', 'html[lang]'],
        }
        
        for key, selectors in meta_mappings.items():
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    value = element.get('content') or element.get('lang')
                    if value:
                        metadata[key] = self._clean_text(value)
                        break
        
        # Extract structured data (JSON-LD)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if '@type' in data:
                    metadata['structured_data'] = data
                    break
            except json.JSONDecodeError:
                continue
        
        # HTTP response metadata
        metadata.update({
            'content_type': response.headers.get('content-type', ''),
            'content_length': response.headers.get('content-length', ''),
            'last_modified': response.headers.get('last-modified', ''),
            'etag': response.headers.get('etag', ''),
        })
        
        return metadata
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract internal and external links."""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            
            # Skip certain types of links
            if any(absolute_url.startswith(prefix) for prefix in ['mailto:', 'tel:', 'javascript:', '#']):
                continue
            
            link_text = link.get_text(strip=True)
            if link_text:
                links.append({
                    'url': absolute_url,
                    'text': self._clean_text(link_text),
                    'is_external': urlparse(absolute_url).netloc != urlparse(base_url).netloc
                })
        
        return links[:50]  # Limit to 50 links
    
    def _generate_summary(self, content: str) -> Optional[str]:
        """Generate a summary from content."""
        if not content:
            return None
        
        # Simple extractive summarization (first few sentences)
        sentences = re.split(r'[.!?]+', content)
        summary_sentences = []
        summary_length = 0
        
        for sentence in sentences[:5]:  # Max 5 sentences
            sentence = sentence.strip()
            if sentence and len(sentence) > 20:  # Skip very short sentences
                summary_sentences.append(sentence)
                summary_length += len(sentence)
                if summary_length >= 300:  # Max ~300 characters
                    break
        
        if summary_sentences:
            return '. '.join(summary_sentences) + '.'
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Decode HTML entities
        text = BeautifulSoup(text, 'html.parser').get_text()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text
    
    def create_document_from_scraped_data(self, scraped_data: Dict, user_id: int, source: Optional[Source] = None) -> Optional[Document]:
        """
        Create a Document from scraped data.
        
        Args:
            scraped_data: Dictionary with scraped content
            user_id: User ID
            source: Optional source configuration
            
        Returns:
            Created Document or None
        """
        try:
            # Check if document already exists
            url_hash = hashlib.md5(scraped_data['url'].encode()).hexdigest()
            vector_id = f"web_{source.id if source else 'manual'}_{url_hash}"
            
            existing_doc = Document.query.filter_by(
                user_id=user_id,
                vector_id=vector_id
            ).first()
            
            if existing_doc:
                logger.debug(f"Document already exists: {scraped_data['title']}")
                return existing_doc
            
            # Extract metadata for document
            metadata = scraped_data.get('metadata', {})
            published_date = None
            
            if 'published_time' in metadata:
                try:
                    from dateutil import parser
                    published_date = parser.parse(metadata['published_time'])
                except Exception:
                    pass
            
            # Generate tags from content and metadata
            tags = []
            if 'keywords' in metadata:
                keywords = metadata['keywords'].split(',')
                tags.extend([kw.strip().lower() for kw in keywords if kw.strip()])
            
            if source and source.auto_tags:
                tags.extend(source.auto_tags)
            
            # Create document
            document = Document.create_document(
                user_id=user_id,
                title=scraped_data['title'],
                content=scraped_data['content'],
                summary=scraped_data.get('summary'),
                source_url=scraped_data['url'],
                source_type='web',
                source_name=source.name if source else 'Web Scraping',
                author=metadata.get('author'),
                published_date=published_date,
                tags=tags,
                vector_id=vector_id
            )
            
            # Process document through AI pipeline for semantic search
            try:
                ai_pipeline = self._get_ai_pipeline()
                if ai_pipeline:
                    success = ai_pipeline.process_document(document)
                    if success:
                        logger.info(f"Document processed through AI pipeline: {document.title}")
                    else:
                        logger.warning(f"Failed to process document through AI pipeline: {document.title}")
                else:
                    logger.warning("AI pipeline not available, document not processed for semantic search")
            except Exception as e:
                logger.error(f"Error processing document through AI pipeline: {e}")
                # Don't fail the entire scraping process if AI processing fails
            
            logger.info(f"Created document from scraped content: {document.title}")
            return document
            
        except Exception as e:
            logger.error(f"Error creating document from scraped data: {e}")
            return None
    
    def scrape_source(self, source: Source) -> Tuple[bool, int, Optional[str]]:
        """
        Scrape content from a web source.
        
        Args:
            source: Source model instance
            
        Returns:
            Tuple of (success, documents_created, error_message)
        """
        try:
            logger.info(f"Starting web scraping for source: {source.name} ({source.url})")
            
            # Scrape the main URL
            success, scraped_data, error = self.scrape_url(source.url, source)
            if not success:
                source.update_crawl_stats(success=False, error=error)
                return False, 0, error
            
            documents_created = 0
            
            # Create document from main page
            document = self.create_document_from_scraped_data(scraped_data, source.user_id, source)
            if document:
                documents_created += 1
            
            # TODO: Implement link following for deeper crawling
            # This would follow internal links to scrape additional pages
            
            # Update source statistics
            source.update_crawl_stats(
                success=True,
                articles_count=documents_created,
                error=None
            )
            
            logger.info(f"Successfully scraped {documents_created} documents from {source.name}")
            return True, documents_created, None
            
        except Exception as e:
            error_msg = f"Web scraping failed for {source.name}: {str(e)}"
            logger.error(error_msg)
            source.update_crawl_stats(success=False, error=error_msg)
            return False, 0, error_msg
