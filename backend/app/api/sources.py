"""
Sources management API endpoints for RSS feeds and web crawling sources.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime

from app import db
from app.models import Source
from app.utils.decorators import validate_json, require_user_ownership
from app.utils.validators import validate_url
from app.crawlers.scheduler import CrawlerScheduler

bp = Blueprint('sources', __name__)

# Initialize crawler scheduler (will be done in app factory)
crawler_scheduler = None

# Validation Schemas
class SourceCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    url = fields.Url(required=True, validate=validate.Length(max=1000))
    source_type = fields.Str(required=True, validate=validate.OneOf(['rss', 'web', 'api']))
    description = fields.Str(validate=validate.Length(max=500))
    update_frequency = fields.Int(validate=validate.Range(min=5, max=10080))  # 5 minutes to 1 week
    auto_tags = fields.List(fields.Str(validate=validate.Length(max=50)), missing=[])
    crawl_settings = fields.Dict(missing={})


class SourceUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=200))
    url = fields.Url(validate=validate.Length(max=1000))
    description = fields.Str(validate=validate.Length(max=500))
    is_active = fields.Bool()
    update_frequency = fields.Int(validate=validate.Range(min=5, max=10080))
    auto_tags = fields.List(fields.Str(validate=validate.Length(max=50)))
    crawl_settings = fields.Dict()


@bp.route('/sources', methods=['GET'])
@jwt_required()
def get_sources():
    """Get all sources for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get query parameters
        source_type = request.args.get('source_type')
        active_only = request.args.get('active_only', '').lower() == 'true'
        
        # Get sources
        sources = Source.get_user_sources(
            user_id=current_user_id,
            source_type=source_type,
            active_only=active_only
        )
        
        return jsonify({
            'sources': [source.to_dict(include_stats=True) for source in sources],
            'count': len(sources)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get sources error: {e}")
        return jsonify({'error': 'Failed to get sources'}), 500


@bp.route('/sources', methods=['POST'])
@jwt_required()
@validate_json(SourceCreateSchema)
def create_source(validated_data):
    """Create a new crawling source."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Validate URL
        is_valid, validation_message = validate_url(validated_data['url'])
        if not is_valid:
            return jsonify({'error': f'Invalid URL: {validation_message}'}), 400
        
        # Check if source URL already exists for this user
        existing_source = Source.query.filter_by(
            user_id=current_user_id,
            url=validated_data['url']
        ).first()
        
        if existing_source:
            return jsonify({'error': 'Source URL already exists'}), 409
        
        # Set default crawl settings based on source type
        default_settings = {
            'auto_tag': True,
            'auto_summarize': True,
            'extract_content': True,
            'follow_redirects': True,
            'respect_robots_txt': True,
            'max_articles_per_crawl': 50,
            'custom_headers': {},
            'xpath_selectors': {},
            'email_notifications': True
        }
        
        crawl_settings = {**default_settings, **validated_data.get('crawl_settings', {})}
        
        # Create source
        source = Source.create_source(
            user_id=current_user_id,
            name=validated_data['name'],
            url=validated_data['url'],
            source_type=validated_data['source_type'],
            description=validated_data.get('description', ''),
            update_frequency=validated_data.get('update_frequency', 60),  # Default 1 hour
            auto_tags=validated_data.get('auto_tags', []),
            crawl_settings=crawl_settings
        )
        
        # Schedule the source for crawling
        global crawler_scheduler
        if crawler_scheduler:
            scheduler_success = crawler_scheduler.schedule_source(source)
            if not scheduler_success:
                current_app.logger.warning(f"Failed to schedule source: {source.name}")
        
        return jsonify({
            'message': 'Source created successfully',
            'source': source.to_dict(include_stats=True)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Create source error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create source'}), 500


@bp.route('/sources/<int:source_id>', methods=['GET'])
@jwt_required()
@require_user_ownership(Source, 'source_id')
def get_source(source_id, resource):
    """Get a specific source by ID."""
    try:
        source = resource  # From decorator
        
        return jsonify({
            'source': source.to_dict(include_stats=True)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get source error: {e}")
        return jsonify({'error': 'Failed to get source'}), 500


@bp.route('/sources/<int:source_id>', methods=['PUT'])
@jwt_required()
@require_user_ownership(Source, 'source_id')
@validate_json(SourceUpdateSchema)
def update_source(validated_data, source_id, resource):
    """Update a source."""
    try:
        source = resource  # From decorator
        
        # Validate URL if provided
        if 'url' in validated_data:
            is_valid, validation_message = validate_url(validated_data['url'])
            if not is_valid:
                return jsonify({'error': f'Invalid URL: {validation_message}'}), 400
            
            # Check if URL conflicts with another source
            existing_source = Source.query.filter(
                Source.user_id == source.user_id,
                Source.url == validated_data['url'],
                Source.id != source.id
            ).first()
            
            if existing_source:
                return jsonify({'error': 'Source URL already exists'}), 409
        
        # Check if scheduling needs to be updated
        frequency_changed = 'update_frequency' in validated_data
        activation_changed = 'is_active' in validated_data
        
        # Update source
        source.update_source(**validated_data)
        
        # Update scheduling if necessary
        global crawler_scheduler
        if crawler_scheduler and (frequency_changed or activation_changed):
            if source.is_active:
                crawler_scheduler.reschedule_source(source)
            else:
                crawler_scheduler.unschedule_source(source.id)
        
        return jsonify({
            'message': 'Source updated successfully',
            'source': source.to_dict(include_stats=True)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Update source error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update source'}), 500


@bp.route('/sources/<int:source_id>', methods=['DELETE'])
@jwt_required()
@require_user_ownership(Source, 'source_id')
def delete_source(source_id, resource):
    """Delete a source."""
    try:
        source = resource  # From decorator
        
        # Unschedule the source
        global crawler_scheduler
        if crawler_scheduler:
            crawler_scheduler.unschedule_source(source_id)
        
        # Delete associated documents (optional - user choice)
        delete_documents = request.args.get('delete_documents', '').lower() == 'true'
        if delete_documents:
            from app.models import Document
            # Delete documents from this source
            documents = Document.query.filter_by(
                user_id=source.user_id,
                source_name=source.name
            ).all()
            
            for doc in documents:
                db.session.delete(doc)
        
        # Delete source
        db.session.delete(source)
        db.session.commit()
        
        return jsonify({'message': 'Source deleted successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Delete source error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete source'}), 500


@bp.route('/sources/<int:source_id>/crawl', methods=['POST'])
@jwt_required()
@require_user_ownership(Source, 'source_id')
def trigger_immediate_crawl(source_id, resource):
    """Trigger immediate crawling for a source."""
    try:
        source = resource  # From decorator
        
        global crawler_scheduler
        if not crawler_scheduler:
            return jsonify({'error': 'Crawler scheduler not available'}), 503
        
        # Trigger immediate crawl
        result = crawler_scheduler.trigger_immediate_crawl(source_id)
        
        if result['success']:
            return jsonify({
                'message': f'Successfully crawled {result["total_articles"]} articles',
                'result': result
            }), 200
        else:
            return jsonify({
                'error': 'Crawling failed',
                'result': result
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Immediate crawl error: {e}")
        return jsonify({'error': 'Failed to trigger crawl'}), 500


@bp.route('/sources/<int:source_id>/test', methods=['POST'])
@jwt_required()
@require_user_ownership(Source, 'source_id')
def test_source(source_id, resource):
    """Test a source to check if it's accessible and contains content."""
    try:
        source = resource  # From decorator
        
        # Import appropriate crawler
        if source.source_type == 'rss':
            from app.crawlers.rss_crawler import RSSCrawler
            crawler = RSSCrawler()
        elif source.source_type == 'web':
            from app.crawlers.web_scraper import WebScraper
            crawler = WebScraper()
        else:
            return jsonify({'error': 'Unsupported source type for testing'}), 400
        
        # Test the source (dry run)
        if source.source_type == 'rss':
            # Test RSS feed parsing without creating documents
            import feedparser
            feed = feedparser.parse(source.url)
            
            if feed.bozo and not feed.entries:
                return jsonify({
                    'success': False,
                    'error': f'Invalid RSS feed: {getattr(feed, "bozo_exception", "Unknown error")}',
                    'accessible': False
                }), 200
            
            return jsonify({
                'success': True,
                'accessible': True,
                'feed_title': getattr(feed.feed, 'title', 'Unknown'),
                'total_entries': len(feed.entries),
                'latest_entry': {
                    'title': getattr(feed.entries[0], 'title', 'No title') if feed.entries else None,
                    'published': getattr(feed.entries[0], 'published', None) if feed.entries else None
                } if feed.entries else None
            }), 200
            
        elif source.source_type == 'web':
            # Test web scraping
            success, scraped_data, error = crawler.scrape_url(source.url, source)
            
            return jsonify({
                'success': success,
                'accessible': success,
                'error': error,
                'content_preview': {
                    'title': scraped_data.get('title') if scraped_data else None,
                    'word_count': scraped_data.get('word_count') if scraped_data else 0,
                    'has_content': bool(scraped_data and scraped_data.get('content'))
                } if scraped_data else None
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"Test source error: {e}")
        return jsonify({
            'success': False,
            'accessible': False,
            'error': str(e)
        }), 200


@bp.route('/sources/stats', methods=['GET'])
@jwt_required()
def get_sources_stats():
    """Get aggregated sources statistics for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        
        stats = Source.get_source_stats(current_user_id)
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Get sources stats error: {e}")
        return jsonify({'error': 'Failed to get sources statistics'}), 500


@bp.route('/sources/due', methods=['GET'])
@jwt_required()
def get_due_sources():
    """Get sources that are due for crawling."""
    try:
        current_user_id = int(get_jwt_identity())
        
        due_sources = Source.get_due_sources(current_user_id)
        
        return jsonify({
            'sources': [source.to_dict(include_stats=False) for source in due_sources],
            'count': len(due_sources)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get due sources error: {e}")
        return jsonify({'error': 'Failed to get due sources'}), 500


@bp.route('/crawler/status', methods=['GET'])
@jwt_required()
def get_crawler_status():
    """Get crawler scheduler status and job information."""
    try:
        global crawler_scheduler
        if not crawler_scheduler:
            return jsonify({'error': 'Crawler scheduler not available'}), 503
        
        # Get scheduler statistics
        stats = crawler_scheduler.get_scheduler_stats()
        
        # Get current jobs
        jobs = crawler_scheduler.get_job_status()
        
        # Get proxy status if available
        proxy_stats = None
        if hasattr(crawler_scheduler.rss_crawler, 'proxy_manager') and crawler_scheduler.rss_crawler.proxy_manager:
            proxy_stats = crawler_scheduler.rss_crawler.proxy_manager.get_proxy_stats()
        
        return jsonify({
            'scheduler_stats': stats,
            'jobs': jobs,
            'proxy_stats': proxy_stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get crawler status error: {e}")
        return jsonify({'error': 'Failed to get crawler status'}), 500


@bp.route('/crawler/pause', methods=['POST'])
@jwt_required()
def pause_crawler():
    """Pause the crawler scheduler."""
    try:
        global crawler_scheduler
        if not crawler_scheduler:
            return jsonify({'error': 'Crawler scheduler not available'}), 503
        
        # For security, only allow admin users to pause/resume (implement admin check)
        current_user_id = int(get_jwt_identity())
        # TODO: Add admin check here
        
        if crawler_scheduler.is_running():
            crawler_scheduler.stop()
            return jsonify({'message': 'Crawler scheduler paused'}), 200
        else:
            return jsonify({'message': 'Crawler scheduler is already stopped'}), 200
            
    except Exception as e:
        current_app.logger.error(f"Pause crawler error: {e}")
        return jsonify({'error': 'Failed to pause crawler'}), 500


@bp.route('/crawler/resume', methods=['POST'])
@jwt_required()
def resume_crawler():
    """Resume the crawler scheduler."""
    try:
        global crawler_scheduler
        if not crawler_scheduler:
            return jsonify({'error': 'Crawler scheduler not available'}), 503
        
        # For security, only allow admin users to pause/resume (implement admin check)
        current_user_id = int(get_jwt_identity())
        # TODO: Add admin check here
        
        if not crawler_scheduler.is_running():
            crawler_scheduler.start()
            return jsonify({'message': 'Crawler scheduler resumed'}), 200
        else:
            return jsonify({'message': 'Crawler scheduler is already running'}), 200
            
    except Exception as e:
        current_app.logger.error(f"Resume crawler error: {e}")
        return jsonify({'error': 'Failed to resume crawler'}), 500


# Initialize crawler scheduler when the module is imported
def init_crawler_scheduler(app):
    """Initialize the crawler scheduler with app configuration."""
    global crawler_scheduler
    
    try:
        crawler_scheduler = CrawlerScheduler(app.config)
        app.logger.info("Crawler scheduler initialized")
        
        # Start scheduler if not in testing mode
        if not app.config.get('TESTING', False):
            crawler_scheduler.start()
            app.logger.info("Crawler scheduler started")
            
    except Exception as e:
        app.logger.error(f"Failed to initialize crawler scheduler: {e}")


# Error handlers
@bp.errorhandler(ValidationError)
def handle_validation_error(e):
    """Handle marshmallow validation errors."""
    return jsonify({'error': 'Validation failed', 'details': e.messages}), 400
