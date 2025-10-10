"""
SMGI Backend - ArcGIS REST API Client
Sistema de Monitoreo Geoespacial Inteligente
Cliente profesional para interactuar con servicios ArcGIS REST API
"""
import requests
import logging
import time
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from django.core.cache import cache
from django.conf import settings


logger = logging.getLogger('apps.gis_services')


class ArcGISClientError(Exception):
    """Base exception for ArcGIS client errors"""
    pass


class ArcGISAuthenticationError(ArcGISClientError):
    """Authentication related errors"""
    pass


class ArcGISConnectionError(ArcGISClientError):
    """Connection related errors"""
    pass


class ArcGISClient:
    """
    Professional client for ArcGIS REST API
    Handles authentication, requests, retries, and error handling
    """
    
    def __init__(self, service=None, base_url=None, timeout=30):
        """
        Initialize ArcGIS client
        
        Args:
            service: ArcGISService model instance
            base_url: Alternative base URL if service not provided
            timeout: Request timeout in seconds
        """
        self.service = service
        self.base_url = service.base_url if service else base_url
        self.timeout = timeout or (service.timeout_seconds if service else 30)
        self.token = None
        self.token_expiry = None
        
        # Configure session with retry strategy
        self.session = self._create_session()
        
        # Get ArcGIS settings
        self.config = getattr(settings, 'ARCGIS_SETTINGS', {})
        self.max_retries = self.config.get('MAX_RETRIES', 3)
        self.retry_delay = self.config.get('RETRY_DELAY', 1)
        
        logger.debug(f"Initialized ArcGIS client for: {self.base_url}")
    
    def _create_session(self):
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': self.config.get('USER_AGENT', 'SMGI-Backend/1.0'),
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        return session
    
    def _get_cache_key(self, key_type, *args):
        """Generate cache key for caching responses"""
        service_id = self.service.id if self.service else 'generic'
        return f"arcgis_{service_id}_{key_type}_{'_'.join(str(arg) for arg in args)}"
    
    def _authenticate(self):
        """
        Authenticate with ArcGIS service and get token
        Supports multiple authentication methods
        """
        if not self.service or not self.service.requires_authentication:
            return None
        
        # Check if we have valid cached token
        if self.service.token and not self.service.needs_token_refresh:
            logger.debug("Using cached token")
            return self.service.token
        
        logger.info(f"Authenticating with ArcGIS service: {self.service.name}")
        
        try:
            # Check if service has credentials
            if not hasattr(self.service, 'credentials'):
                logger.warning(f"Service {self.service.name} requires auth but has no credentials")
                return None
            
            credentials = self.service.credentials
            
            # Determine authentication URL
            auth_url = credentials.auth_url or urljoin(self.base_url, '/generateToken')
            
            # Prepare authentication payload
            auth_data = {
                'username': credentials.username,
                'password': credentials.password,
                'f': 'json',
                'expiration': 60,  # Token valid for 60 minutes
                'client': 'referer',
                'referer': self.base_url
            }
            
            # Make authentication request
            response = self.session.post(
                auth_url,
                data=auth_data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            auth_response = response.json()
            
            # Check for errors in response
            if 'error' in auth_response:
                error_msg = auth_response['error'].get('message', 'Unknown authentication error')
                logger.error(f"Authentication failed: {error_msg}")
                raise ArcGISAuthenticationError(error_msg)
            
            # Extract token
            token = auth_response.get('token')
            expires = auth_response.get('expires')
            
            if not token:
                raise ArcGISAuthenticationError("No token in authentication response")
            
            # Update service credentials with new token
            from django.utils import timezone
            credentials.access_token = token
            credentials.token_created_at = timezone.now()
            credentials.expires_in = expires
            credentials.save(update_fields=['access_token', 'token_created_at', 'expires_in'])
            
            # Update service token
            self.service.token = token
            self.service.token_expires = timezone.now() + timezone.timedelta(seconds=expires)
            self.service.save(update_fields=['token', 'token_expires'])
            
            self.token = token
            self.token_expiry = expires
            
            logger.info(f"Successfully authenticated with ArcGIS service: {self.service.name}")
            return token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during authentication: {e}")
            raise ArcGISConnectionError(f"Failed to connect to authentication service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise ArcGISAuthenticationError(f"Authentication failed: {e}")
    
    def _make_request(self, method, url, params=None, data=None, use_cache=True, cache_timeout=300):
        """
        Make HTTP request to ArcGIS service with error handling and caching
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            data: POST data
            use_cache: Whether to use caching
            cache_timeout: Cache timeout in seconds
        
        Returns:
            Response JSON data
        """
        # Prepare parameters
        params = params or {}
        params['f'] = 'json'  # Always request JSON format
        
        # Add authentication token if available
        if self.service and self.service.requires_authentication:
            token = self._authenticate()
            if token:
                params['token'] = token
        
        # Generate cache key
        cache_key = self._get_cache_key('request', method, url, json.dumps(params, sort_keys=True))
        
        # Check cache for GET requests
        if method.upper() == 'GET' and use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Returning cached response for: {url}")
                return cached_data
        
        # Make request with retries
        max_attempts = self.max_retries + 1
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                logger.debug(f"Making {method} request to: {url} (attempt {attempt + 1}/{max_attempts})")
                
                start_time = time.time()
                
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, timeout=self.timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, params=params, data=data, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Check response status
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    response_data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from {url}: {e}")
                    raise ArcGISClientError(f"Invalid JSON response: {e}")
                
                # Check for ArcGIS-specific errors
                if 'error' in response_data:
                    error = response_data['error']
                    error_msg = error.get('message', 'Unknown error')
                    error_code = error.get('code', 'unknown')
                    
                    logger.error(f"ArcGIS API error: {error_code} - {error_msg}")
                    
                    # Handle specific error codes
                    if error_code == 498:  # Invalid token
                        logger.warning("Token expired, re-authenticating...")
                        if self.service:
                            self.service.token = None
                            self.service.save(update_fields=['token'])
                        if attempt < max_attempts - 1:
                            continue  # Retry with new token
                    
                    raise ArcGISClientError(f"ArcGIS error {error_code}: {error_msg}")
                
                # Record successful request metrics
                if self.service:
                    from apps.gis_services.models import ServiceMetrics
                    ServiceMetrics.record_request(
                        service=self.service,
                        endpoint=url,
                        method=method,
                        response_time_ms=response_time,
                        status_code=response.status_code,
                        success=True,
                        request_size_bytes=len(str(params)),
                        response_size_bytes=len(response.content)
                    )
                
                # Cache successful GET requests
                if method.upper() == 'GET' and use_cache:
                    cache.set(cache_key, response_data, cache_timeout)
                
                logger.debug(f"Request successful in {response_time:.2f}ms")
                return response_data
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
                
                if attempt < max_attempts - 1:
                    sleep_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(f"Request failed on attempt {attempt + 1}: {e}")
                
                if attempt < max_attempts - 1:
                    sleep_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
            
            except ArcGISClientError as e:
                # Don't retry on ArcGIS-specific errors (except token issues)
                last_exception = e
                if 'token' not in str(e).lower():
                    break
        
        # Record failed request metrics
        if self.service:
            from apps.gis_services.models import ServiceMetrics
            ServiceMetrics.record_request(
                service=self.service,
                endpoint=url,
                method=method,
                response_time_ms=0,
                status_code=0,
                success=False,
                error_message=str(last_exception)
            )
        
        # All retries failed
        logger.error(f"All {max_attempts} attempts failed for {url}")
        raise ArcGISConnectionError(f"Failed after {max_attempts} attempts: {last_exception}")
    
    def get_service_info(self, use_cache=True):
        """
        Get service information
        
        Returns:
            Dict with service metadata
        """
        url = self.base_url.rstrip('/')
        
        try:
            logger.info(f"Getting service info from: {url}")
            response = self._make_request('GET', url, use_cache=use_cache)
            
            return {
                'name': response.get('serviceDescription', response.get('name', 'Unknown')),
                'description': response.get('description', ''),
                'type': response.get('type', 'Unknown'),
                'capabilities': response.get('capabilities', '').split(','),
                'layers': response.get('layers', []),
                'tables': response.get('tables', []),
                'spatialReference': response.get('spatialReference', {}),
                'initialExtent': response.get('initialExtent', {}),
                'fullExtent': response.get('fullExtent', {}),
                'supportedQueryFormats': response.get('supportedQueryFormats', ''),
                'maxRecordCount': response.get('maxRecordCount', 1000),
                'currentVersion': response.get('currentVersion', 'Unknown'),
            }
            
        except Exception as e:
            logger.error(f"Error getting service info: {e}")
            raise
    
    def get_layer_info(self, layer_id, use_cache=True):
        """
        Get information about a specific layer
        
        Args:
            layer_id: Layer ID
            use_cache: Whether to use caching
        
        Returns:
            Dict with layer information
        """
        url = urljoin(self.base_url.rstrip('/') + '/', str(layer_id))
        
        try:
            logger.info(f"Getting layer info for layer {layer_id}")
            response = self._make_request('GET', url, use_cache=use_cache)
            
            return {
                'id': response.get('id'),
                'name': response.get('name'),
                'type': response.get('type'),
                'description': response.get('description', ''),
                'geometryType': response.get('geometryType'),
                'copyrightText': response.get('copyrightText', ''),
                'minScale': response.get('minScale'),
                'maxScale': response.get('maxScale'),
                'extent': response.get('extent', {}),
                'fields': response.get('fields', []),
                'relationships': response.get('relationships', []),
                'capabilities': response.get('capabilities', ''),
                'maxRecordCount': response.get('maxRecordCount', 1000),
                'supportedQueryFormats': response.get('supportedQueryFormats', ''),
                'supportsStatistics': response.get('supportsStatistics', False),
                'supportsAdvancedQueries': response.get('supportsAdvancedQueries', False),
                'hasAttachments': response.get('hasAttachments', False),
            }
            
        except Exception as e:
            logger.error(f"Error getting layer info for layer {layer_id}: {e}")
            raise
    
    def query_layer(self, layer_id, where='1=1', out_fields='*', return_geometry=False, 
                   return_count_only=False, result_offset=0, result_record_count=None):
        """
        Query layer features
        
        Args:
            layer_id: Layer ID
            where: SQL where clause
            out_fields: Fields to return
            return_geometry: Whether to return geometry
            return_count_only: Only return feature count
            result_offset: Pagination offset
            result_record_count: Number of records to return
        
        Returns:
            Query results
        """
        url = urljoin(self.base_url.rstrip('/') + '/', f"{layer_id}/query")
        
        params = {
            'where': where,
            'outFields': out_fields,
            'returnGeometry': 'true' if return_geometry else 'false',
            'returnCountOnly': 'true' if return_count_only else 'false',
            'resultOffset': result_offset,
        }
        
        if result_record_count:
            params['resultRecordCount'] = result_record_count
        
        try:
            logger.info(f"Querying layer {layer_id} with where clause: {where}")
            response = self._make_request('GET', url, params=params, use_cache=False)
            
            if return_count_only:
                return {
                    'count': response.get('count', 0)
                }
            
            return {
                'features': response.get('features', []),
                'count': len(response.get('features', [])),
                'exceededTransferLimit': response.get('exceededTransferLimit', False),
                'geometryType': response.get('geometryType'),
                'spatialReference': response.get('spatialReference', {}),
            }
            
        except Exception as e:
            logger.error(f"Error querying layer {layer_id}: {e}")
            raise
    
    def get_feature_count(self, layer_id, where='1=1'):
        """
        Get feature count for a layer
        
        Args:
            layer_id: Layer ID
            where: SQL where clause
        
        Returns:
            int: Feature count
        """
        try:
            result = self.query_layer(layer_id, where=where, return_count_only=True)
            return result.get('count', 0)
        except Exception as e:
            logger.error(f"Error getting feature count for layer {layer_id}: {e}")
            return 0
    
    def get_all_features(self, layer_id, where='1=1', out_fields='*', batch_size=1000):
        """
        Get all features from a layer, handling pagination
        
        Args:
            layer_id: Layer ID
            where: SQL where clause
            out_fields: Fields to return
            batch_size: Number of features per request
        
        Yields:
            Feature dictionaries
        """
        offset = 0
        total_fetched = 0
        
        while True:
            try:
                result = self.query_layer(
                    layer_id,
                    where=where,
                    out_fields=out_fields,
                    return_geometry=True,
                    result_offset=offset,
                    result_record_count=batch_size
                )
                
                features = result.get('features', [])
                
                if not features:
                    break
                
                for feature in features:
                    yield feature
                    total_fetched += 1
                
                # Check if we've reached the end
                if not result.get('exceededTransferLimit', False):
                    break
                
                offset += batch_size
                logger.debug(f"Fetched {total_fetched} features so far...")
                
            except Exception as e:
                logger.error(f"Error fetching features at offset {offset}: {e}")
                break
        
        logger.info(f"Fetched total of {total_fetched} features from layer {layer_id}")
    
    def test_connection(self):
        """
        Test connection to ArcGIS service
        
        Returns:
            Tuple of (bool, str): (success, message)
        """
        try:
            logger.info(f"Testing connection to: {self.base_url}")
            
            # Try to get service info
            info = self.get_service_info(use_cache=False)
            
            return (True, f"Successfully connected to {info.get('name', 'service')}")
            
        except ArcGISConnectionError as e:
            return (False, f"Connection failed: {e}")
        except ArcGISAuthenticationError as e:
            return (False, f"Authentication failed: {e}")
        except Exception as e:
            return (False, f"Unexpected error: {e}")
    
    def close(self):
        """Close the client session"""
        if self.session:
            self.session.close()
            logger.debug("ArcGIS client session closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()