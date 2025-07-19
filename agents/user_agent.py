from typing import Dict, Any
from langchain.tools import BaseTool
from langchain_community.tools.requests.tool import RequestsGetTool
from langchain_community.utilities.requests import TextRequestsWrapper
from bs4 import BeautifulSoup
from pydantic import Field
from langchain_core.language_models import BaseLanguageModel
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
import asyncio
import concurrent.futures
import re
import requests
import urllib.parse
from .base_agent import BaseAgent
import json

class ProfileAnalysisTool(BaseTool):
    name: str = "profile_analysis"
    description: str = "Analyzes user profile data and provides insights"
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, profile: Dict[str, Any]) -> str:
        # Quick validation and formatting without LLM for basic profiles
        name = profile.get('name', 'Not provided')
        age = profile.get('age', 'Not provided')
        interests = profile.get('interests', 'Not provided')
        
        # If profile is minimal, return a quick template-based response
        if not interests or interests == 'Not provided':
            return f"""KEY INTERESTS:
- General conversation
- Getting to know new topics

PERSONALITY TRAITS:
- Open to new experiences
- Curious about different subjects

CONVERSATION TOPICS:
- Current events and news
- Hobbies and personal interests
- Technology and innovation"""
        
        # Only use LLM for complex profiles with substantial content
        if len(str(interests)) > 50:
            prompt = f"""OMG, I'm SO excited to analyze this amazing person! 🎉✨ Let me dive into their awesome profile!

Name: {name} (what a great name! 😄), Age: {age}, Occupation: {profile.get('occupation', 'Not specified')}, Interests: {interests}

I need to create an ENERGETIC and POSITIVE analysis! Please format it like this:

KEY INTERESTS: [2-3 main interests with enthusiasm!]
PERSONALITY TRAITS: [2-3 positive traits with energy!]
CONVERSATION TOPICS: [2-3 exciting topics to chat about!]

Make it sound fun, warm, and exciting! Use lots of positive energy! 🌸🎊"""
            
            analysis = self.llm.invoke(prompt)
            if hasattr(analysis, 'content'):
                analysis = analysis.content
            return str(analysis)
        else:
            # Template-based response for simple interests
            interests_list = str(interests).split(',')[:3]
            return f"""KEY INTERESTS:
{chr(10).join(f'- {interest.strip()}' for interest in interests_list)}

PERSONALITY TRAITS:
- Engaged and interested
- Values personal connections

CONVERSATION TOPICS:
{chr(10).join(f'- {interest.strip()}-related discussions' for interest in interests_list[:2])}
- Personal experiences and stories"""
    
    async def _arun(self, profile: Dict[str, Any]) -> str:
        return self._run(profile)

