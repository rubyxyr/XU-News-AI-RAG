#!/usr/bin/env python
"""
Command-line interface for managing the XU-News-AI-RAG crawler system.
"""
import os
import sys
import click
import logging
from datetime import datetime
from flask import current_app

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Source, Document, User
from app.crawlers.scheduler import CrawlerScheduler
from app.crawlers.rss_crawler import RSSCrawler
from app.crawlers.web_scraper import WebScraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Global scheduler instance
scheduler = None


@click.group()
@click.option('--config', default='development', help='Configuration name (development, production, testing)')
@click.pass_context
def cli(ctx, config):
    """XU-News-AI-RAG Crawler Management CLI."""
    # Create Flask application context
    app = create_app(config)
    ctx.ensure_object(dict)
    ctx.obj['app'] = app
    
    with app.app_context():
        # Initialize scheduler
        global scheduler
        scheduler = CrawlerScheduler(app.config)


@cli.command()
@click.pass_context
def start_scheduler(ctx):
    """Start the crawler scheduler."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            if scheduler.is_running():
                click.echo("Scheduler is already running!")
                return
            
            click.echo("Starting crawler scheduler...")
            scheduler.start()
            click.echo("✅ Crawler scheduler started successfully!")
            
            # Keep the process running
            try:
                while True:
                    import time
                    time.sleep(60)  # Check every minute
                    
                    if not scheduler.is_running():
                        click.echo("❌ Scheduler stopped unexpectedly!")
                        break
                    
            except KeyboardInterrupt:
                click.echo("\n🛑 Stopping crawler scheduler...")
                scheduler.stop()
                click.echo("✅ Crawler scheduler stopped.")
                
        except Exception as e:
            click.echo(f"❌ Failed to start scheduler: {e}")
            sys.exit(1)


@cli.command()
@click.pass_context
def stop_scheduler(ctx):
    """Stop the crawler scheduler."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            if not scheduler.is_running():
                click.echo("Scheduler is not running.")
                return
            
            click.echo("Stopping crawler scheduler...")
            scheduler.stop()
            click.echo("✅ Crawler scheduler stopped successfully!")
            
        except Exception as e:
            click.echo(f"❌ Failed to stop scheduler: {e}")
            sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show crawler scheduler status."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            stats = scheduler.get_scheduler_stats()
            jobs = scheduler.get_job_status()
            
            click.echo("📊 Crawler Scheduler Status")
            click.echo("=" * 50)
            click.echo(f"Running: {'✅ Yes' if stats['is_running'] else '❌ No'}")
            click.echo(f"Total Jobs: {stats['total_jobs']}")
            click.echo(f"Max Workers: {stats['max_workers']}")
            click.echo(f"Jobs Executed: {stats['jobs_executed']}")
            click.echo(f"Jobs Failed: {stats['jobs_failed']}")
            click.echo(f"Jobs Missed: {stats['jobs_missed']}")
            click.echo(f"Last Execution: {stats['last_execution'] or 'Never'}")
            click.echo(f"Total Articles Crawled: {stats['total_articles_crawled']}")
            
            if jobs:
                click.echo(f"\n📋 Scheduled Jobs ({len(jobs)}):")
                click.echo("-" * 50)
                for job in jobs:
                    next_run = job['next_run_time']
                    if next_run:
                        from datetime import datetime
                        dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                        next_run_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        next_run_str = 'Not scheduled'
                    
                    click.echo(f"• {job['name']}")
                    click.echo(f"  ID: {job['id']}")
                    click.echo(f"  Next Run: {next_run_str}")
                    click.echo(f"  Trigger: {job['trigger']}")
                    click.echo()
            else:
                click.echo("\nNo scheduled jobs.")
                
        except Exception as e:
            click.echo(f"❌ Failed to get status: {e}")
            sys.exit(1)


@cli.command()
@click.option('--user-id', type=int, help='Crawl sources for specific user only')
@click.pass_context
def crawl_now(ctx, user_id):
    """Trigger immediate crawling for all due sources."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            click.echo("🚀 Starting immediate crawl...")
            
            # Get due sources
            if user_id:
                due_sources = Source.get_due_sources(user_id)
                click.echo(f"Found {len(due_sources)} due sources for user {user_id}")
            else:
                due_sources = Source.get_due_sources()
                click.echo(f"Found {len(due_sources)} due sources across all users")
            
            if not due_sources:
                click.echo("No sources are due for crawling.")
                return
            
            # Initialize crawlers
            rss_crawler = RSSCrawler(app.config)
            web_scraper = WebScraper(app.config)
            
            total_articles = 0
            successful_sources = 0
            failed_sources = 0
            
            with click.progressbar(due_sources, label='Crawling sources') as bar:
                for source in bar:
                    try:
                        if source.source_type == 'rss':
                            success, articles_count, error = rss_crawler.crawl_source(source)
                        elif source.source_type == 'web':
                            success, articles_count, error = web_scraper.scrape_source(source)
                        else:
                            click.echo(f"⚠️  Skipping unsupported source type: {source.source_type}")
                            continue
                        
                        if success:
                            successful_sources += 1
                            total_articles += articles_count
                            click.echo(f"✅ {source.name}: {articles_count} articles")
                        else:
                            failed_sources += 1
                            click.echo(f"❌ {source.name}: {error}")
                            
                    except Exception as e:
                        failed_sources += 1
                        click.echo(f"❌ {source.name}: {str(e)}")
            
            click.echo(f"\n📊 Crawling Summary:")
            click.echo(f"Total articles collected: {total_articles}")
            click.echo(f"Successful sources: {successful_sources}")
            click.echo(f"Failed sources: {failed_sources}")
            
        except Exception as e:
            click.echo(f"❌ Crawling failed: {e}")
            sys.exit(1)


@cli.command()
@click.option('--source-id', type=int, required=True, help='Source ID to crawl')
@click.pass_context
def crawl_source(ctx, source_id):
    """Crawl a specific source by ID."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            source = Source.query.get(source_id)
            if not source:
                click.echo(f"❌ Source with ID {source_id} not found.")
                sys.exit(1)
            
            click.echo(f"🚀 Crawling source: {source.name}")
            
            if source.source_type == 'rss':
                crawler = RSSCrawler(app.config)
                success, articles_count, error = crawler.crawl_source(source)
            elif source.source_type == 'web':
                scraper = WebScraper(app.config)
                success, articles_count, error = scraper.scrape_source(source)
            else:
                click.echo(f"❌ Unsupported source type: {source.source_type}")
                sys.exit(1)
            
            if success:
                click.echo(f"✅ Successfully crawled {articles_count} articles from {source.name}")
            else:
                click.echo(f"❌ Crawling failed: {error}")
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Failed to crawl source: {e}")
            sys.exit(1)


