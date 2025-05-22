import streamlit as st
import asyncio
from agents.user_agent import UserAgent
from agents.chatbot_agent import ChatbotAgent
from agents.management_agent import ManagementAgent
from database import Database
import json
import os

# Check for API key in environment first
if not os.environ.get("OPENAI_API_KEY"):
    from dotenv import load_dotenv
    load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    st.error("Please set your OPENAI_API_KEY as an environment variable or in the .env file.")
    st.stop()

# Initialize agents and database
user_agent = UserAgent()
chatbot_agent = ChatbotAgent()
management_agent = ManagementAgent()
db = Database()

# Initialize session state
if 'user_context' not in st.session_state:
    st.session_state.user_context = {}
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'satisfaction_metrics' not in st.session_state:
    st.session_state.satisfaction_metrics = {}
if 'processing_metrics' not in st.session_state:
    st.session_state.processing_metrics = False
if 'metrics_task' not in st.session_state:
    st.session_state.metrics_task = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

def main():
    st.title("AI-Powered Chatbot System")
    
    # Sidebar for navigation
    page = st.sidebar.selectbox("Choose a page", ["Profile Setup", "Chat", "User Management"])
    
    if page == "Profile Setup":
        show_profile_setup()
    elif page == "Chat":
        show_chat()
    else:
        show_user_management()

def show_profile_setup():
    st.header("User Profile Setup")
    
    # Check if user is already logged in
    if st.session_state.user_id:
        user_profile = db.get_user_profile(st.session_state.user_id)
        if user_profile:
            st.info(f"Welcome back, {user_profile['name']}!")
            if st.button("Logout"):
                st.session_state.user_id = None
                st.session_state.user_context = {}
                st.session_state.conversation_history = []
                st.rerun()
            return
    
    # User profile form
    with st.form("user_profile_form"):
        st.subheader("Personal Information")
        name = st.text_input("Name")
        age = st.number_input("Age", min_value=0, max_value=120)
        interests = st.text_area("Interests and Hobbies")
        
        st.subheader("Social Media Links")
        twitter = st.text_input("Twitter/X Profile URL")
        instagram = st.text_input("Instagram Profile URL")
        facebook = st.text_input("Facebook Profile URL")
        
        submitted = st.form_submit_button("Submit Profile")
        
        if submitted:
            if not name or not interests:  # Add validation
                st.error("Please fill in at least your name and interests.")
                return
                
            # Process user profile
            user_profile = {
                "name": name,
                "age": age,
                "interests": interests
            }
            social_links = [link for link in [twitter, instagram, facebook] if link]
            
            # Process with user agent
            result = asyncio.run(process_user_profile(user_profile, social_links))
            
            # Convert LLM responses to strings if needed
            processed_result = {
                "profile_analysis": str(result["profile_analysis"]),
                "social_analysis": str(result["social_analysis"]),
                "combined_context": str(result["combined_context"])
            }
            
            # Save to database
            user_id = db.save_user_profile({
                **user_profile,
                "social_links": social_links,
                "user_context": processed_result
            })
            
            # Update session state
            st.session_state.user_id = user_id
            st.session_state.user_context = processed_result
            
            st.success("Profile processed and saved successfully!")
            st.rerun()

