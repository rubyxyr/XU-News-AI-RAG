"""
Proxy Manager for intelligent proxy handling and rotation.
"""
import logging
import time
import random
from typing import List, Dict, Optional
import requests
from threading import Lock
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Intelligent proxy manager with rotation, health checking, and failure handling.
    """
    
    def __init__(self, config=None):
        """
        Initialize Proxy Manager.
        
        Args:
            config: Configuration dictionary with proxy settings
        """
        self.config = config or {}
        self.proxies = []
        self.proxy_stats = defaultdict(lambda: {
            'success_count': 0,
            'failure_count': 0,
            'last_used': None,
            'last_failure': None,
            'response_times': [],
            'is_healthy': True
        })
        self.current_proxy_index = 0
        self.lock = Lock()
        
        # Configuration
        self.health_check_interval = self.config.get('PROXY_HEALTH_CHECK_INTERVAL', 300)  # 5 minutes
        self.max_failures = self.config.get('PROXY_MAX_FAILURES', 3)
        self.failure_timeout = self.config.get('PROXY_FAILURE_TIMEOUT', 600)  # 10 minutes
        self.rotation_strategy = self.config.get('PROXY_ROTATION_STRATEGY', 'round_robin')  # round_robin, random, performance
        
        # Load proxies from configuration
        self._load_proxies()
        
        logger.info(f"Proxy Manager initialized with {len(self.proxies)} proxies")
    
    def _load_proxies(self):
        """Load proxy configurations."""
        proxy_configs = self.config.get('PROXIES', [])
        
        # Support different proxy configuration formats
        for proxy_config in proxy_configs:
            if isinstance(proxy_config, str):
                # Simple URL format
                self.proxies.append({
                    'url': proxy_config,
                    'type': 'http',
                    'username': None,
                    'password': None,
                })
            elif isinstance(proxy_config, dict):
                # Detailed configuration
                self.proxies.append({
                    'url': proxy_config.get('url', ''),
                    'type': proxy_config.get('type', 'http'),
                    'username': proxy_config.get('username'),
                    'password': proxy_config.get('password'),
                    'location': proxy_config.get('location', ''),
                    'provider': proxy_config.get('provider', ''),
                })
        
        # If no proxies configured, add some free proxy examples (for demonstration)
        if not self.proxies:
            # Note: These are example proxies - in production, use reliable proxy services
            example_proxies = [
                'http://proxy1.example.com:8080',
                'http://proxy2.example.com:8080',
                'socks5://proxy3.example.com:1080'
            ]
            
            for proxy_url in example_proxies:
                self.proxies.append({
                    'url': proxy_url,
                    'type': 'http' if proxy_url.startswith('http') else 'socks5',
                    'username': None,
                    'password': None,
                })
    
    def get_proxy(self) -> Optional[Dict]:
        """
        Get the next available proxy based on rotation strategy.
        
        Returns:
            Proxy configuration dictionary or None if no proxies available
        """
        if not self.proxies:
            return None
        
        with self.lock:
            healthy_proxies = [
                proxy for proxy in self.proxies 
                if self._is_proxy_healthy(proxy)
            ]
            
            if not healthy_proxies:
                logger.warning("No healthy proxies available")
                # Try to recover failed proxies
                self._recover_failed_proxies()
                return None
            
            if self.rotation_strategy == 'random':
                proxy = random.choice(healthy_proxies)
            elif self.rotation_strategy == 'performance':
                proxy = self._get_best_performance_proxy(healthy_proxies)
            else:  # round_robin (default)
                proxy = self._get_round_robin_proxy(healthy_proxies)
            
            # Update usage statistics
            self.proxy_stats[proxy['url']]['last_used'] = datetime.now()
            
            return proxy
    
    def _is_proxy_healthy(self, proxy: Dict) -> bool:
        """
        Check if a proxy is healthy based on recent failure history.
        
        Args:
            proxy: Proxy configuration
            
        Returns:
            True if proxy is healthy, False otherwise
        """
        stats = self.proxy_stats[proxy['url']]
        
        # Check if proxy has exceeded maximum failures
        if stats['failure_count'] >= self.max_failures:
            # Check if enough time has passed since last failure to retry
            if stats['last_failure']:
                time_since_failure = datetime.now() - stats['last_failure']
                if time_since_failure < timedelta(seconds=self.failure_timeout):
                    return False
                else:
                    # Reset failure count after timeout
                    stats['failure_count'] = 0
                    stats['is_healthy'] = True
        
        return stats['is_healthy']
    
    def _get_round_robin_proxy(self, proxies: List[Dict]) -> Dict:
        """Get proxy using round-robin strategy."""
        if not proxies:
            return None
        
        proxy = proxies[self.current_proxy_index % len(proxies)]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(proxies)
        return proxy
    
    def _get_best_performance_proxy(self, proxies: List[Dict]) -> Dict:
        """Get proxy with best performance metrics."""
        if not proxies:
            return None
        
        best_proxy = None
        best_score = float('inf')
        
        for proxy in proxies:
            stats = self.proxy_stats[proxy['url']]
            
            # Calculate performance score (lower is better)
            avg_response_time = (
                sum(stats['response_times'][-10:]) / len(stats['response_times'][-10:]) 
                if stats['response_times'] else 1.0
            )
            
            failure_rate = (
                stats['failure_count'] / (stats['success_count'] + stats['failure_count'])
                if (stats['success_count'] + stats['failure_count']) > 0 else 0.5
            )
            
            score = avg_response_time * (1 + failure_rate)
            
            if score < best_score:
                best_score = score
                best_proxy = proxy
        
        return best_proxy or proxies[0]
    
    def _recover_failed_proxies(self):
        """Attempt to recover proxies that have failed."""
        current_time = datetime.now()
        
        for proxy in self.proxies:
            stats = self.proxy_stats[proxy['url']]
            
            if not stats['is_healthy'] and stats['last_failure']:
                time_since_failure = current_time - stats['last_failure']
                
                if time_since_failure > timedelta(seconds=self.failure_timeout):
                    logger.info(f"Attempting to recover proxy: {proxy['url']}")
                    
                    # Reset failure statistics
                    stats['failure_count'] = 0
                    stats['is_healthy'] = True
                    stats['last_failure'] = None
    
    def report_success(self, proxy: Dict, response_time: float = None):
        """
        Report successful proxy usage.
        
        Args:
            proxy: Proxy configuration that was used
            response_time: Response time in seconds (optional)
        """
        if not proxy:
            return
        
        with self.lock:
            stats = self.proxy_stats[proxy['url']]
            stats['success_count'] += 1
            stats['is_healthy'] = True
            
            if response_time is not None:
                stats['response_times'].append(response_time)
                # Keep only last 20 response times
                if len(stats['response_times']) > 20:
                    stats['response_times'] = stats['response_times'][-20:]
        
        logger.debug(f"Proxy success reported: {proxy['url']}")
    
    def report_failure(self, proxy: Dict, error: Exception = None):
        """
        Report proxy failure.
        
        Args:
            proxy: Proxy configuration that failed
            error: Exception that occurred (optional)
        """
        if not proxy:
            return
        
        with self.lock:
            stats = self.proxy_stats[proxy['url']]
            stats['failure_count'] += 1
            stats['last_failure'] = datetime.now()
            
            if stats['failure_count'] >= self.max_failures:
                stats['is_healthy'] = False
                logger.warning(f"Proxy marked as unhealthy: {proxy['url']}")
        
        logger.debug(f"Proxy failure reported: {proxy['url']} - {error}")
    
    def health_check_proxies(self):
        """
        Perform health check on all proxies.
        This should be called periodically to maintain proxy health status.
        """
        logger.info("Starting proxy health check...")
        
        for proxy in self.proxies:
            try:
                success = self._test_proxy(proxy)
                
                if success:
                    self.report_success(proxy)
                    logger.debug(f"Proxy health check passed: {proxy['url']}")
                else:
                    self.report_failure(proxy)
                    logger.debug(f"Proxy health check failed: {proxy['url']}")
                    
                # Small delay between health checks
                time.sleep(0.5)
                
            except Exception as e:
                self.report_failure(proxy, e)
                logger.debug(f"Proxy health check error: {proxy['url']} - {e}")
        
        logger.info("Proxy health check completed")
    
    def _test_proxy(self, proxy: Dict) -> bool:
        """
        Test a proxy by making a simple HTTP request.
        
        Args:
            proxy: Proxy configuration to test
            
        Returns:
            True if proxy is working, False otherwise
        """
        try:
            # Test URL (should be a simple, reliable endpoint)
            test_url = 'http://httpbin.org/ip'
            
            proxies = {
                'http': proxy['url'],
                'https': proxy['url']
            }
            
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=10,
                headers={'User-Agent': 'XU-News-AI-RAG-Proxy-Test/1.0'}
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_proxy_stats(self) -> Dict:
        """
        Get statistics for all proxies.
        
        Returns:
            Dictionary with proxy statistics
        """
        with self.lock:
            stats_summary = {
                'total_proxies': len(self.proxies),
                'healthy_proxies': 0,
                'unhealthy_proxies': 0,
                'proxies': []
            }
            
            for proxy in self.proxies:
                proxy_stats = self.proxy_stats[proxy['url']]
                
                is_healthy = self._is_proxy_healthy(proxy)
                if is_healthy:
                    stats_summary['healthy_proxies'] += 1
                else:
                    stats_summary['unhealthy_proxies'] += 1
                
                avg_response_time = (
                    sum(proxy_stats['response_times']) / len(proxy_stats['response_times'])
                    if proxy_stats['response_times'] else 0
                )
                
                stats_summary['proxies'].append({
                    'url': proxy['url'],
                    'type': proxy.get('type', 'http'),
                    'is_healthy': is_healthy,
                    'success_count': proxy_stats['success_count'],
                    'failure_count': proxy_stats['failure_count'],
                    'last_used': proxy_stats['last_used'].isoformat() if proxy_stats['last_used'] else None,
                    'last_failure': proxy_stats['last_failure'].isoformat() if proxy_stats['last_failure'] else None,
                    'avg_response_time': round(avg_response_time, 3),
                    'location': proxy.get('location', ''),
                    'provider': proxy.get('provider', ''),
                })
            
            return stats_summary
    
    def add_proxy(self, proxy_config: Dict):
        """
        Add a new proxy to the pool.
        
        Args:
            proxy_config: Proxy configuration dictionary
        """
        with self.lock:
            self.proxies.append(proxy_config)
            logger.info(f"Added new proxy: {proxy_config['url']}")
    
    def remove_proxy(self, proxy_url: str):
        """
        Remove a proxy from the pool.
        
        Args:
            proxy_url: URL of the proxy to remove
        """
        with self.lock:
            self.proxies = [p for p in self.proxies if p['url'] != proxy_url]
            if proxy_url in self.proxy_stats:
                del self.proxy_stats[proxy_url]
            logger.info(f"Removed proxy: {proxy_url}")
    
    def rotate_proxy(self):
        """Force rotation to next proxy."""
        with self.lock:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
    
    def reset_proxy_stats(self, proxy_url: str = None):
        """
        Reset proxy statistics.
        
        Args:
            proxy_url: Specific proxy URL to reset, or None to reset all
        """
        with self.lock:
            if proxy_url:
                if proxy_url in self.proxy_stats:
                    self.proxy_stats[proxy_url] = {
                        'success_count': 0,
                        'failure_count': 0,
                        'last_used': None,
                        'last_failure': None,
                        'response_times': [],
                        'is_healthy': True
                    }
            else:
                self.proxy_stats.clear()
            
            logger.info(f"Reset proxy statistics: {proxy_url or 'all proxies'}")
    
    def __len__(self):
        """Return number of available proxies."""
        return len(self.proxies)
    
    def __bool__(self):
        """Return True if proxy manager has proxies available."""
        return len(self.proxies) > 0
