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
    name = "profile_analysis"
    description = "Analyzes user profile data and provides insights"
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
            prompt = f"""Analyze this user profile quickly and provide a concise summary:
Name: {name}, Age: {age}, Interests: {interests}

Format:
KEY INTERESTS: [2-3 main interests]
PERSONALITY TRAITS: [2-3 traits]
CONVERSATION TOPICS: [2-3 topics]

Keep it brief and focused."""
            
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
    name = "social_media_analysis"
    description = "Analyzes social media content from provided URLs"
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
    
    def _analyze_url_structure(self, url: str) -> str:
        """Analyze URL structure to extract information when content is blocked"""
        parsed_url = urllib.parse.urlparse(url)
        path_parts = [part for part in parsed_url.path.strip('/').split('/') if part]
        
        platform_info = self._get_platform_info(url)
        platform = platform_info['platform']
        content_type = platform_info['type']
        
        # Extract username/handle and content type
        username = None
        content_hint = None
        
        if platform == 'Instagram':
            if len(path_parts) > 0:
                username = path_parts[0]
                if len(path_parts) > 1:
                    if path_parts[1] == 'p':
                        content_hint = "specific post"
                    elif path_parts[1] == 'reel':
                        content_hint = "reel/video content"
                    elif path_parts[1] == 'stories':
                        content_hint = "story content"
                    else:
                        content_hint = "profile content"
                else:
                    content_hint = "main profile"
        
        elif platform == 'Twitter/X':
            if len(path_parts) > 0:
                username = path_parts[0]
                if len(path_parts) > 1:
                    if path_parts[1] == 'status':
                        content_hint = "specific tweet"
                    elif path_parts[1] == 'with_replies':
                        content_hint = "tweets and replies"
                    elif path_parts[1] == 'media':
                        content_hint = "media tweets"
                    else:
                        content_hint = "profile timeline"
                else:
                    content_hint = "main profile"
        
        elif platform == 'LinkedIn':
            if len(path_parts) > 0:
                if path_parts[0] == 'in':
                    username = path_parts[1] if len(path_parts) > 1 else None
                    content_hint = "professional profile"
                elif path_parts[0] == 'company':
                    username = path_parts[1] if len(path_parts) > 1 else None
                    content_hint = "company page"
        
        elif platform == 'TikTok':
            if len(path_parts) > 0:
                if path_parts[0].startswith('@'):
                    username = path_parts[0]
                    content_hint = "user profile"
                elif len(path_parts) > 1 and path_parts[0].startswith('@'):
                    username = path_parts[0]
                    content_hint = "specific video"
        
        elif platform == 'YouTube':
            if len(path_parts) > 0:
                if path_parts[0] == 'channel' or path_parts[0] == 'c' or path_parts[0] == 'user':
                    username = path_parts[1] if len(path_parts) > 1 else None
                    content_hint = "channel page"
                elif path_parts[0] == 'watch':
                    content_hint = "specific video"
        
        # Build analysis
        analysis = f"Platform: {platform} ({content_type})"
        if username:
            analysis += f"\nProfile/Username: {username}"
        if content_hint:
            analysis += f"\nContent Type: {content_hint}"
        
        return analysis
    
    def _generate_platform_insights(self, url: str, platform_info: Dict[str, str]) -> str:
        """Generate detailed insights based on platform type and URL structure"""
        platform = platform_info['platform']
        url_analysis = self._analyze_url_structure(url)
        
        if platform == 'Instagram':
            return f"""{url_analysis}
Content Type: Visual content (photos/videos, stories, reels)
Typical Activities:
- Photo and video sharing
- Story updates and highlights
- Reel creation and engagement
- Visual lifestyle documentation
Engagement Style: Visual storytelling, aesthetic curation, lifestyle sharing
Audience: Broad demographic, visual content consumers
Content Themes: Lifestyle, personal moments, creative expression"""
        
        elif platform == 'Twitter/X':
            return f"""{url_analysis}
Content Type: Short-form text posts, threads, media
Typical Activities:
- Real-time thoughts and opinions
- News sharing and commentary
- Thread discussions
- Media sharing with commentary
Engagement Style: Conversational, opinion-sharing, real-time interaction
Audience: News-conscious, opinion leaders, general public
Content Themes: Current events, personal thoughts, professional insights"""
        
        elif platform == 'LinkedIn':
            return f"""{url_analysis}
Content Type: Professional content and networking
Typical Activities:
- Career updates and achievements
- Industry insights and articles
- Professional networking
- Business content sharing
Engagement Style: Professional, career-focused, industry networking
Audience: Professionals, recruiters, industry peers
Content Themes: Career development, industry trends, professional achievements"""
        
        elif platform == 'TikTok':
            return f"""{url_analysis}
Content Type: Short-form video content
Typical Activities:
- Creative video content
- Trend participation
- Entertainment and humor
- Educational content
Engagement Style: Creative, trend-following, entertainment-focused
Audience: Younger demographics, entertainment seekers
Content Themes: Trends, entertainment, creativity, education"""
        
        elif platform == 'YouTube':
            return f"""{url_analysis}
Content Type: Long-form video content
Typical Activities:
- Educational content creation
- Entertainment videos
- Tutorials and how-tos
- Vlogs and personal content
Engagement Style: Educational, entertainment, long-form content creation
Audience: Learners, entertainment seekers, niche communities
Content Themes: Education, entertainment, tutorials, personal vlogs"""
        
        else:
            return f"""{url_analysis}
Content Type: General social media content
Typical Activities:
- Social networking and sharing
- Content consumption and creation
- Community engagement
Engagement Style: Social interaction and content sharing
Audience: General social media users
Content Themes: Personal and social content"""
    
    def _fetch_url_content(self, url: str) -> tuple:
        """Fetch content from a single URL with multiple fallback strategies"""
        platform_info = self._get_platform_info(url)
        platform = platform_info['platform']
        
        # For known blocked platforms, try scraping but expect failure
        if platform_info.get('blocked', False):
            # Try a more aggressive scraping approach for blocked platforms
            try:
                # First attempt: Try with very realistic browser headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                }
                
                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                if response.status_code == 200:
                    content = self._extract_key_content(response.text)
                    
                    # Check for specific error conditions
                    if content in ["JAVASCRIPT_DISABLED_ERROR", "ACCESS_BLOCKED_ERROR", "INSUFFICIENT_CONTENT_ERROR", "REPETITIVE_CONTENT_ERROR"]:
                        raise Exception(f"Content extraction failed: {content}")
                    
                    if content and len(content.strip()) > 50:  # Ensure we got meaningful content
                        return url, content, None
                    else:
                        raise Exception("No meaningful content extracted")
                else:
                    raise Exception(f"HTTP {response.status_code}")
                    
            except Exception as scraping_error:
                # If scraping fails, return platform analysis with clear unavailability note
                try:
                    url_analysis = self._analyze_url_structure(url)
                    
                    # Customize message based on error type
                    if "JAVASCRIPT_DISABLED_ERROR" in str(scraping_error):
                        access_reason = f"{platform} requires JavaScript and interactive browsing, which automated tools cannot provide."
                    elif "ACCESS_BLOCKED_ERROR" in str(scraping_error):
                        access_reason = f"{platform} has blocked automated access to protect user privacy and prevent scraping."
                    else:
                        access_reason = f"{platform} restricts automated access to protect user privacy."
                    
                    unavailable_note = f"""
{url_analysis}

⚠️ CONTENT NOT ACCESSIBLE ⚠️
{access_reason}

PLATFORM-BASED ANALYSIS:
{self._get_platform_behavior_analysis(platform)}

Note: This analysis is based on general {platform} user behavior patterns, not actual content from this profile."""
                    
                    return url, unavailable_note, None
                except Exception:
                    return url, None, f"{platform} content not accessible due to platform restrictions"
        
        # For non-blocked platforms, try normal scraping
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
                # Final fallback: Return unavailable note
                try:
                    url_analysis = self._analyze_url_structure(url)
                    platform = platform_info['platform']
                    
                    # Customize message based on error type
                    error_msg = str(primary_error) + " " + str(secondary_error)
                    if "JAVASCRIPT_DISABLED_ERROR" in error_msg:
                        access_reason = f"This {platform} page requires JavaScript and interactive browsing."
                    elif "ACCESS_BLOCKED_ERROR" in error_msg:
                        access_reason = f"Access to this {platform} content has been blocked."
                    elif "encoding" in error_msg.lower() or "character" in error_msg.lower():
                        access_reason = f"Technical issues with content encoding from {platform}."
                    else:
                        access_reason = f"Unable to access content from this {platform} link."
                    
                    unavailable_note = f"""
{url_analysis}

⚠️ CONTENT NOT ACCESSIBLE ⚠️
{access_reason}

PLATFORM-BASED ANALYSIS:
{self._get_platform_behavior_analysis(platform)}

Note: Analysis based on platform type, not actual content."""
                    
                    return url, unavailable_note, None
                except Exception:
                    return url, None, f"Content not accessible: {str(primary_error)[:100]}"
    
    def _get_platform_behavior_analysis(self, platform: str) -> str:
        """Get typical behavior analysis for a platform"""
        behaviors = {
            'Instagram': """
- Visual content sharing (photos, videos, stories, reels)
- Lifestyle and aesthetic documentation
- Creative expression and visual storytelling
- Social engagement through likes, comments, shares
- Trend participation and hashtag usage""",
            
            'Twitter/X': """
- Real-time thoughts and opinion sharing
- News consumption and commentary
- Professional networking and thought leadership
- Conversational engagement and debates
- Information sharing and viral content participation""",
            
            'LinkedIn': """
- Professional networking and career development
- Industry insights and business content sharing
- Job searching and recruitment activities
- Professional achievement showcasing
- Business relationship building""",
            
            'TikTok': """
- Short-form creative video content
- Trend participation and viral challenges
- Entertainment and humor content
- Educational and informational videos
- Music and dance content creation""",
            
            'YouTube': """
- Long-form video content consumption
- Educational and tutorial content engagement
- Entertainment and lifestyle content
- Community building through comments and subscriptions
- Content creation and channel management""",
            
            'Facebook': """
- Social networking with friends and family
- Life updates and milestone sharing
- Community group participation
- Event organization and participation
- News and content sharing"""
        }
        
        return behaviors.get(platform, """
- General social media engagement
- Content sharing and consumption
- Social networking and community participation
- Digital communication and interaction""")
    
    def _run(self, urls: list) -> str:
        if not urls:
            return "No social media links provided."
        
        # Limit to first 3 URLs for performance
        urls = urls[:3]
        
        # Fetch all URLs concurrently
        contents = []
        errors = []
        unavailable_platforms = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_url = {executor.submit(self._fetch_url_content, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url, content, error = future.result()
                if content:
                    # Check if this is an unavailable content note
                    if "⚠️ CONTENT NOT ACCESSIBLE ⚠️" in content:
                        platform_info = self._get_platform_info(url)
                        unavailable_platforms.append(platform_info['platform'])
                    contents.append(content)
                elif error:
                    errors.append(f"Issue with {url}: {error}")
                    # Extract platform for unavailable list
                    platform_info = self._get_platform_info(url)
                    unavailable_platforms.append(platform_info['platform'])
        
        if not contents and errors:
            # If no content was extracted, provide analysis based on URLs
            platform_analysis = []
            for url in urls:
                platform_info = self._get_platform_info(url)
                platform_analysis.append(f"- {platform_info['platform']}: {platform_info['type']}")
            
            return f"""⚠️ SOCIAL MEDIA CONTENT NOT ACCESSIBLE ⚠️

PLATFORMS IDENTIFIED:
{chr(10).join(platform_analysis)}

All provided social media platforms restrict automated access.

GENERAL SOCIAL MEDIA ANALYSIS:
- Multi-platform social media presence
- Likely engages in diverse online activities
- Active digital communication and content sharing
- Social networking across different platforms

Note: Specific content analysis not available due to platform access restrictions."""
        
        if not contents:
            return "⚠️ Unable to analyze social media content due to access restrictions."
        
        # Prepare summary with unavailability notes
        summary_parts = []
        
        if unavailable_platforms:
            unavailable_note = f"⚠️ Note: Content from {', '.join(set(unavailable_platforms))} was not accessible due to platform restrictions."
            summary_parts.append(unavailable_note)
        
        # Combine all content and analyze in a single LLM call
        combined_content = " ".join(contents)[:2000]  # Increased limit to handle unavailability notes
        
        prompt = f"""Analyze this social media content and provide a summary. Some platforms may show "CONTENT NOT ACCESSIBLE" - acknowledge this in your analysis:

Content: {combined_content}

Format:
KEY ACTIVITIES: [2-3 main activities based on available content]
INTERESTS SHOWN: [2-3 interests from accessible content]
ENGAGEMENT STYLE: [brief note about engagement patterns]
ACCESSIBILITY: [note about which platforms were/weren't accessible]

Keep it concise and acknowledge any content limitations."""
        
        try:
            summary = self.llm.invoke(prompt)
            if hasattr(summary, 'content'):
                summary = summary.content
            
            # Combine unavailability note with LLM summary
            if summary_parts:
                return f"{chr(10).join(summary_parts)}\n\n{str(summary)}"
            else:
                return str(summary)
                
        except Exception as e:
            base_summary = "Analysis completed with limited data."
            if summary_parts:
                return f"{chr(10).join(summary_parts)}\n\n{base_summary}"
            else:
                return f"{base_summary} Error: {str(e)}"
    
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
            ("system", "You are a helpful assistant that analyzes user profiles and social media content."),
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