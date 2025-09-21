#!/usr/bin/env python
"""
RSS-only crawler service for XU-News-AI-RAG.
This script runs only RSS crawling, ignoring web sources.
"""
import os
import sys
import signal
import logging
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.crawlers.rss_crawler import RSSCrawler
from app.models import Source

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rss_crawler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global variables
app = None
rss_crawler = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down RSS crawler...")
    logger.info("RSS crawler service stopped.")
    sys.exit(0)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def crawl_rss_sources():
    """Crawl all active RSS sources."""
    with app.app_context():
        # Get only active RSS sources
        rss_sources = Source.query.filter_by(
            source_type='rss',
            is_active=True
        ).all()
        
        if not rss_sources:
            logger.info("No active RSS sources found")
            return
        
        logger.info(f"Found {len(rss_sources)} active RSS sources")
        
        for source in rss_sources:
            try:
                logger.info(f"🔄 Crawling: {source.name}")
                result = rss_crawler.crawl_source(source)
                
                if result['success']:
                    logger.info(f"✅ {source.name}: {result['total_articles']} articles")
                else:
                    logger.error(f"❌ {source.name}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"❌ Error crawling {source.name}: {e}")


def main():
    """Main function to run the RSS-only crawler service."""
    global app, rss_crawler
    
    try:
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        logger.info("🚀 Starting RSS-Only Crawler Service...")
        
        # Setup signal handlers
        setup_signal_handlers()
        
        # Create Flask application
        config_name = os.environ.get('FLASK_ENV', 'development')
        app = create_app(config_name)
        
        with app.app_context():
            # Initialize database
            db.create_all()
            
            # Initialize RSS crawler only
            rss_crawler = RSSCrawler(app.config)
            logger.info("RSS Crawler initialized")
            
            logger.info("✅ RSS-only crawler service started!")
            logger.info("📡 Only RSS sources will be crawled")
            logger.info("Press Ctrl+C to stop")
            
            # Run crawling loop
            import time
            crawl_interval = 300  # 5 minutes
            
            while True:
                try:
                    crawl_rss_sources()
                    logger.info(f"💤 Sleeping for {crawl_interval // 60} minutes...")
                    time.sleep(crawl_interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Crawling error: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
                    
    except Exception as e:
        logger.error(f"Failed to start RSS crawler service: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
