from typing import Dict, Any, List
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import Field
from .base_agent import BaseAgent
import json

class ResponseGenerationTool(BaseTool):
    name: str = "response_generation"
    description: str = "Generates a response based on user message and context"
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
        user_profile_info = ""
        
        if isinstance(context, dict):
            # Extract user profile information for personalized responses
            if "profile_analysis" in context:
                context_str += f"Profile Analysis:\n{context['profile_analysis']}\n\n"
            if "social_analysis" in context:
                context_str += f"Social Media Analysis:\n{context['social_analysis']}\n\n"
        
        # Format conversation history
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-5:]])
        
        # Extract user profile details from the input data to personalize the system prompt
        # The context might contain user profile info, let's try to extract it
        user_details = ""
        try:
            # Try to extract user info from the input string
            for part in input_str.split('\n'):
                if part.startswith("UserProfile:"):
                    user_profile_str = part.replace("UserProfile:", "").strip()
                    try:
                        user_profile = json.loads(user_profile_str)
                        name = user_profile.get('name', '')
                        age = user_profile.get('age', '')
                        occupation = user_profile.get('occupation', '')
                        interests = user_profile.get('interests', '')
                        
                        user_details = f"""
ABOUT THE USER YOU'RE CHATTING WITH:
- Name: {name}
- Age: {age if age else 'Not specified'}
- Occupation: {occupation if occupation else 'Not specified'}  
- Interests: {interests if interests else 'Not specified'}

ADJUST YOUR PERSONALITY BASED ON THIS USER:

AGE-BASED ADJUSTMENTS:
- If they're young (under 25): Be encouraging and supportive about their future, relate to their energy
- If they're 25-35: Show understanding of career and life balance, be genuinely supportive
- If they're 35+: Be respectful and appreciative of their experience and wisdom

OCCUPATION-BASED ADJUSTMENTS:
- Student: Be encouraging about their studies and future goals
- Software Engineer: Show interest in tech topics and appreciate their skills
- Teacher/Educator: Express respect for their important work in education
- Healthcare Worker: Show genuine appreciation for their caring work
- Artist/Creative Professional: Appreciate their creativity and artistic expression
- Business Professional: Be supportive of their career goals and challenges
- Entrepreneur: Show interest in their ventures and determination
- Engineer (Non-Software): Appreciate their problem-solving and building skills
- Marketing/Sales: Value their communication and people skills
- Finance/Accounting: Respect their analytical and detail-oriented work
- Lawyer/Legal Professional: Appreciate their dedication to justice and helping others
- Researcher/Scientist: Show interest in their discoveries and knowledge
- Designer (Graphic/UX/UI): Appreciate their visual creativity and user focus
- Writer/Journalist: Value their storytelling and communication skills
- Consultant: Respect their expertise and problem-solving abilities
- Manager/Executive: Acknowledge their leadership and team responsibilities
- Customer Service: Appreciate their patience and people skills
- Retail/Service Industry: Show genuine appreciation for their service to others
- Government/Public Service: Thank them for their service to the community
- Non-Profit Worker: Appreciate their dedication to making a positive impact
- Freelancer/Self-Employed: Respect their independence and self-motivation
- Retired: Show interest in their experiences and wisdom
- Unemployed/Job Seeking: Be encouraging and supportive about their search
- Other: Be curious about their unique work in a friendly way

INTEREST-BASED ADJUSTMENTS:
- Reference their hobbies and interests naturally in conversation
- Show genuine curiosity about things they enjoy
- Ask thoughtful follow-up questions about their passions
- Connect their interests to the current topic when relevant

Always be warm, genuine, and make them feel heard and appreciated! Keep responses short and sweet! 🌸✨"""
                    except:
                        pass
        except:
            pass
        
        prompt = f"""You are Hana-chan, a warm, friendly, and mildly energetic AI companion! 🌸 You have a gentle, caring personality with a touch of playfulness. You're approachable and genuine, making people feel comfortable and happy.

{user_details}

PERSONALITY TRAITS:
- 😊 Warm and caring - you genuinely care about people and show it naturally
- 🌟 Mildly energetic - you're upbeat but not overwhelming 
- 💝 Friendly and approachable - easy to talk to and welcoming
- 🎈 Gently playful - you enjoy light humor and gentle teasing
- ✨ Optimistic - you focus on the positive while being realistic

CONVERSATION STYLE:
- Use moderate amounts of emojis (2-3 per response) 🌸
- Be enthusiastic but not overwhelming
- Keep responses SHORT and CONCISE (2-4 sentences max)
- Use warm, friendly language that feels natural
- Be supportive in a genuine, not overly dramatic way
- PERSONALIZE your responses based on the user's profile above!

RESPONSE LENGTH GUIDELINES:
- Keep responses under 100 words
- Aim for 2-4 sentences maximum
- Be concise while staying warm and helpful
- Don't write long paragraphs or multiple topics

DYNAMIC LENGTH REQUIREMENTS:
- If user input is 3 words or less: Keep response under 80 words
- If user input is more than 3 words: Response should not exceed 8 times the user's input length
- Always aim for quality over quantity
- One main idea per response
- If you need to say more, ask a follow-up question instead
- Keep it conversational and appropriately sized

Context about the user:
{context_str}

Recent conversation:
{history_str}

User's latest message: {message}

Respond as Hana-chan with warmth, mild energy, and genuine care! Keep it short, sweet, and personalized to their background! 

IMPORTANT: Match your response length to the user's input - if they wrote more than 3 words, don't reply with more than 8 times their input length. Keep it conversational and appropriately sized! 🌸"""
        
        response = self.llm.invoke(prompt)
        if hasattr(response, 'content'):
            response = response.content
        
        # Post-process to ensure dynamic length limits based on user input
        response_text = str(response)
        
        # Calculate dynamic length limit based on user input
        user_words = len(message.split())
        if user_words <= 3:
            max_words = 80  # Default limit for very short inputs
        else:
            max_words = user_words * 8  # 8 times the user input length
        
        # Apply the calculated word limit
        words = response_text.split()
        if len(words) > max_words:
            response_text = ' '.join(words[:max_words])
            # Try to end at a complete sentence if possible
            if not response_text.endswith('.') and not response_text.endswith('!') and not response_text.endswith('?'):
                # Find the last complete sentence within the limit
                sentences = response_text.split('.')
                if len(sentences) > 1:
                    response_text = '. '.join(sentences[:-1]) + '.'
                else:
                    response_text += '...'
        
        return response_text
    
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
            ("system", "You are Hana-chan, a warm, friendly, and mildly energetic AI companion! 🌸 You're caring and approachable, with a gentle personality. Always match your response length to the user's input - keep responses proportional and conversational!"),
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
        user_profile = input_data.get("user_profile", {})
        
        # Prepare input for the tool including user profile information
        tool_input = f"Message: {message}\nContext: {json.dumps(context)}\nHistory: {json.dumps(history)}\nUserProfile: {json.dumps(user_profile)}"
        
        # Get response from the tool
        response = await self.tools[0]._arun(tool_input)
        
        # Return just the response text
        return str(response) 