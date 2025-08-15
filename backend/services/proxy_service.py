"""
Proxy service to act as middleware between frontend and yt-dlp
This helps bypass YouTube blocking by distributing requests
"""

import asyncio
import aiohttp
import json
import re
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
import random

logger = logging.getLogger(__name__)

class YouTubeProxyService:
    def __init__(self):
        self.session = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
    
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def fetch_video_metadata(self, url: str, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Fetch basic video metadata directly from YouTube"""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                raise Exception("Could not extract video ID from URL")
            
            session = await self.get_session()
            headers = {
                'User-Agent': user_agent or random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Try multiple endpoints
            endpoints = [
                f'https://www.youtube.com/watch?v={video_id}',
                f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json',
                f'https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}'
            ]
            
            metadata = {}
            
            for endpoint in endpoints:
                try:
                    async with session.get(endpoint, headers=headers) as response:
                        if response.status == 200:
                            if 'oembed' in endpoint or 'noembed' in endpoint:
                                # JSON response
                                data = await response.json()
                                metadata.update({
                                    'title': data.get('title'),
                                    'author_name': data.get('author_name'),
                                    'thumbnail_url': data.get('thumbnail_url'),
                                    'duration': data.get('duration'),
                                    'provider_name': data.get('provider_name')
                                })
                            else:
                                # HTML response - extract from page
                                html = await response.text()
                                metadata.update(self._extract_from_html(html))
                            
                            logger.info(f"Successfully fetched metadata from {endpoint}")
                            break
                except Exception as e:
                    logger.warning(f"Failed to fetch from {endpoint}: {e}")
                    continue
            
            return {
                'video_id': video_id,
                'url': url,
                'metadata': metadata,
                'status': 'success' if metadata else 'partial'
            }
            
        except Exception as e:
            logger.error(f"Error fetching video metadata: {e}")
            return {
                'video_id': video_id if 'video_id' in locals() else None,
                'url': url,
                'metadata': {},
                'status': 'error',
                'error': str(e)
            }
    
    def _extract_from_html(self, html: str) -> Dict[str, Any]:
        """Extract metadata from YouTube HTML page"""
        metadata = {}
        
        try:
            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', html)
            if title_match:
                title = title_match.group(1).replace(' - YouTube', '')
                metadata['title'] = title
            
            # Extract from meta tags
            meta_patterns = {
                'title': r'<meta property="og:title" content="([^"]+)"',
                'description': r'<meta property="og:description" content="([^"]+)"',
                'thumbnail': r'<meta property="og:image" content="([^"]+)"',
                'duration': r'<meta property="video:duration" content="([^"]+)"',
                'author': r'<meta name="author" content="([^"]+)"'
            }
            
            for key, pattern in meta_patterns.items():
                match = re.search(pattern, html)
                if match:
                    metadata[key] = match.group(1)
            
            # Extract JSON-LD data
            json_ld_match = re.search(r'<script type="application/ld\+json">([^<]+)</script>', html)
            if json_ld_match:
                try:
                    json_data = json.loads(json_ld_match.group(1))
                    if isinstance(json_data, list):
                        json_data = json_data[0]
                    
                    metadata.update({
                        'name': json_data.get('name'),
                        'description': json_data.get('description'),
                        'uploadDate': json_data.get('uploadDate'),
                        'duration': json_data.get('duration')
                    })
                except json.JSONDecodeError:
                    pass
            
        except Exception as e:
            logger.warning(f"Error extracting from HTML: {e}")
        
        return metadata
    
    async def get_video_info_with_proxy(self, url: str, video_data: Optional[Dict] = None, 
                                      user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Get video info using proxy approach"""
        try:
            # Step 1: Fetch metadata if not provided
            if not video_data:
                video_data = await self.fetch_video_metadata(url, user_agent)
            
            # Step 2: Prepare enhanced data for yt-dlp
            enhanced_data = {
                'url': url,
                'proxy_metadata': video_data,
                'user_agent': user_agent or random.choice(self.user_agents),
                'headers': {
                    'User-Agent': user_agent or random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.youtube.com/',
                    'Origin': 'https://www.youtube.com'
                }
            }
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error in proxy video info: {e}")
            raise Exception(f"Proxy service failed: {str(e)}")

# Global proxy service instance
proxy_service = YouTubeProxyService()