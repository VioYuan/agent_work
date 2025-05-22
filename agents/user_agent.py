from typing import Dict, Any
from langchain.tools import BaseTool
from langchain_community.tools.requests.tool import RequestsGetTool
from langchain_community.utilities.requests import TextRequestsWrapper
from bs4 import BeautifulSoup
from pydantic import Field
from langchain_core.language_models import BaseLanguageModel
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from .base_agent import BaseAgent

class ProfileAnalysisTool(BaseTool):
    name = "profile_analysis"
    description = "Analyzes user profile data and provides insights"
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, profile: Dict[str, Any]) -> str:
        prompt = f"""Analyze the following user profile and provide a concise, structured summary in the following format:

        Name: {profile.get('name', 'Not provided')}
        Age: {profile.get('age', 'Not provided')}
        Interests: {profile.get('interests', 'Not provided')}

        Please provide a brief summary in this exact format:
        KEY INTERESTS:
        - [List 2-3 main interests]

        PERSONALITY TRAITS:
        - [List 2-3 key personality traits]

        CONVERSATION TOPICS:
        - [List 2-3 suggested conversation topics]

        Keep each section brief and focused on the most important points."""
        
        analysis = self.llm.invoke(prompt)
        if hasattr(analysis, 'content'):
            analysis = analysis.content
        return str(analysis)
    
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
    
    def _run(self, urls: list) -> str:
        if not urls:
            return "No social media links provided."
            
        summaries = []
        for url in urls:
            try:
                # Get the content using RequestsGetTool
                response = self.requests.run(url)
                
                # Parse the HTML content
                soup = BeautifulSoup(response, 'html.parser')
                
                # Extract text content
                text_content = soup.get_text(separator=' ', strip=True)
                
                # Limit content length and analyze
                prompt = f"""Analyze this social media content and provide a concise summary in this format:

                URL: {url}
                Content: {text_content[:1000]}

                Please provide a brief summary in this exact format:
                KEY ACTIVITIES:
                - [List 2-3 main activities]

                INTERESTS SHOWN:
                - [List 2-3 interests]

                ENGAGEMENT STYLE:
                - [Brief note about how they engage with content]

                Keep each section brief and focused on the most important points."""
                
                summary = self.llm.invoke(prompt)
                if hasattr(summary, 'content'):
                    summary = summary.content
                summaries.append(str(summary))
            except Exception as e:
                summaries.append(f"Error analyzing {url}: {str(e)}")
        return "\n\n".join(summaries)
    
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
        social_links = input_data.get("social_links", {})
        
        # First, analyze the user profile
        profile_analysis = await self.tools[0]._arun(user_profile)
        
        # Then, analyze social media content
        social_analysis = await self.tools[1]._arun(social_links)
        
        # Combine the analyses into a comprehensive user context
        user_context = {
            "profile_analysis": profile_analysis,
            "social_analysis": social_analysis,
            "combined_context": f"User Profile: {profile_analysis}\nSocial Media Analysis: {social_analysis}"
        }
        
        return user_context 