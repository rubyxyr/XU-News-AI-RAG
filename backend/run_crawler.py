#!/usr/bin/env python
"""
Crawler service runner for XU-News-AI-RAG.
This script starts the Flask application with the crawler scheduler.
"""
import os
import sys
import signal
import logging
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.crawlers.scheduler import CrawlerScheduler
from app.api.sources import init_crawler_scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/crawler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global variables
app = None
crawler_scheduler = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    
    if crawler_scheduler and crawler_scheduler.is_running():
        logger.info("Stopping crawler scheduler...")
        crawler_scheduler.stop()
    
    logger.info("Crawler service stopped.")
    sys.exit(0)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def main():
    """Main function to run the crawler service."""
    global app, crawler_scheduler
    
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        logger.info("Starting XU-News-AI-RAG Crawler Service...")
        
        # Setup signal handlers
        setup_signal_handlers()
        
        # Get configuration from environment
        config_name = os.environ.get('FLASK_ENV', 'development')
        logger.info(f"Using configuration: {config_name}")
        
        # Create Flask application
        app = create_app(config_name)
        
        with app.app_context():
            # Initialize database if needed
            try:
                db.create_all()
                logger.info("Database initialized")
            except Exception as e:
                logger.warning(f"Database initialization: {e}")
            
            # Initialize crawler scheduler
            logger.info("Initializing crawler scheduler...")
            init_crawler_scheduler(app)
            
            # Keep the service running
            logger.info("✅ Crawler service started successfully!")
            logger.info("Press Ctrl+C to stop the service")
            
            try:
                # Keep the main thread alive
                while True:
                    import time
                    time.sleep(60)  # Sleep for 1 minute
                    
                    # Periodic health check
                    if hasattr(app, 'crawler_scheduler'):
                        scheduler = getattr(app, 'crawler_scheduler')
                        if not scheduler.is_running():
                            logger.error("Scheduler stopped unexpectedly!")
                            break
                    
            except KeyboardInterrupt:
                logger.info("Received shutdown signal...")
                
    except Exception as e:
        logger.error(f"Failed to start crawler service: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
