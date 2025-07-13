from typing import Dict, Any, List
from langchain.tools import BaseTool
from .base_agent import BaseAgent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.language_models import BaseLanguageModel
from pydantic import Field
import json

class ConversationQualityTool(BaseTool):
    name: str = "conversation_quality"
    description: str = "Analyzes conversation quality and provides metrics"
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, conversation: List[Dict[str, str]]) -> Dict[str, float]:
        conversation_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        
        prompt = f"""Analyze the following conversation and provide quality metrics (0-1) for:
        1. Response relevance
        2. Response clarity
        3. Conversation flow
        4. User engagement
        
        Conversation:
        {conversation_str}
        
        Provide the metrics in JSON format like this:
        {{
            "relevance": 0.8,
            "clarity": 0.9,
            "flow": 0.85,
            "engagement": 0.75
        }}"""
        
        analysis = self.llm.invoke(prompt)
        try:
            # Try to parse the response as JSON
            if hasattr(analysis, 'content'):
                analysis = analysis.content
            metrics = json.loads(analysis)
            return metrics
        except:
            # If parsing fails, return default metrics
            return {
                "relevance": 0.7,
                "clarity": 0.7,
                "flow": 0.7,
                "engagement": 0.7
            }
    
    async def _arun(self, conversation: List[Dict[str, str]]) -> Dict[str, float]:
        return self._run(conversation)

class SatisfactionAssessmentTool(BaseTool):
    name: str = "satisfaction_assessment"
    description: str = "Assesses user satisfaction based on conversation and context"
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, conversation: List[Dict[str, str]], user_context: Dict[str, Any]) -> float:
        conversation_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        
        prompt = f"""Based on the conversation and user context, assess the user's satisfaction level (0-1):
        
        User Context: {user_context}
        
        Conversation:
        {conversation_str}
        
        Consider factors like:
        1. User's engagement level
        2. Response quality
        3. Problem resolution
        4. User's emotional tone
        
        Provide a single number between 0 and 1 representing the satisfaction score."""
        
        analysis = self.llm.invoke(prompt)
        try:
            # Try to extract a number from the response
            if hasattr(analysis, 'content'):
                analysis = analysis.content
            score = float(analysis.strip())
            return max(0.0, min(1.0, score))  # Ensure score is between 0 and 1
        except:
            return 0.7  # Default score if parsing fails
    
    async def _arun(self, conversation: List[Dict[str, str]], user_context: Dict[str, Any]) -> float:
        return self._run(conversation, user_context)

class RecommendationTool(BaseTool):
    name: str = "recommendation_generation"
    description: str = "Generates recommendations based on quality metrics and satisfaction"
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, quality_metrics: Dict[str, float], satisfaction: float) -> List[str]:
        prompt = f"""Based on the following quality metrics and satisfaction score, provide specific recommendations for improvement:
        
        Quality Metrics: {quality_metrics}
        Satisfaction Score: {satisfaction}
        
        Provide 2-3 specific, actionable recommendations. Format each recommendation on a new line starting with a dash (-)."""
        
        recommendations = self.llm.invoke(prompt)
        if hasattr(recommendations, 'content'):
            recommendations = recommendations.content
        # Split by newlines and clean up
        return [r.strip('- ').strip() for r in recommendations.split('\n') if r.strip()]
    
    async def _arun(self, quality_metrics: Dict[str, float], satisfaction: float) -> List[str]:
        return self._run(quality_metrics, satisfaction)

class ManagementAgent(BaseAgent):
    def __init__(self):
        super().__init__()  # Initialize base class first
        
        # Create tools
        self.tools = [
            ConversationQualityTool(llm=self.llm),
            SatisfactionAssessmentTool(llm=self.llm),
            RecommendationTool(llm=self.llm)
        ]
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that analyzes conversation quality and user satisfaction."),
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
        
        self.satisfaction_history: List[Dict[str, Any]] = []
     
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        conversation = input_data.get("conversation", [])
        user_context = input_data.get("user_context", {})
        
        # First, analyze conversation quality
        quality_metrics = await self.tools[0]._arun(conversation)
        
        # Then, assess user satisfaction
        satisfaction = await self.tools[1]._arun(conversation, user_context)
        
        # Finally, generate recommendations
        recommendations = await self.tools[2]._arun(quality_metrics, satisfaction)
        
        # Update satisfaction history
        self.satisfaction_history.append({
            "metrics": quality_metrics,
            "satisfaction": satisfaction,
            "recommendations": recommendations
        })
        
        return {
            "quality_metrics": quality_metrics,
            "satisfaction_score": satisfaction,
            "recommendations": recommendations,
            "satisfaction_history": self.satisfaction_history
        } 