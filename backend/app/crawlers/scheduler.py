"""
Intelligent crawler scheduler for automated news collection.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import pytz

from app import db
from app.models import Source
from app.crawlers.rss_crawler import RSSCrawler
from app.crawlers.web_scraper import WebScraper
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class CrawlerScheduler:
    """
    Intelligent scheduler for automated crawling tasks with load balancing and error handling.
    """
    
    def __init__(self, config=None):
        """
        Initialize Crawler Scheduler.
        
        Args:
            config: Configuration dictionary with scheduler settings
        """
        self.config = config or {}
        
        # Initialize crawlers
        self.rss_crawler = RSSCrawler(config)
        self.web_scraper = WebScraper(config)
        self.email_service = EmailService(config)
        
        # Scheduler configuration
        self.max_workers = self.config.get('SCHEDULER_MAX_WORKERS', 2)
        self.coalesce = self.config.get('SCHEDULER_COALESCE', True)
        self.max_instances = self.config.get('SCHEDULER_MAX_INSTANCES', 2)
        
        # Job store configuration (use SQLite by default)
        database_url = self.config.get('DATABASE_URL', 'sqlite:///scheduler.db')
        jobstore = SQLAlchemyJobStore(url=database_url)
        
        # Executor configuration
        executors = {
            'default': ThreadPoolExecutor(self.max_workers),
        }
        
        job_defaults = {
            'coalesce': self.coalesce,
            'max_instances': self.max_instances,
            'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
        }
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler(
            jobstores={'default': jobstore},
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.UTC
        )
        
        # Statistics
        self.stats = {
            'jobs_executed': 0,
            'jobs_failed': 0,
            'jobs_missed': 0,
            'last_execution': None,
            'total_articles_crawled': 0,
        }
        
        # Setup event listeners
        self._setup_event_listeners()
        
        logger.info("Crawler Scheduler initialized")
    
    def start(self):
        """Start the scheduler."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Crawler Scheduler started")
                
                # Schedule initial tasks
                self._schedule_existing_sources()
                
                # Schedule periodic maintenance tasks
                self._schedule_maintenance_tasks()
            else:
                logger.warning("Scheduler is already running")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Crawler Scheduler stopped")
            else:
                logger.warning("Scheduler is not running")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
    
    def _setup_event_listeners(self):
        """Setup event listeners for job monitoring."""
        
        def job_executed_listener(event):
            self.stats['jobs_executed'] += 1
            self.stats['last_execution'] = datetime.now()
            
            # Extract job result if available
            if hasattr(event, 'retval') and isinstance(event.retval, dict):
                articles = event.retval.get('total_articles', 0)
                self.stats['total_articles_crawled'] += articles
            
            logger.debug(f"Job executed: {event.job_id}")
        
        def job_error_listener(event):
            self.stats['jobs_failed'] += 1
            logger.error(f"Job failed: {event.job_id} - {event.exception}")
            
            # Send alert email for critical failures
            self._send_failure_alert(event.job_id, str(event.exception))
        
        def job_missed_listener(event):
            self.stats['jobs_missed'] += 1
            logger.warning(f"Job missed: {event.job_id}")
        
        self.scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
        self.scheduler.add_listener(job_missed_listener, EVENT_JOB_MISSED)
    
    def _schedule_existing_sources(self):
        """Schedule crawling jobs for all existing active sources."""
        try:
            active_sources = Source.query.filter_by(is_active=True).all()
            
            for source in active_sources:
                self.schedule_source(source)
                
            logger.info(f"Scheduled {len(active_sources)} existing sources")
            
        except Exception as e:
            logger.error(f"Failed to schedule existing sources: {e}")
    
    def _schedule_maintenance_tasks(self):
        """Schedule periodic maintenance tasks."""
        
        # Proxy health check (every 5 minutes)
        self.scheduler.add_job(
            func=self._proxy_health_check_task,
            trigger=IntervalTrigger(minutes=5),
            id='proxy_health_check',
            name='Proxy Health Check',
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        
        # Database cleanup (daily at 2 AM)
        # self.scheduler.add_job(
        #     func=self._database_cleanup_task,
        #     trigger=CronTrigger(hour=2, minute=0),
        #     id='database_cleanup',
        #     name='Database Cleanup',
        #     replace_existing=True,
        #     coalesce=True,
        #     max_instances=1
        # )
        
        # Statistics report (weekly on Monday at 9 AM)
        # self.scheduler.add_job(
        #     func=self._weekly_report_task,
        #     trigger=CronTrigger(day_of_week=0, hour=9, minute=0),
        #     id='weekly_report',
        #     name='Weekly Statistics Report',
        #     replace_existing=True,
        #     coalesce=True,
        #     max_instances=1
        # )
        
        logger.info("Scheduled maintenance tasks")
    
    def schedule_source(self, source: Source) -> bool:
        """
        Schedule crawling job for a source.
        
        Args:
            source: Source model instance
            
        Returns:
            True if scheduled successfully, False otherwise
        """
        try:
            job_id = f"crawl_source_{source.id}"
            
            # Remove existing job if present
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass  # Job doesn't exist, which is fine
            
            # Determine trigger based on update frequency
            minutes = source.update_frequency or 60
            trigger = IntervalTrigger(minutes=minutes)
            
            # Choose appropriate crawler function
            if source.source_type == 'rss':
                crawler_func = self._crawl_rss_source
            elif source.source_type == 'web':
                crawler_func = self._crawl_web_source
            else:
                logger.warning(f"Unknown source type: {source.source_type}")
                return False
            
            # Schedule the job
            self.scheduler.add_job(
                func=crawler_func,
                trigger=trigger,
                args=[source.id],
                id=job_id,
                name=f"Crawl {source.name}",
                replace_existing=True,
                coalesce=True,
                max_instances=2,  # Allow some overlap but not too much
                next_run_time=source.next_crawl or datetime.now()
            )
            
            logger.info(f"Scheduled crawling for source: {source.name} (every {minutes} minutes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule source {source.name}: {e}")
            return False
    
    def unschedule_source(self, source_id: int):
        """
        Remove scheduled job for a source.
        
        Args:
            source_id: Source ID
        """
        try:
            job_id = f"crawl_source_{source_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled crawling for source ID: {source_id}")
        except Exception as e:
            logger.debug(f"Failed to unschedule source {source_id}: {e}")
    
    def reschedule_source(self, source: Source):
        """
        Reschedule a source (useful when update frequency changes).
        
        Args:
            source: Source model instance
        """
        self.unschedule_source(source.id)
        self.schedule_source(source)
    
    def _crawl_rss_source(self, source_id: int) -> Dict:
        """
        Crawl an RSS source (job function).
        
        Args:
            source_id: Source ID to crawl
            
        Returns:
            Dictionary with crawling results
        """
        try:
            source = Source.query.get(source_id)
            if not source:
                logger.error(f"Source not found: {source_id}")
                return {'success': False, 'error': 'Source not found'}
            
            if not source.is_active:
                logger.info(f"Skipping inactive source: {source.name}")
                return {'success': True, 'total_articles': 0, 'message': 'Source inactive'}
            
            logger.info(f"Starting scheduled RSS crawl: {source.name}")
            
            success, articles_count, error = self.rss_crawler.crawl_source(source)
            
            result = {
                'success': success,
                'source_id': source_id,
                'source_name': source.name,
                'total_articles': articles_count,
                'timestamp': datetime.now().isoformat()
            }
            
            if error:
                result['error'] = error
            
            logger.info(f"RSS crawl completed: {source.name} - {articles_count} articles")
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled RSS crawl for source {source_id}: {e}")
            return {
                'success': False,
                'source_id': source_id,
                'error': str(e),
                'total_articles': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _crawl_web_source(self, source_id: int) -> Dict:
        """
        Crawl a web source (job function).
        
        Args:
            source_id: Source ID to crawl
            
        Returns:
            Dictionary with crawling results
        """
        try:
            source = Source.query.get(source_id)
            if not source:
                logger.error(f"Source not found: {source_id}")
                return {'success': False, 'error': 'Source not found'}
            
            if not source.is_active:
                logger.info(f"Skipping inactive source: {source.name}")
                return {'success': True, 'total_articles': 0, 'message': 'Source inactive'}
            
            logger.info(f"Starting scheduled web crawl: {source.name}")
            
            success, documents_count, error = self.web_scraper.scrape_source(source)
            
            result = {
                'success': success,
                'source_id': source_id,
                'source_name': source.name,
                'total_articles': documents_count,
                'timestamp': datetime.now().isoformat()
            }
            
            if error:
                result['error'] = error
            
            logger.info(f"Web crawl completed: {source.name} - {documents_count} documents")
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled web crawl for source {source_id}: {e}")
            return {
                'success': False,
                'source_id': source_id,
                'error': str(e),
                'total_articles': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _proxy_health_check_task(self):
        """Periodic proxy health check task."""
        try:
            logger.debug("Running proxy health check task")
            
            if self.rss_crawler and hasattr(self.rss_crawler, 'proxy_manager'):
                self.rss_crawler.proxy_manager.health_check_proxies()
            
            if self.web_scraper and hasattr(self.web_scraper, 'proxy_manager'):
                self.web_scraper.proxy_manager.health_check_proxies()
            
        except Exception as e:
            logger.error(f"Proxy health check task failed: {e}")
    
    def _database_cleanup_task(self):
        """Periodic database cleanup task."""
        try:
            logger.info("Running database cleanup task")
            
            # Clean up old search history (older than 90 days)
            from app.models import SearchHistory
            removed_searches = SearchHistory.cleanup_old_searches(days=90)
            logger.info(f"Cleaned up {removed_searches} old search records")
            
            # Update tag usage counts
            from app.models import Tag
            Tag.update_all_usage_counts()
            logger.info("Updated tag usage counts")
            
            # Clean up unused tags
            removed_tags = Tag.cleanup_unused_tags(min_usage=0)
            logger.info(f"Cleaned up {removed_tags} unused tags")
            
            # Optimize database (SQLite specific)
            if 'sqlite' in self.config.get('DATABASE_URL', ''):
                db.engine.execute('VACUUM')
                logger.info("Database vacuumed")
            
        except Exception as e:
            logger.error(f"Database cleanup task failed: {e}")
    
    def _weekly_report_task(self):
        """Generate and send weekly statistics report."""
        try:
            logger.info("Generating weekly statistics report")
            
            # Collect statistics
            total_sources = Source.query.count()
            active_sources = Source.query.filter_by(is_active=True).count()
            
            from app.models import Document
            week_ago = datetime.now() - timedelta(days=7)
            new_documents = Document.query.filter(Document.created_at >= week_ago).count()
            total_documents = Document.query.count()
            
            # Generate report
            report = f"""
            XU-News-AI-RAG Weekly Crawler Report
            ===================================
            
            Week ending: {datetime.now().strftime('%Y-%m-%d')}
            
            Source Statistics:
            - Total sources: {total_sources}
            - Active sources: {active_sources}
            
            Content Statistics:
            - New documents this week: {new_documents}
            - Total documents: {total_documents}
            
            Scheduler Statistics:
            - Jobs executed: {self.stats['jobs_executed']}
            - Jobs failed: {self.stats['jobs_failed']}
            - Jobs missed: {self.stats['jobs_missed']}
            - Total articles crawled: {self.stats['total_articles_crawled']}
            - Last execution: {self.stats['last_execution']}
            
            Current Jobs:
            """
            
            # Add job information
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'None'
                report += f"  - {job.name}: next run at {next_run}\n"
            
            # Send report email (if configured)
            admin_email = self.config.get('ADMIN_EMAIL')
            if admin_email and self.email_service:
                self.email_service.send_email(
                    to_email=admin_email,
                    subject='XU-News-AI-RAG Weekly Crawler Report',
                    body=report
                )
                logger.info("Weekly report sent to admin")
            
        except Exception as e:
            logger.error(f"Weekly report task failed: {e}")
    
    def _send_failure_alert(self, job_id: str, error_message: str):
        """Send failure alert email."""
        try:
            admin_email = self.config.get('ADMIN_EMAIL')
            if admin_email and self.email_service:
                subject = f"XU-News-AI-RAG Crawler Job Failed: {job_id}"
                body = f"""
                A scheduled crawler job has failed:
                
                Job ID: {job_id}
                Error: {error_message}
                Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                Please check the logs for more details.
                """
                
                self.email_service.send_email(
                    to_email=admin_email,
                    subject=subject,
                    body=body
                )
        except Exception as e:
            logger.error(f"Failed to send failure alert: {e}")
    
    def trigger_immediate_crawl(self, source_id: int) -> Dict:
        """
        Trigger immediate crawling for a source (bypass schedule).
        
        Args:
            source_id: Source ID to crawl immediately
            
        Returns:
            Dictionary with crawling results
        """
        try:
            source = Source.query.get(source_id)
            if not source:
                return {'success': False, 'error': 'Source not found'}
            
            logger.info(f"Triggering immediate crawl for: {source.name}")
            
            if source.source_type == 'rss':
                success, articles_count, error = self.rss_crawler.crawl_source(source)
            elif source.source_type == 'web':
                success, articles_count, error = self.web_scraper.scrape_source(source)
            else:
                return {'success': False, 'error': 'Unknown source type'}
            
            result = {
                'success': success,
                'source_id': source_id,
                'source_name': source.name,
                'total_articles': articles_count,
                'timestamp': datetime.now().isoformat()
            }
            
            if error:
                result['error'] = error
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to trigger immediate crawl: {e}")
            return {
                'success': False,
                'source_id': source_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_job_status(self) -> List[Dict]:
        """
        Get status of all scheduled jobs.
        
        Returns:
            List of job status dictionaries
        """
        jobs = []
        
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'max_instances': job.max_instances,
                'coalesce': job.coalesce,
            })
        
        return jobs
    
    def get_scheduler_stats(self) -> Dict:
        """
        Get scheduler statistics.
        
        Returns:
            Dictionary with scheduler statistics
        """
        stats = self.stats.copy()
        stats.update({
            'is_running': self.scheduler.running,
            'total_jobs': len(self.scheduler.get_jobs()),
            'max_workers': self.max_workers,
            'last_execution': stats['last_execution'].isoformat() if stats['last_execution'] else None,
        })
        
        return stats
    
    def pause_job(self, job_id: str):
        """Pause a specific job."""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
    
    def resume_job(self, job_id: str):
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler.running
