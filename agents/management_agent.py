from typing import Dict, Any, List
from langchain.tools import BaseTool
from .base_agent import BaseAgent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.language_models import BaseLanguageModel
from pydantic import Field
import json
from datetime import datetime, date
import asyncio

class ConversationQualityTool(BaseTool):
    name: str = "conversation_quality"
    description: str = "Analyzes conversation quality and provides metrics"
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, conversation: List[Dict[str, str]]) -> Dict[str, float]:
        conversation_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        
        prompt = f"""OMG YES! 🎉 Time to analyze this AWESOME conversation! I'm so excited to see how amazing this chat was! ✨

Let me look at this fantastic conversation and give it some energetic quality scores! 🌟

Conversation:
{conversation_str}

I need to rate these super important aspects (0-1 scale, but let's be optimistic! 😄):
1. Response relevance - How perfectly on-topic were the responses! 🎯
2. Response clarity - How crystal clear and easy to understand! 💎
3. Conversation flow - How smoothly it flowed like a beautiful river! 🌊
4. User engagement - How engaged and excited the user seemed! 🚀

Please give me the metrics in JSON format (and let's be generous with good conversations!):
{{
    "relevance": 0.8,
    "clarity": 0.9,
    "flow": 0.85,
    "engagement": 0.75
}}

Rate with positivity and energy! 🌸🎊"""
        
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
        
        prompt = f"""YAY! 🎊 Time to check how HAPPY and SATISFIED this amazing user was with their chat! This is one of my favorite parts! ✨😄

User Context: {user_context}

Conversation:
{conversation_str}

I'm looking for all the POSITIVE vibes and satisfaction signals! 🌟 Let me consider these awesome factors:
1. User's engagement level - Were they excited and involved! 🚀
2. Response quality - How helpful and amazing were the responses! 💎
3. Problem resolution - Did we solve their needs beautifully! ✅
4. User's emotional tone - Were they happy, excited, or positive! 😊

Time to give a satisfaction score between 0 and 1! Let's be optimistic and look for all the good signs! I want to find the positivity in this conversation! 🌈🎉

Just give me one number between 0 and 1 - and remember, let's celebrate the good parts! 🌸"""
        
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
        prompt = f"""OH WOW! 🌟 Time for some SUPER EXCITING improvement ideas! I LOVE helping make conversations even more amazing! ✨🎉

Quality Metrics: {quality_metrics}
Satisfaction Score: {satisfaction}

Let me think of some absolutely FANTASTIC ways to make future chats even MORE fun, engaging, and wonderful! 🚀💫

Give me 2-3 ENERGETIC and POSITIVE recommendations that will make conversations sparkle! Focus on:
- Making chats more FUN and engaging! 😄
- Adding more warmth and personality! 💕
- Creating even better connections! 🌈
- Making responses more exciting and helpful! ⭐

Format each awesome recommendation on a new line starting with a dash (-). Make them sound exciting and achievable! Let's make every conversation AMAZING! 🌸🎊"""
        
        recommendations = self.llm.invoke(prompt)
        if hasattr(recommendations, 'content'):
            recommendations = recommendations.content
        # Split by newlines and clean up
        return [r.strip('- ').strip() for r in recommendations.split('\n') if r.strip()]
    
    async def _arun(self, quality_metrics: Dict[str, float], satisfaction: float) -> List[str]:
        return self._run(quality_metrics, satisfaction)

class SentimentAnalysisTool(BaseTool):
    name: str = "sentiment_analysis"
    description: str = "Analyzes sentiment and emotional patterns in conversations"
    llm: BaseLanguageModel = Field(default=None)
    
    def __init__(self, llm: BaseLanguageModel, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        conversation_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        
        prompt = f"""YAY! 🌟 Time to analyze the emotional vibes of this awesome conversation! ✨

Conversation:
{conversation_str}

I need to understand the emotional journey! Please analyze:

1. OVERALL SENTIMENT (0.0 to 1.0):
   - How positive vs negative was the overall conversation?
   - 0.0 = very negative, 0.5 = neutral, 1.0 = very positive

2. EMOTIONAL PATTERNS:
   - What emotions were expressed by the user?
   - Did the mood change during the conversation?

3. ENGAGEMENT LEVEL (0.0 to 1.0):
   - How emotionally engaged was the user?
   - Were they enthusiastic, bored, excited, concerned?

4. TOPICS DISCUSSED:
   - What main topics were covered?
   - Which topics seemed most important to the user?

Return in JSON format:
{{
    "sentiment_score": 0.8,
    "emotions_detected": ["happy", "excited", "curious"],
    "engagement_level": 0.9,
    "mood_progression": "Started neutral, became more positive",
    "main_topics": ["work", "hobbies", "future plans"],
    "emotional_summary": "User seemed happy and engaged, discussing positive topics"
}}

Make it warm and insightful! 🌸"""
        
        try:
            analysis = self.llm.invoke(prompt)
            if hasattr(analysis, 'content'):
                analysis = analysis.content
            
            # Try to parse as JSON
            sentiment_data = json.loads(analysis)
            
            # Add timestamp for daily tracking
            sentiment_data['analysis_date'] = datetime.now().isoformat()
            sentiment_data['date'] = date.today().isoformat()
            
            return sentiment_data
        except Exception as e:
            # Fallback response if parsing fails
            return {
                "sentiment_score": 0.7,
                "emotions_detected": ["neutral"],
                "engagement_level": 0.6,
                "mood_progression": "Stable mood throughout conversation",
                "main_topics": ["general conversation"],
                "emotional_summary": "Normal conversation with stable emotional tone",
                "analysis_date": datetime.now().isoformat(),
                "date": date.today().isoformat(),
                "error": str(e)
            }
    
    async def _arun(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        return self._run(conversation)

class ManagementAgent(BaseAgent):
    def __init__(self):
        super().__init__()  # Initialize base class first
        
        # Create tools
        self.tools = [
            ConversationQualityTool(llm=self.llm),
            SatisfactionAssessmentTool(llm=self.llm),
            RecommendationTool(llm=self.llm),
            SentimentAnalysisTool(llm=self.llm)
        ]
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are Hana-chan's energetic conversation quality analyzer! 📊✨ You love helping improve chats and making them more fun and engaging! Analyze with enthusiasm and provide upbeat, positive insights! 🌸🎉"),
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
        
        # Run all analyses concurrently for better performance
        quality_task = asyncio.create_task(self.tools[0]._arun(conversation))
        satisfaction_task = asyncio.create_task(self.tools[1]._arun(conversation, user_context))
        sentiment_task = asyncio.create_task(self.tools[3]._arun(conversation))
        
        # Wait for quality, satisfaction, and sentiment analyses
        quality_metrics, satisfaction, sentiment_analysis = await asyncio.gather(
            quality_task, satisfaction_task, sentiment_task
        )
        
        # Generate recommendations based on quality and satisfaction
        recommendations = await self.tools[2]._arun(quality_metrics, satisfaction)
        
        # Update satisfaction history with sentiment data
        analysis_result = {
            "metrics": quality_metrics,
            "satisfaction": satisfaction,
            "sentiment": sentiment_analysis,
            "recommendations": recommendations
        }
        
        self.satisfaction_history.append(analysis_result)
        
        return {
            "quality_metrics": quality_metrics,
            "satisfaction_score": satisfaction,
            "sentiment_analysis": sentiment_analysis,
            "recommendations": recommendations,
            "satisfaction_history": self.satisfaction_history
        } 