class SocialMediaAnalysisTool(BaseTool):
    name: str = "social_media_analysis"
    description: str = "Analyzes social media content from provided URLs"
    requests: RequestsGetTool = Field(default=None)
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        requests_wrapper = TextRequestsWrapper()
        self.requests = RequestsGetTool(requests_wrapper=requests_wrapper, allow_dangerous_requests=True)
    
    def _get_platform_info(self, url: str) -> Dict[str, str]:
        """Extract platform information from URL"""
        url_lower = url.lower()
        if 'instagram.com' in url_lower:
            return {'platform': 'Instagram', 'type': 'photo/video sharing', 'blocked': True}
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return {'platform': 'Twitter/X', 'type': 'microblogging', 'blocked': True}
        elif 'threads.com' in url_lower:
            return {'platform': 'Threads', 'type': 'text-based social', 'blocked': True}
        elif 'linkedin.com' in url_lower:
            return {'platform': 'LinkedIn', 'type': 'professional networking', 'blocked': False}
        elif 'facebook.com' in url_lower:
            return {'platform': 'Facebook', 'type': 'social networking', 'blocked': True}
        elif 'tiktok.com' in url_lower:
            return {'platform': 'TikTok', 'type': 'short video content', 'blocked': True}
        elif 'youtube.com' in url_lower:
            return {'platform': 'YouTube', 'type': 'video content', 'blocked': False}
        else:
            return {'platform': 'Unknown', 'type': 'social media', 'blocked': False}
    
    def _fallback_scrape(self, url: str) -> str:
        """Fallback scraping method with different strategies"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            # Try with custom headers
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            # If that fails, try with minimal headers
            try:
                simple_headers = {'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0)'}
                response = requests.get(url, headers=simple_headers, timeout=5)
                response.raise_for_status()
                return response.text
            except Exception:
                raise e
    
    def _extract_key_content(self, html_content: str) -> str:
        """Extract only the most relevant content from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check for common error indicators
        text_content = soup.get_text().lower()
        
        # Detect JavaScript-disabled pages
        if any(indicator in text_content for indicator in [
            'javascript is not available',
            'javascript disabled',
            'enable javascript',
            'javascript is required',
            'please enable javascript',
            'javascript must be enabled'
        ]):
            return "JAVASCRIPT_DISABLED_ERROR"
        
        # Detect other common blocking messages
        if any(indicator in text_content for indicator in [
            'access denied',
            'blocked',
            'not authorized',
            'forbidden',
            'rate limit',
            'temporarily unavailable',
            'service unavailable'
        ]):
            return "ACCESS_BLOCKED_ERROR"
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Try to find main content areas
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|post'))
        
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
        
        # Clean and validate text
        text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII characters that might cause encoding issues
        
        # Check if content is meaningful (not just error pages or empty content)
        if len(text.strip()) < 50:
            return "INSUFFICIENT_CONTENT_ERROR"
        
        # Check for repetitive or meaningless content
        words = text.split()
        if len(set(words)) < len(words) * 0.3:  # If less than 30% unique words, likely error page
            return "REPETITIVE_CONTENT_ERROR"
        
        return text[:500]  # Limit to 500 characters for faster processing
    
    def _advanced_url_analysis(self, url: str) -> Dict[str, Any]:
        """Advanced URL analysis to extract maximum information without scraping"""
        parsed_url = urllib.parse.urlparse(url)
        path_parts = [part for part in parsed_url.path.strip('/').split('/') if part]
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        platform_info = self._get_platform_info(url)
        platform = platform_info['platform']
        
        analysis = {
            'platform': platform,
            'username': None,
            'content_type': 'profile',
            'post_id': None,
            'engagement_indicators': [],
            'content_themes': [],
            'activity_level': 'moderate'
        }
        
        if platform == 'Instagram':
            if len(path_parts) > 0:
                analysis['username'] = path_parts[0]
                
                if len(path_parts) > 1:
                    if path_parts[1] == 'p':
                        analysis['content_type'] = 'photo_post'
                        analysis['post_id'] = path_parts[2] if len(path_parts) > 2 else None
                        analysis['engagement_indicators'] = ['visual_content', 'photo_sharing', 'aesthetic_focus']
                    elif path_parts[1] == 'reel':
                        analysis['content_type'] = 'reel'
                        analysis['post_id'] = path_parts[2] if len(path_parts) > 2 else None
                        analysis['engagement_indicators'] = ['video_content', 'trend_participation', 'creative_expression']
                    elif path_parts[1] == 'stories':
                        analysis['content_type'] = 'story'
                        analysis['engagement_indicators'] = ['ephemeral_content', 'daily_updates', 'casual_sharing']
                    elif path_parts[1] == 'tv':
                        analysis['content_type'] = 'igtv'
                        analysis['engagement_indicators'] = ['long_form_video', 'educational_content', 'storytelling']
                    else:
                        analysis['content_type'] = 'profile_section'
                
                # Analyze username patterns for insights
                username = analysis['username'].lower()
                if any(word in username for word in ['official', 'real', 'verified']):
                    analysis['engagement_indicators'].append('official_presence')
                if any(word in username for word in ['art', 'photo', 'pic', 'visual']):
                    analysis['content_themes'].append('visual_arts')
                if any(word in username for word in ['food', 'cook', 'chef', 'recipe']):
                    analysis['content_themes'].append('food_lifestyle')
                if any(word in username for word in ['fit', 'gym', 'health', 'workout']):
                    analysis['content_themes'].append('fitness_health')
                if any(word in username for word in ['travel', 'adventure', 'explore']):
                    analysis['content_themes'].append('travel_lifestyle')
                if any(word in username for word in ['business', 'entrepreneur', 'ceo', 'founder']):
                    analysis['content_themes'].append('business_professional')
        
        elif platform == 'Twitter/X':
            if len(path_parts) > 0:
                analysis['username'] = path_parts[0]
                
                if len(path_parts) > 1:
                    if path_parts[1] == 'status':
                        analysis['content_type'] = 'tweet'
                        analysis['post_id'] = path_parts[2] if len(path_parts) > 2 else None
                        analysis['engagement_indicators'] = ['real_time_sharing', 'opinion_expression', 'news_discussion']
                    elif path_parts[1] == 'with_replies':
                        analysis['content_type'] = 'replies'
                        analysis['engagement_indicators'] = ['conversational', 'community_engagement', 'responsive']
                    elif path_parts[1] == 'media':
                        analysis['content_type'] = 'media_tweets'
                        analysis['engagement_indicators'] = ['visual_sharing', 'multimedia_content', 'creative_posts']
                    elif path_parts[1] == 'likes':
                        analysis['content_type'] = 'liked_tweets'
                        analysis['engagement_indicators'] = ['content_curator', 'trend_follower', 'engaged_reader']
                    elif path_parts[1] == 'following':
                        analysis['content_type'] = 'following_list'
                        analysis['engagement_indicators'] = ['network_builder', 'community_focused', 'social_connector']
                    elif path_parts[1] == 'followers':
                        analysis['content_type'] = 'followers_list'
                        analysis['engagement_indicators'] = ['influence_building', 'thought_leadership', 'community_leader']
                
                # Analyze username patterns
                username = analysis['username'].lower()
                if any(word in username for word in ['news', 'breaking', 'update', 'report']):
                    analysis['content_themes'].append('news_information')
                if any(word in username for word in ['tech', 'dev', 'code', 'programming']):
                    analysis['content_themes'].append('technology')
                if any(word in username for word in ['business', 'ceo', 'entrepreneur', 'startup']):
                    analysis['content_themes'].append('business_leadership')
                if any(word in username for word in ['art', 'design', 'creative', 'artist']):
                    analysis['content_themes'].append('creative_arts')
                if any(word in username for word in ['sports', 'athlete', 'game', 'team']):
                    analysis['content_themes'].append('sports_entertainment')
                if any(word in username for word in ['politics', 'policy', 'government', 'vote']):
                    analysis['content_themes'].append('political_civic')
        
        elif platform == 'LinkedIn':
            if len(path_parts) > 0:
                if path_parts[0] == 'in':
                    analysis['username'] = path_parts[1] if len(path_parts) > 1 else None
                    analysis['content_type'] = 'professional_profile'
                    analysis['engagement_indicators'] = ['career_focused', 'professional_networking', 'industry_engagement']
                elif path_parts[0] == 'company':
                    analysis['username'] = path_parts[1] if len(path_parts) > 1 else None
                    analysis['content_type'] = 'company_page'
                    analysis['engagement_indicators'] = ['business_presence', 'corporate_communication', 'employer_branding']
                elif path_parts[0] == 'posts':
                    analysis['content_type'] = 'post'
                    analysis['engagement_indicators'] = ['thought_leadership', 'professional_insights', 'industry_commentary']
        
        elif platform == 'Threads':
            if len(path_parts) > 0:
                # Threads URL structure: www.threads.com/@username or www.threads.com/@username/post/postid
                if path_parts[0].startswith('@'):
                    analysis['username'] = path_parts[0][1:]  # Remove @ symbol
                    
                    if len(path_parts) > 1:
                        if path_parts[1] == 'post':
                            analysis['content_type'] = 'thread_post'
                            analysis['post_id'] = path_parts[2] if len(path_parts) > 2 else None
                            analysis['engagement_indicators'] = ['text_sharing', 'conversation_starter', 'community_discussion']
                        elif path_parts[1] == 'reply':
                            analysis['content_type'] = 'thread_reply'
                            analysis['engagement_indicators'] = ['conversational', 'responsive', 'community_engagement']
                        else:
                            analysis['content_type'] = 'profile_section'
                    else:
                        analysis['content_type'] = 'profile'
                        analysis['engagement_indicators'] = ['text_focused', 'community_builder', 'authentic_sharing']
                
                # Analyze username patterns for Threads-specific insights
                if analysis['username']:
                    username = analysis['username'].lower()
                    if any(word in username for word in ['creator', 'artist', 'writer', 'author']):
                        analysis['content_themes'].append('creative_content')
                    if any(word in username for word in ['news', 'journalist', 'reporter', 'media']):
                        analysis['content_themes'].append('news_media')
                    if any(word in username for word in ['coach', 'mentor', 'teacher', 'educator']):
                        analysis['content_themes'].append('education_mentoring')
                    if any(word in username for word in ['brand', 'business', 'company', 'official']):
                        analysis['content_themes'].append('brand_business')
                    if any(word in username for word in ['community', 'group', 'collective']):
                        analysis['content_themes'].append('community_building')
        
        # Determine activity level based on content type
        if analysis['content_type'] in ['photo_post', 'reel', 'tweet', 'story', 'thread_post']:
            analysis['activity_level'] = 'high'
        elif analysis['content_type'] in ['profile_section', 'replies', 'media_tweets', 'thread_reply']:
            analysis['activity_level'] = 'moderate'
        else:
            analysis['activity_level'] = 'low'
        
        return analysis
    
    def _generate_intelligent_analysis(self, url: str) -> str:
        """Generate intelligent analysis based on URL structure and patterns"""
        analysis = self._advanced_url_analysis(url)
        platform = analysis['platform']
        username = analysis['username']
        content_type = analysis['content_type']
        engagement_indicators = analysis['engagement_indicators']
        content_themes = analysis['content_themes']
        activity_level = analysis['activity_level']
        
        # Build comprehensive analysis
        result = f"""Platform: {platform}
Username: {username or 'Not detected'}
Content Type: {content_type.replace('_', ' ').title()}
Activity Level: {activity_level.title()}

ENGAGEMENT PATTERNS:"""
        
        if engagement_indicators:
            for indicator in engagement_indicators:
                result += f"\n- {indicator.replace('_', ' ').title()}"
        else:
            result += f"\n- Standard {platform} user behavior"
        
        if content_themes:
            result += f"\n\nCONTENT THEMES:"
            for theme in content_themes:
                result += f"\n- {theme.replace('_', ' ').title()}"
        
        # Add platform-specific insights
        if platform == 'Instagram':
            if content_type == 'photo_post':
                result += f"\n\nINSIGHTS:\n- Shares individual photos/moments\n- Likely focuses on visual storytelling\n- Engages with photo-based content"
            elif content_type == 'reel':
                result += f"\n\nINSIGHTS:\n- Creates short-form video content\n- Participates in trends and challenges\n- Engages with dynamic, creative content"
            elif content_type == 'story':
                result += f"\n\nINSIGHTS:\n- Shares daily updates and behind-the-scenes content\n- Prefers ephemeral, casual communication\n- Maintains regular audience engagement"
            else:
                result += f"\n\nINSIGHTS:\n- Active Instagram user with visual content focus\n- Likely shares lifestyle and personal moments\n- Engages with community through visual media"
        
        elif platform == 'Twitter/X':
            if content_type == 'tweet':
                result += f"\n\nINSIGHTS:\n- Shares specific thoughts and opinions\n- Engages in real-time conversations\n- Participates in trending discussions"
            elif content_type == 'replies':
                result += f"\n\nINSIGHTS:\n- Highly conversational and responsive\n- Builds community through dialogue\n- Values two-way communication"
            elif content_type == 'media_tweets':
                result += f"\n\nINSIGHTS:\n- Combines text with visual content\n- Shares multimedia experiences\n- Engages audiences with rich media"
            else:
                result += f"\n\nINSIGHTS:\n- Active Twitter/X user with opinion-sharing focus\n- Likely engages in current events and discussions\n- Values real-time communication and networking"
        
        elif platform == 'Threads':
            if content_type == 'thread_post':
                result += f"\n\nINSIGHTS:\n- Creates thoughtful, text-based content\n- Engages in meaningful conversations\n- Builds authentic community connections"
            elif content_type == 'thread_reply':
                result += f"\n\nINSIGHTS:\n- Actively participates in discussions\n- Values community engagement and dialogue\n- Responsive to others' content and ideas"
            else:
                result += f"\n\nINSIGHTS:\n- Active Threads user focused on authentic sharing\n- Likely engages in text-based conversations\n- Values community building and meaningful connections"
        
        # Add behavioral predictions
        result += f"\n\nBEHAVIORAL PREDICTIONS:"
        if activity_level == 'high':
            result += f"\n- Frequent poster and active community member\n- Likely responds quickly to messages\n- Stays current with platform trends"
        elif activity_level == 'moderate':
            result += f"\n- Regular but selective posting\n- Thoughtful engagement with content\n- Balanced approach to social media"
        else:
            result += f"\n- Occasional poster, more of a consumer\n- Selective about shared content\n- Values quality over quantity"
        
        return result
    
    def _fetch_url_content(self, url: str) -> tuple:
        """Fetch content from a single URL with intelligent fallback to URL analysis"""
        platform_info = self._get_platform_info(url)
        platform = platform_info['platform']
        
        # For Instagram and Twitter/X, skip scraping entirely and use intelligent analysis
        if platform in ['Instagram', 'Twitter/X', 'Threads']:
            try:
                intelligent_analysis = self._generate_intelligent_analysis(url)
                note = f"""⚠️ CONTENT ANALYSIS FROM URL STRUCTURE ⚠️
{platform} restricts automated content access, but we can analyze the URL structure.

{intelligent_analysis}

Note: This analysis is based on URL patterns and general {platform} user behavior, not actual content."""
                
                return url, note, None
            except Exception as e:
                return url, None, f"{platform} analysis failed: {str(e)}"
        
        # For other platforms, try scraping first
        try:
            # First try: Use RequestsGetTool
            response = self.requests.run(url)
            content = self._extract_key_content(response)
            
            # Check for error conditions
            if content in ["JAVASCRIPT_DISABLED_ERROR", "ACCESS_BLOCKED_ERROR", "INSUFFICIENT_CONTENT_ERROR", "REPETITIVE_CONTENT_ERROR"]:
                raise Exception(f"Content extraction failed: {content}")
            
            if content and len(content.strip()) > 20:
                return url, content, None
            else:
                raise Exception("No meaningful content extracted")
        except Exception as primary_error:
            try:
                # Second try: Fallback scraping with custom headers
                html_content = self._fallback_scrape(url)
                content = self._extract_key_content(html_content)
                
                # Check for error conditions
                if content in ["JAVASCRIPT_DISABLED_ERROR", "ACCESS_BLOCKED_ERROR", "INSUFFICIENT_CONTENT_ERROR", "REPETITIVE_CONTENT_ERROR"]:
                    raise Exception(f"Content extraction failed: {content}")
                
                if content and len(content.strip()) > 20:
                    return url, content, None
                else:
                    raise Exception("No meaningful content extracted")
            except Exception as secondary_error:
                # Final fallback: Use intelligent URL analysis
                try:
                    intelligent_analysis = self._generate_intelligent_analysis(url)
                    note = f"""⚠️ CONTENT NOT ACCESSIBLE - URL ANALYSIS PROVIDED ⚠️
Scraping failed, but we can analyze the URL structure for insights.

{intelligent_analysis}

Note: Analysis based on URL patterns and platform behavior, not actual content."""
                    
                    return url, note, None
                except Exception:
                    return url, None, f"Content not accessible: {str(primary_error)[:100]}"
    
    def _run(self, urls: list) -> str:
        if not urls:
            return "No social media links provided."
        
        # Limit to first 3 URLs for performance
        urls = urls[:3]
        
        # Fetch all URLs concurrently
        contents = []
        errors = []
        analyzed_platforms = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_url = {executor.submit(self._fetch_url_content, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url, content, error = future.result()
                platform_info = self._get_platform_info(url)
                platform = platform_info['platform']
                
                if content:
                    # Check if this is URL-based analysis (for Instagram/Twitter)
                    if "⚠️ CONTENT ANALYSIS FROM URL STRUCTURE ⚠️" in content:
                        analyzed_platforms.append(f"{platform} (URL Analysis)")
                    elif "⚠️ CONTENT NOT ACCESSIBLE" in content:
                        analyzed_platforms.append(f"{platform} (Limited Analysis)")
                    else:
                        analyzed_platforms.append(f"{platform} (Content Scraped)")
                    contents.append(content)
                elif error:
                    errors.append(f"Issue with {platform}: {error}")
                    analyzed_platforms.append(f"{platform} (Failed)")
        
        if not contents and errors:
            # If no content was extracted, provide analysis based on URLs
            platform_analysis = []
            for url in urls:
                platform_info = self._get_platform_info(url)
                try:
                    intelligent_analysis = self._generate_intelligent_analysis(url)
                    platform_analysis.append(f"**{platform_info['platform']}:**\n{intelligent_analysis}")
                except Exception:
                    platform_analysis.append(f"- {platform_info['platform']}: {platform_info['type']}")
            
            return f"""⚠️ SOCIAL MEDIA ANALYSIS FROM URL PATTERNS ⚠️

{chr(10).join(platform_analysis)}

Note: Analysis based on URL structure and platform behavior patterns due to access restrictions."""
        
        if not contents:
            return "⚠️ Unable to analyze social media content due to access restrictions."
        
        # Prepare summary with platform analysis notes
        summary_parts = []
        
        if analyzed_platforms:
            platform_note = f"📊 ANALYSIS METHODS: {', '.join(analyzed_platforms)}"
            summary_parts.append(platform_note)
        
        # Combine all content and analyze in a single LLM call
        combined_content = " ".join(contents)[:3000]  # Increased limit for URL analysis content
        
        prompt = f"""WOW! 🤩 I'm absolutely THRILLED to analyze this person's social media presence! This is going to be SO fun! ✨🎉

Content: {combined_content}

Time to create an AMAZING and ENERGETIC analysis! Please give me:

KEY ACTIVITIES: [main activities with lots of excitement! 🚀]
INTERESTS & THEMES: [super cool interests and themes! 🎨]
ENGAGEMENT STYLE: [how they communicate - make it sound awesome! 💬]
PLATFORM BEHAVIOR: [their platform style with positive vibes! 📱]
PERSONALITY INSIGHTS: [wonderful personality traits - focus on the positives! ✨]

Make this analysis WARM, ENERGETIC, and EXCITING! Use positive language and make it sound like we're discovering something amazing about this fantastic person! Focus on actionable insights that will make conversations more fun! 🌸🎊"""
        
        try:
            summary = self.llm.invoke(prompt)
            if hasattr(summary, 'content'):
                summary = summary.content
            
            # Combine platform notes with LLM summary
            if summary_parts:
                return f"{chr(10).join(summary_parts)}\n\n{str(summary)}"
            else:
                return str(summary)
                
        except Exception as e:
            # Fallback to template-based analysis if LLM fails
            instagram_count = sum(1 for url in urls if 'instagram.com' in url.lower())
            twitter_count = sum(1 for url in urls if any(domain in url.lower() for domain in ['twitter.com', 'x.com']))
            
            base_summary = f"""SOCIAL MEDIA ANALYSIS SUMMARY:

PLATFORMS DETECTED:
- Instagram links: {instagram_count}
- Twitter/X links: {twitter_count}
- Other platforms: {len(urls) - instagram_count - twitter_count}

KEY INSIGHTS:
- Multi-platform social media presence
- Likely engages in visual content (Instagram) and real-time discussions (Twitter/X)
- Active digital communicator across different social networks
- Demonstrates varied online engagement patterns

CONVERSATION TOPICS:
- Social media trends and platforms
- Visual content and photography (if Instagram user)
- Current events and opinions (if Twitter/X user)
- Digital communication preferences"""
            
            if summary_parts:
                return f"{chr(10).join(summary_parts)}\n\n{base_summary}"
            else:
                return f"{base_summary}\n\nNote: Analysis error occurred: {str(e)[:100]}"
    
    async def _arun(self, urls: list) -> str:
        return self._run(urls)

class UserAgent(BaseAgent):
    def __init__(self):
        super().__init__()  # Initialize base class first
        
        # Create tools
        self.tools = [
            ProfileAnalysisTool(llm=self.llm),
            SocialMediaAnalysisTool(llm=self.llm)
        ]
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are Hana-chan's super enthusiastic profile analyzer! 🎯✨ You love discovering awesome things about people and getting excited about their interests and social media! Analyze with energy and positivity! 🌸🎉"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True
        )
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_profile = input_data.get("user_profile", {})
        social_links = input_data.get("social_links", [])
        
        # Process both analyses concurrently for better performance
        profile_task = asyncio.create_task(self.tools[0]._arun(user_profile))
        social_task = asyncio.create_task(self.tools[1]._arun(social_links))
        
        # Wait for both to complete
        profile_analysis, social_analysis = await asyncio.gather(profile_task, social_task)
        
        # Combine the analyses into a comprehensive user context
        user_context = {
            "profile_analysis": profile_analysis,
            "social_analysis": social_analysis,
            "combined_context": f"User Profile: {profile_analysis}\nSocial Media Analysis: {social_analysis}"
        }
        
        return user_context 