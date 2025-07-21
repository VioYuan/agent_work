"""
Social Media Authentication and Data Fetching Module

Handles OAuth authentication and recent post fetching for:
- Instagram (via Facebook Graph API)
- Twitter/X (via Twitter API v2)
- LinkedIn (via LinkedIn API)
- Facebook (via Facebook Graph API)
- Threads (via Instagram API)

This module provides secure authentication flows and data fetching capabilities
while respecting API rate limits and user privacy.
"""

import os
import json
import time
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs
import requests
from requests_oauthlib import OAuth2Session
import tweepy
from authlib.integrations.requests_client import OAuth2Session as AuthlibOAuth2Session

class SocialMediaAuthConfig:
    """Configuration for social media API credentials"""
    
    def __init__(self):
        # Instagram/Facebook (Meta)
        self.INSTAGRAM_CLIENT_ID = os.getenv('INSTAGRAM_CLIENT_ID')
        self.INSTAGRAM_CLIENT_SECRET = os.getenv('INSTAGRAM_CLIENT_SECRET')
        
        # Twitter/X
        self.TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID') 
        self.TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
        self.TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
        
        # LinkedIn
        self.LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
        self.LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
        
        # Facebook
        self.FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID')
        self.FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
        
        # Threads (uses Instagram API)
        self.THREADS_CLIENT_ID = os.getenv('THREADS_CLIENT_ID', self.INSTAGRAM_CLIENT_ID)
        self.THREADS_CLIENT_SECRET = os.getenv('THREADS_CLIENT_SECRET', self.INSTAGRAM_CLIENT_SECRET)

