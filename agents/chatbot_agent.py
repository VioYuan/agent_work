from typing import Dict, Any, List
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import Field
from .base_agent import BaseAgent
import json

class ResponseGenerationTool(BaseTool):
    name = "response_generation"
    description = "Generates a response based on user message and context"
    llm: Any = Field(default=None)
    
    def __init__(self, llm: Any, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, input_str: str) -> str:
        # Parse the input string to extract message, context, and history
        try:
            # Split the input string into its components
            parts = input_str.split('\n')
            message = ""
            context = {}
            history = []
            
            for part in parts:
                if part.startswith("Message:"):
                    message = part.replace("Message:", "").strip()
                elif part.startswith("Context:"):
                    context_str = part.replace("Context:", "").strip()
                    try:
                        context = json.loads(context_str)
                    except:
                        context = {}
                elif part.startswith("History:"):
                    history_str = part.replace("History:", "").strip()
                    try:
                        history = json.loads(history_str)
                    except:
                        history = []
        except:
            return "Error: Invalid input format"
        
        # Format context for the prompt
        context_str = ""
        if isinstance(context, dict):
            if "profile_analysis" in context:
                context_str += f"Profile Analysis:\n{context['profile_analysis']}\n\n"
            if "social_analysis" in context:
                context_str += f"Social Media Analysis:\n{context['social_analysis']}\n\n"
        
        # Format conversation history
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-5:]])
        
        prompt = f"""Based on the following context and conversation history, provide a helpful response:
        
        {context_str}
        
        Recent conversation:
        {history_str}
        
        User's latest message: {message}
        
        Provide a natural, helpful response that takes into account the user's context and conversation history."""
        
        response = self.llm.invoke(prompt)
        if hasattr(response, 'content'):
            response = response.content
        return str(response)
    
    async def _arun(self, input_str: str) -> str:
        return self._run(input_str)

class ChatbotAgent(BaseAgent):
    def __init__(self):
        super().__init__()  # Initialize base class first
        
        # Create tools
        self.tools = [
            ResponseGenerationTool(llm=self.llm)
        ]
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that generates responses based on user messages and context."),
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
    
    async def process(self, input_data: Dict[str, Any]) -> str:
        message = input_data.get("message", "")
        context = input_data.get("context", {})
        history = input_data.get("history", [])
        
        # Prepare input for the tool
        tool_input = f"Message: {message}\nContext: {json.dumps(context)}\nHistory: {json.dumps(history)}"
        
        # Get response from the tool
        response = await self.tools[0]._arun(tool_input)
        
        # Return just the response text
        return str(response) 