def show_user_management():
    st.header("User Management")
    
    # Show all users
    users = db.get_all_users()
    if users:
        st.subheader("Registered Users")
        for user in users:
            with st.expander(f"{user['name']} (Age: {user['age']})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"Load Profile", key=f"load_{user['id']}"):
                        user_profile = db.get_user_profile(user['id'])
                        if user_profile:
                            st.session_state.user_id = user['id']
                            st.session_state.user_context = user_profile['user_context']
                            st.session_state.conversation_history = []
                            st.rerun()
                
                with col2:
                    if st.button(f"Delete Profile", key=f"delete_{user['id']}"):
                        if db.delete_user_profile(user['id']):
                            st.success(f"Successfully deleted {user['name']}'s profile")
                            st.rerun()
                        else:
                            st.error("Failed to delete profile")
                
                # Show recent conversations
                conversations = db.get_user_conversations(user['id'])
                if conversations:
                    st.subheader("Recent Conversations")
                    for conv in conversations:
                        st.write(f"**User:** {conv['message']}")
                        st.write(f"**Assistant:** {conv['response']}")
                        st.write(f"**Satisfaction Score:** {conv['satisfaction_score']:.2f}")
                        st.write("---")
    else:
        st.info("No users registered yet.")

async def process_user_profile(user_profile, social_links):
    result = await user_agent.process({
        "user_profile": user_profile,
        "social_links": social_links
    })
    return result

def show_chat():
    st.header("Chat Interface")
    
    # Check if user is logged in
    if not st.session_state.user_id:
        st.warning("Please set up your profile first!")
        return
    
    # Display user context if available
    if st.session_state.user_context:
        with st.expander("User Context"):
            context = st.session_state.user_context
            if isinstance(context, dict):
                # Display profile analysis
                if "profile_analysis" in context:
                    st.subheader("Profile Summary")
                    st.write(context["profile_analysis"])
                
                # Display social media insights
                if "social_analysis" in context:
                    st.subheader("Social Media Insights")
                    st.write(context["social_analysis"])
                
                # Add a divider
                st.markdown("---")
                
                # Display key points
                st.subheader("Key Points")
                if "combined_context" in context:
                    # Split the combined context into bullet points
                    points = context["combined_context"].split("\n")
                    for point in points:
                        if point.strip():
                            st.markdown(f"• {point.strip()}")
            else:
                st.write("No context available")
    
    # Chat interface
    user_input = st.text_input("Type your message here...")
    
    if st.button("Send"):
        if user_input:
            # Process message with chatbot agent immediately
            asyncio.run(process_message(user_input))
    
    # Display conversation history
    for message in st.session_state.conversation_history:
        if message["role"] == "user":
            st.write(f"👤 You: {message['content']}")
        else:
            st.write(f"🤖 Assistant: {message['content']}")
    
    # Display satisfaction metrics if available
    if st.session_state.satisfaction_metrics:
        with st.expander("Conversation Quality Metrics"):
            metrics = st.session_state.satisfaction_metrics
            if isinstance(metrics, dict):
                # Display quality metrics
                if "quality_metrics" in metrics:
                    st.subheader("Quality Metrics")
                    for key, value in metrics["quality_metrics"].items():
                        st.metric(key.title(), f"{value:.2f}")
                
                # Display satisfaction score
                if "satisfaction_score" in metrics:
                    st.subheader("Satisfaction Score")
                    st.metric("Overall Satisfaction", f"{metrics['satisfaction_score']:.2f}")
                
                # Display recommendations
                if "recommendations" in metrics:
                    st.subheader("Recommendations")
                    for rec in metrics["recommendations"]:
                        st.markdown(f"• {rec}")
            else:
                st.json(metrics)
    
    # Show processing indicator if metrics are being calculated
    if st.session_state.processing_metrics:
        st.info("Calculating conversation quality metrics...")
    
    # Check if there's a pending metrics task
    if st.session_state.metrics_task and st.session_state.metrics_task.done():
        try:
            result = st.session_state.metrics_task.result()
            st.session_state.satisfaction_metrics = result
            
            # Save conversation to database
            if st.session_state.conversation_history:
                last_user_msg = next((msg['content'] for msg in reversed(st.session_state.conversation_history) 
                                    if msg['role'] == 'user'), None)
                last_assistant_msg = next((msg['content'] for msg in reversed(st.session_state.conversation_history) 
                                        if msg['role'] == 'assistant'), None)
                
                if last_user_msg and last_assistant_msg:
                    db.save_conversation(
                        st.session_state.user_id,
                        last_user_msg,
                        last_assistant_msg,
                        result.get("satisfaction_score", 0.0)
                    )
            
            st.session_state.processing_metrics = False
            st.session_state.metrics_task = None
            st.rerun()
        except Exception as e:
            st.error(f"Error processing metrics: {str(e)}")
            st.session_state.processing_metrics = False
            st.session_state.metrics_task = None

async def process_message(message):
    # Process with chatbot agent
    response = await chatbot_agent.process({
        "message": message,
        "context": st.session_state.user_context or {},
        "history": st.session_state.conversation_history
    })
    
    # Update conversation history
    st.session_state.conversation_history.append({"role": "user", "content": message})
    st.session_state.conversation_history.append({"role": "assistant", "content": response})
    
    # Start metrics processing in background
    st.session_state.processing_metrics = True
    st.session_state.metrics_task = asyncio.create_task(process_metrics())

async def process_metrics():
    # Process with management agent
    result = await management_agent.process({
        "conversation": st.session_state.conversation_history,
        "user_context": st.session_state.user_context or {}
    })
    
    # Save conversation to database
    if st.session_state.conversation_history:
        last_user_msg = next((msg['content'] for msg in reversed(st.session_state.conversation_history) 
                            if msg['role'] == 'user'), None)
        last_assistant_msg = next((msg['content'] for msg in reversed(st.session_state.conversation_history) 
                                if msg['role'] == 'assistant'), None)
        
        if last_user_msg and last_assistant_msg:
            db.save_conversation(
                st.session_state.user_id,
                last_user_msg,
                last_assistant_msg,
                result.get("satisfaction_score", 0.0)
            )
    
    return result

if __name__ == "__main__":
    main() 