@cli.command()
@click.pass_context
def list_sources(ctx):
    """List all crawling sources."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            sources = Source.query.all()
            
            if not sources:
                click.echo("No sources configured.")
                return
            
            click.echo(f"📋 Crawling Sources ({len(sources)}):")
            click.echo("=" * 80)
            
            for source in sources:
                status_icon = "✅" if source.is_active else "❌"
                last_crawled = source.last_crawled.strftime('%Y-%m-%d %H:%M') if source.last_crawled else 'Never'
                
                click.echo(f"{status_icon} [{source.id}] {source.name}")
                click.echo(f"    Type: {source.source_type.upper()}")
                click.echo(f"    URL: {source.url}")
                click.echo(f"    User ID: {source.user_id}")
                click.echo(f"    Articles: {source.total_articles}")
                click.echo(f"    Last Crawled: {last_crawled}")
                click.echo(f"    Update Frequency: {source.update_frequency} minutes")
                click.echo()
                
        except Exception as e:
            click.echo(f"❌ Failed to list sources: {e}")
            sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show crawler statistics."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            # Overall statistics
            total_sources = Source.query.count()
            active_sources = Source.query.filter_by(is_active=True).count()
            total_documents = Document.query.count()
            total_users = User.query.count()
            
            # Recent activity (last 24 hours)
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            recent_documents = Document.query.filter(Document.created_at >= yesterday).count()
            
            # Statistics by source type
            rss_sources = Source.query.filter_by(source_type='rss').count()
            web_sources = Source.query.filter_by(source_type='web').count()
            
            click.echo("📊 XU-News-AI-RAG Statistics")
            click.echo("=" * 50)
            click.echo(f"Total Users: {total_users}")
            click.echo(f"Total Sources: {total_sources}")
            click.echo(f"  - RSS Sources: {rss_sources}")
            click.echo(f"  - Web Sources: {web_sources}")
            click.echo(f"Active Sources: {active_sources}")
            click.echo(f"Total Documents: {total_documents}")
            click.echo(f"Documents Added (24h): {recent_documents}")
            
            # Top sources by article count
            top_sources = Source.query.order_by(Source.total_articles.desc()).limit(5).all()
            if top_sources:
                click.echo(f"\n🏆 Top Sources by Articles:")
                click.echo("-" * 30)
                for i, source in enumerate(top_sources, 1):
                    click.echo(f"{i}. {source.name}: {source.total_articles} articles")
            
        except Exception as e:
            click.echo(f"❌ Failed to get statistics: {e}")
            sys.exit(1)


@cli.command()
@click.option('--days', default=30, help='Clean up data older than N days')
@click.pass_context
def cleanup(ctx, days):
    """Clean up old data and optimize database."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            click.echo(f"🧹 Cleaning up data older than {days} days...")
            
            # Clean up old search history
            from app.models import SearchHistory
            removed_searches = SearchHistory.cleanup_old_searches(days)
            click.echo(f"✅ Removed {removed_searches} old search records")
            
            # Update tag usage counts
            from app.models import Tag
            Tag.update_all_usage_counts()
            click.echo("✅ Updated tag usage counts")
            
            # Clean up unused tags
            removed_tags = Tag.cleanup_unused_tags(min_usage=0)
            click.echo(f"✅ Removed {removed_tags} unused tags")
            
            # Optimize database (SQLite specific)
            if 'sqlite' in app.config.get('DATABASE_URL', ''):
                db.engine.execute('VACUUM')
                click.echo("✅ Database optimized")
            
            click.echo("✅ Cleanup completed successfully!")
            
        except Exception as e:
            click.echo(f"❌ Cleanup failed: {e}")
            sys.exit(1)


@cli.command()
@click.option('--email', prompt='Admin email address', help='Admin email for test')
@click.pass_context
def test_email(ctx, email):
    """Test email configuration."""
    app = ctx.obj['app']
    
    with app.app_context():
        try:
            from app.services.email_service import EmailService
            
            email_service = EmailService(app.config)
            result = email_service.test_configuration()
            
            if result['success']:
                click.echo(f"✅ {result['message']}")
                
                # Send a test notification
                success = email_service.send_email(
                    to_email=email,
                    subject='XU-News-AI-RAG Crawler CLI Test',
                    body='This is a test email sent from the crawler CLI.'
                )
                
                if success:
                    click.echo(f"✅ Test email sent to {email}")
                else:
                    click.echo(f"❌ Failed to send test email to {email}")
                    
            else:
                click.echo(f"❌ {result['message']}")
                
        except Exception as e:
            click.echo(f"❌ Email test failed: {e}")
            sys.exit(1)


if __name__ == '__main__':
    cli()