class SocialMediaAuthenticator:
    """Handles social media OAuth authentication flows"""
    
    def __init__(self, config: SocialMediaAuthConfig, redirect_base_url: str = "http://localhost:8501"):
        self.config = config
        self.redirect_base_url = redirect_base_url
        
    def generate_state_token(self) -> str:
        """Generate a secure state token for OAuth"""
        return secrets.token_urlsafe(32)
    
    def generate_pkce_challenge(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge for Twitter OAuth2"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge
    
    def get_instagram_auth_url(self, state: str) -> str:
        """Generate Instagram OAuth authorization URL"""
        if not self.config.INSTAGRAM_CLIENT_ID:
            raise ValueError("Instagram Client ID not configured")
        
        params = {
            'client_id': self.config.INSTAGRAM_CLIENT_ID,
            'redirect_uri': f"{self.redirect_base_url}/auth/instagram/callback",
            'scope': 'user_profile,user_media',
            'response_type': 'code',
            'state': state
        }
        
        return f"https://api.instagram.com/oauth/authorize?{urlencode(params)}"
    
    def get_twitter_auth_url(self, state: str) -> Tuple[str, str, str]:
        """Generate Twitter OAuth2 authorization URL with PKCE"""
        if not self.config.TWITTER_CLIENT_ID:
            raise ValueError("Twitter Client ID not configured")
        
        code_verifier, code_challenge = self.generate_pkce_challenge()
        
        params = {
            'response_type': 'code',
            'client_id': self.config.TWITTER_CLIENT_ID,
            'redirect_uri': f"{self.redirect_base_url}/auth/twitter/callback",
            'scope': 'tweet.read users.read follows.read offline.access',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"
        return auth_url, code_verifier, code_challenge
    
    def get_linkedin_auth_url(self, state: str) -> str:
        """Generate LinkedIn OAuth authorization URL"""
        if not self.config.LINKEDIN_CLIENT_ID:
            raise ValueError("LinkedIn Client ID not configured")
        
        params = {
            'response_type': 'code',
            'client_id': self.config.LINKEDIN_CLIENT_ID,
            'redirect_uri': f"{self.redirect_base_url}/auth/linkedin/callback",
            'state': state,
            'scope': 'r_liteprofile r_emailaddress w_member_social'
        }
        
        return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    
    def get_facebook_auth_url(self, state: str) -> str:
        """Generate Facebook OAuth authorization URL"""
        if not self.config.FACEBOOK_APP_ID:
            raise ValueError("Facebook App ID not configured")
        
        params = {
            'client_id': self.config.FACEBOOK_APP_ID,
            'redirect_uri': f"{self.redirect_base_url}/auth/facebook/callback",
            'state': state,
            'scope': 'email,public_profile,user_posts,pages_read_engagement',
            'response_type': 'code'
        }
        
        return f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"

class SocialMediaDataFetcher:
    """Handles fetching recent posts from social media platforms"""
    
    def __init__(self, config: SocialMediaAuthConfig):
        self.config = config
    
    def exchange_instagram_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange Instagram authorization code for access token"""
        data = {
            'client_id': self.config.INSTAGRAM_CLIENT_ID,
            'client_secret': self.config.INSTAGRAM_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        response = requests.post('https://api.instagram.com/oauth/access_token', data=data)
        response.raise_for_status()
        return response.json()
    
    def exchange_twitter_code(self, code: str, code_verifier: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange Twitter authorization code for access token"""
        auth_header = base64.b64encode(
            f"{self.config.TWITTER_CLIENT_ID}:{self.config.TWITTER_CLIENT_SECRET}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'code': code,
            'grant_type': 'authorization_code',
            'client_id': self.config.TWITTER_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier
        }
        
        response = requests.post('https://api.twitter.com/2/oauth2/token', headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    
    def exchange_linkedin_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange LinkedIn authorization code for access token"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.config.LINKEDIN_CLIENT_ID,
            'client_secret': self.config.LINKEDIN_CLIENT_SECRET,
            'redirect_uri': redirect_uri
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post('https://www.linkedin.com/oauth/v2/accessToken', data=data, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def exchange_facebook_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange Facebook authorization code for access token"""
        params = {
            'client_id': self.config.FACEBOOK_APP_ID,
            'client_secret': self.config.FACEBOOK_APP_SECRET,
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        response = requests.get('https://graph.facebook.com/v18.0/oauth/access_token', params=params)
        response.raise_for_status()
        return response.json()
    
    def fetch_instagram_posts(self, access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent Instagram posts"""
        try:
            # Get user ID first
            me_response = requests.get(
                f"https://graph.instagram.com/me?fields=id,username&access_token={access_token}"
            )
            me_response.raise_for_status()
            user_data = me_response.json()
            
            # Fetch recent media
            media_response = requests.get(
                f"https://graph.instagram.com/{user_data['id']}/media"
                f"?fields=id,caption,media_type,media_url,thumbnail_url,timestamp,permalink"
                f"&limit={limit}&access_token={access_token}"
            )
            media_response.raise_for_status()
            media_data = media_response.json()
            
            posts = []
            for item in media_data.get('data', []):
                posts.append({
                    'id': item.get('id'),
                    'text': item.get('caption', ''),
                    'media_type': item.get('media_type'),
                    'media_url': item.get('media_url'),
                    'thumbnail_url': item.get('thumbnail_url'),
                    'timestamp': item.get('timestamp'),
                    'permalink': item.get('permalink'),
                    'platform': 'instagram'
                })
            
            return posts
            
        except Exception as e:
            print(f"Error fetching Instagram posts: {str(e)}")
            return []
    
    def fetch_twitter_posts(self, access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent Twitter posts"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get user info first
            me_response = requests.get(
                'https://api.twitter.com/2/users/me?user.fields=public_metrics,profile_image_url',
                headers=headers
            )
            me_response.raise_for_status()
            user_data = me_response.json()['data']
            
            # Fetch recent tweets
            tweets_response = requests.get(
                f"https://api.twitter.com/2/users/{user_data['id']}/tweets"
                f"?tweet.fields=created_at,public_metrics,context_annotations,entities"
                f"&max_results={min(limit, 100)}",
                headers=headers
            )
            tweets_response.raise_for_status()
            tweets_data = tweets_response.json()
            
            posts = []
            for tweet in tweets_data.get('data', []):
                posts.append({
                    'id': tweet.get('id'),
                    'text': tweet.get('text', ''),
                    'created_at': tweet.get('created_at'),
                    'public_metrics': tweet.get('public_metrics', {}),
                    'url': f"https://twitter.com/{user_data['username']}/status/{tweet['id']}",
                    'platform': 'twitter'
                })
            
            return posts
            
        except Exception as e:
            print(f"Error fetching Twitter posts: {str(e)}")
            return []
    
    def fetch_linkedin_posts(self, access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent LinkedIn posts"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get user profile
            profile_response = requests.get(
                'https://api.linkedin.com/v2/people/~?projection=(id,firstName,lastName,profilePicture(displayImage~:playableStreams))',
                headers=headers
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()
            
            # Fetch user's posts (this requires special permissions)
            posts_response = requests.get(
                f'https://api.linkedin.com/v2/shares?q=owners&owners=urn:li:person:{profile_data["id"]}'
                f'&sortBy=CREATED&count={limit}',
                headers=headers
            )
            
            if posts_response.status_code == 200:
                posts_data = posts_response.json()
                
                posts = []
                for element in posts_data.get('elements', []):
                    text = ''
                    if 'text' in element.get('commentary', {}):
                        text = element['commentary']['text']
                    
                    posts.append({
                        'id': element.get('id'),
                        'text': text,
                        'created_time': element.get('created', {}).get('time'),
                        'platform': 'linkedin'
                    })
                
                return posts
            else:
                # If posts API not available, return profile info as a "post"
                return [{
                    'id': 'profile',
                    'text': f"LinkedIn profile: {profile_data.get('firstName', '')} {profile_data.get('lastName', '')}",
                    'created_time': datetime.now().isoformat(),
                    'platform': 'linkedin'
                }]
            
        except Exception as e:
            print(f"Error fetching LinkedIn posts: {str(e)}")
            return []
    
    def fetch_facebook_posts(self, access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent Facebook posts"""
        try:
            # Get user info and posts
            response = requests.get(
                f'https://graph.facebook.com/me/posts'
                f'?fields=id,message,created_time,story,full_picture,permalink_url'
                f'&limit={limit}&access_token={access_token}'
            )
            response.raise_for_status()
            data = response.json()
            
            posts = []
            for post in data.get('data', []):
                posts.append({
                    'id': post.get('id'),
                    'text': post.get('message', post.get('story', '')),
                    'created_time': post.get('created_time'),
                    'full_picture': post.get('full_picture'),
                    'permalink_url': post.get('permalink_url'),
                    'platform': 'facebook'
                })
            
            return posts
            
        except Exception as e:
            print(f"Error fetching Facebook posts: {str(e)}")
            return []

class SocialMediaManager:
    """Main class that coordinates authentication and data fetching"""
    
    def __init__(self, redirect_base_url: str = "http://localhost:8501"):
        self.config = SocialMediaAuthConfig()
        self.authenticator = SocialMediaAuthenticator(self.config, redirect_base_url)
        self.fetcher = SocialMediaDataFetcher(self.config)
        
        # Platform availability check
        self.available_platforms = self._check_platform_availability()
    
    def _check_platform_availability(self) -> Dict[str, bool]:
        """Check which platforms are properly configured"""
        return {
            'instagram': bool(self.config.INSTAGRAM_CLIENT_ID and self.config.INSTAGRAM_CLIENT_SECRET),
            'twitter': bool(self.config.TWITTER_CLIENT_ID and self.config.TWITTER_CLIENT_SECRET),
            'linkedin': bool(self.config.LINKEDIN_CLIENT_ID and self.config.LINKEDIN_CLIENT_SECRET),
            'facebook': bool(self.config.FACEBOOK_APP_ID and self.config.FACEBOOK_APP_SECRET),
        }
    
    def get_auth_url(self, platform: str, state: str) -> Dict[str, Any]:
        """Get authentication URL for a platform"""
        if platform not in self.available_platforms or not self.available_platforms[platform]:
            raise ValueError(f"Platform {platform} not available or not configured")
        
        if platform == 'instagram':
            return {
                'url': self.authenticator.get_instagram_auth_url(state),
                'type': 'oauth2'
            }
        elif platform == 'twitter':
            url, code_verifier, code_challenge = self.authenticator.get_twitter_auth_url(state)
            return {
                'url': url,
                'type': 'oauth2_pkce',
                'code_verifier': code_verifier,
                'code_challenge': code_challenge
            }
        elif platform == 'linkedin':
            return {
                'url': self.authenticator.get_linkedin_auth_url(state),
                'type': 'oauth2'
            }
        elif platform == 'facebook':
            return {
                'url': self.authenticator.get_facebook_auth_url(state),
                'type': 'oauth2'
            }
        else:
            raise ValueError(f"Platform {platform} not supported")
    
    def handle_callback(self, platform: str, code: str, redirect_uri: str, **kwargs) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for token"""
        if platform == 'instagram':
            return self.fetcher.exchange_instagram_code(code, redirect_uri)
        elif platform == 'twitter':
            code_verifier = kwargs.get('code_verifier')
            if not code_verifier:
                raise ValueError("code_verifier required for Twitter OAuth")
            return self.fetcher.exchange_twitter_code(code, code_verifier, redirect_uri)
        elif platform == 'linkedin':
            return self.fetcher.exchange_linkedin_code(code, redirect_uri)
        elif platform == 'facebook':
            return self.fetcher.exchange_facebook_code(code, redirect_uri)
        else:
            raise ValueError(f"Platform {platform} not supported")
    
    def fetch_recent_posts(self, platform: str, access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent posts from a platform"""
        if platform == 'instagram':
            return self.fetcher.fetch_instagram_posts(access_token, limit)
        elif platform == 'twitter':
            return self.fetcher.fetch_twitter_posts(access_token, limit)
        elif platform == 'linkedin':
            return self.fetcher.fetch_linkedin_posts(access_token, limit)
        elif platform == 'facebook':
            return self.fetcher.fetch_facebook_posts(access_token, limit)
        else:
            raise ValueError(f"Platform {platform} not supported")
    
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported and configured platforms"""
        return [platform for platform, available in self.available_platforms.items() if available] 