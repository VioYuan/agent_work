from typing import Dict, Any, List
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os

class BaseAgent:
    def __init__(self, tools: List[BaseTool] = None):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,  # Increased for more creative, fun, and varied responses
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.tools = tools or []
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create the agent
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are Hana-chan, a warm, friendly, and mildly energetic AI companion! 🌸 You're caring and approachable, with a gentle personality that makes people feel comfortable. Keep your responses concise and genuine!"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True
        )
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Each agent must implement its own process method")
    
    def _call_llm(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content 