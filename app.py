import streamlit as st
import asyncio
from agents.user_agent import UserAgent
from agents.chatbot_agent import ChatbotAgent
from agents.management_agent import ManagementAgent
from database import Database
import json
import os

# Load environment variables only if OPENAI_API_KEY is not already set
if not os.environ.get("OPENAI_API_KEY"):
    from dotenv import load_dotenv
    load_dotenv()

# Check for API key and validate it's not a placeholder
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key or api_key.startswith("sk-your-") or "placeholder" in api_key.lower() or "your-api-key" in api_key.lower():
    st.error("""
    🔑 **OpenAI API Key Required**
    
    Please set your OPENAI_API_KEY environment variable with your actual API key.
    
    **Option 1: Set environment variable (recommended)**
    ```bash
    export OPENAI_API_KEY="sk-your-actual-key-here"
    ```
    
    **Option 2: Update .env file**
    Replace the placeholder in the .env file with your actual API key.
    
    Get your API key from: https://platform.openai.com/api-keys
    """)
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
if 'social_analysis_results' not in st.session_state:
    st.session_state.social_analysis_results = {}

def main():
    st.title("🔍 AI-Powered Social Media & Chat System")
    
    # Sidebar for navigation
    page = st.sidebar.selectbox("Choose a page", [
        "🏠 Profile Setup", 
        "💬 Chat", 
        "📱 Social Media Analysis",
        "👥 User Management"
    ])
    
    if page == "🏠 Profile Setup":
        show_profile_setup()
    elif page == "💬 Chat":
        show_chat()
    elif page == "📱 Social Media Analysis":
        show_social_media_analysis()
    else:
        show_user_management()

def show_profile_setup():
    st.header("👤 User Profile Setup")
    
    # Check if user is already logged in
    if st.session_state.user_id:
        user_profile = db.get_user_profile(st.session_state.user_id)
        if user_profile:
            st.success(f"✅ Welcome back, {user_profile['name']}!")
            
            # Show current social media links if available
            if user_profile.get('social_links'):
                st.subheader("📱 Your Social Media Profiles")
                for i, link in enumerate(user_profile['social_links'], 1):
                    st.write(f"{i}. {link}")
                
                if st.button("🔄 Re-analyze Social Media"):
                    with st.spinner("Re-analyzing your social media profiles..."):
                        result = asyncio.run(analyze_social_media_urls(user_profile['social_links']))
                        st.session_state.social_analysis_results = result
                        st.success("✅ Social media analysis updated!")
                        st.rerun()
            
            if st.button("🚪 Logout"):
                st.session_state.user_id = None
                st.session_state.user_context = {}
                st.session_state.conversation_history = []
                st.session_state.social_analysis_results = {}
                st.rerun()
            return
    
    st.markdown("**Create your profile to get personalized AI interactions based on your social media presence**")
    
    # User profile form
    with st.form("user_profile_form"):
        st.subheader("👤 Personal Information")
        name = st.text_input("Name", help="Your full name or preferred name")
        age = st.number_input("Age", min_value=0, max_value=120, help="Your age (optional)")
        interests = st.text_area("Interests and Hobbies", 
                                help="Tell us about your interests, hobbies, and what you're passionate about")
        
        st.subheader("📱 Social Media Links")
        st.markdown("*Add your social media profiles for AI-powered personality analysis*")
        
        # Enhanced social media inputs with better labels and examples
        col1, col2 = st.columns(2)
        
        with col1:
            instagram = st.text_input(
                "📸 Instagram Profile", 
                placeholder="https://www.instagram.com/username/",
                help="Your Instagram profile URL"
            )
            twitter = st.text_input(
                "🐦 Twitter/X Profile", 
                placeholder="https://twitter.com/username or https://x.com/username",
                help="Your Twitter or X profile URL"
            )
        
        with col2:
            threads = st.text_input(
                "🧵 Threads Profile", 
                placeholder="https://www.threads.com/@username",
                help="Your Threads profile URL (Meta's new platform)"
            )
            linkedin = st.text_input(
                "💼 LinkedIn Profile", 
                placeholder="https://www.linkedin.com/in/username/",
                help="Your LinkedIn profile URL"
            )
        
        # Additional social media options
        with st.expander("🔗 More Social Media Platforms"):
            facebook = st.text_input(
                "📘 Facebook Profile", 
                placeholder="https://www.facebook.com/username"
            )
            tiktok = st.text_input(
                "🎵 TikTok Profile", 
                placeholder="https://www.tiktok.com/@username"
            )
            youtube = st.text_input(
                "📺 YouTube Channel", 
                placeholder="https://www.youtube.com/c/channelname"
            )
        
        # Quick example buttons
        st.markdown("**📋 Quick Examples:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.form_submit_button("📸 Use Instagram Example", use_container_width=True):
                instagram = "https://www.instagram.com/lalalalisa_m/"
        with col2:
            if st.form_submit_button("🧵 Use Threads Example", use_container_width=True):
                threads = "https://www.threads.com/@zuck"
        with col3:
            if st.form_submit_button("🐦 Use Twitter Example", use_container_width=True):
                twitter = "https://twitter.com/elonmusk"
        with col4:
            if st.form_submit_button("💼 Use LinkedIn Example", use_container_width=True):
                linkedin = "https://www.linkedin.com/in/satyanadella/"
        
        submitted = st.form_submit_button("🚀 Create Profile & Analyze", type="primary")
        
        if submitted:
            if not name or not interests:
                st.error("❌ Please fill in at least your name and interests.")
                return
            
            # Collect all social media links
            social_links = [link for link in [instagram, twitter, threads, linkedin, facebook, tiktok, youtube] if link.strip()]
            
            if not social_links:
                st.warning("⚠️ No social media links provided. Profile will be created with basic information only.")
            
            # Show processing status
            with st.spinner("🔄 Processing your profile and analyzing social media..."):
                # Process user profile
                user_profile = {
                    "name": name,
                    "age": age,
                    "interests": interests
                }
                
                # Process with user agent (includes social media analysis)
                result = asyncio.run(process_user_profile(user_profile, social_links))
                
                # Convert LLM responses to strings if needed
                processed_result = {
                    "profile_analysis": str(result["profile_analysis"]),
                    "social_analysis": str(result["social_analysis"]),
                    "combined_context": str(result["combined_context"])
                }
                
                # Save social media analysis results to session state
                if social_links:
                    social_analysis = asyncio.run(analyze_social_media_urls(social_links))
                    st.session_state.social_analysis_results = social_analysis
                
                # Save to database
                user_id = db.save_user_profile({
                    **user_profile,
                    "social_links": social_links,
                    "user_context": processed_result
                })
                
                # Update session state
                st.session_state.user_id = user_id
                st.session_state.user_context = processed_result
            
            st.success("✅ Profile processed and saved successfully!")
            
            # Show quick summary
            if social_links:
                st.info(f"📊 Analyzed {len(social_links)} social media profile(s)")
                st.markdown("**🔍 Go to 'Social Media Analysis' page to see detailed insights!**")
            
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

def show_social_media_analysis():
    st.header("📱 Social Media URL Analysis")
    st.markdown("**AI-Powered URL Analysis for Instagram, Twitter/X, Threads & More**")
    st.markdown("✨ *Now with full Threads support! Analyze profiles, posts, and replies from Meta's new platform.*")
    
    # Platform badges
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.markdown("📱 **Instagram**")
    with col2:
        st.markdown("🐦 **Twitter/X**")
    with col3:
        st.markdown("🧵 **Threads**")
    with col4:
        st.markdown("💼 **LinkedIn**")
    with col5:
        st.markdown("🎵 **TikTok**")
    with col6:
        st.markdown("📺 **YouTube**")
    
    st.markdown("---")
    
    # Threads showcase section
    with st.container():
        st.markdown("""
        <div style="background: linear-gradient(135deg, #000000, #333333); color: white; border-radius: 15px; padding: 20px; margin-bottom: 30px; text-align: center;">
            <h3>🧵 NEW: Threads Support!</h3>
            <p>Analyze Meta's new text-based social platform with advanced URL pattern recognition</p>
        </div>
        """, unsafe_allow_html=True)
    
    # URL input section
    st.subheader("🔗 Enter Social Media URLs")
    
    # Create input fields
    url1 = st.text_input(
        "Social Media URL #1",
        placeholder="https://www.instagram.com/username/ or https://www.threads.com/@username",
        help="Enter an Instagram, Twitter, Threads, or other social media URL"
    )
    
    url2 = st.text_input(
        "Social Media URL #2 (Optional)",
        placeholder="https://twitter.com/username or https://www.threads.com/@username",
        help="Enter a second social media URL for comparison"
    )
    
    url3 = st.text_input(
        "Social Media URL #3 (Optional)",
        placeholder="https://www.linkedin.com/in/username or https://www.threads.com/@username",
        help="Enter a third social media URL"
    )
    
    url4 = st.text_input(
        "Social Media URL #4 (Optional) - Threads Focus",
        placeholder="https://www.threads.com/@username",
        help="Dedicated field for Threads URLs"
    )
    
    # Example buttons
    st.subheader("📋 Quick Examples")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📸 Instagram Example"):
            st.session_state.example_url = "https://www.instagram.com/lalalalisa_m/"
    with col2:
        if st.button("🐦 Twitter Example"):
            st.session_state.example_url = "https://twitter.com/elonmusk"
    with col3:
        if st.button("🧵 Threads Example"):
            st.session_state.example_url = "https://www.threads.com/@zuck"
    with col4:
        if st.button("💼 LinkedIn Example"):
            st.session_state.example_url = "https://www.linkedin.com/in/satyanadella/"
    
    # Show example URL if selected
    if hasattr(st.session_state, 'example_url'):
        st.info(f"Example URL: {st.session_state.example_url}")
        if st.button("Use This Example"):
            url1 = st.session_state.example_url
            st.rerun()
    
    # Analysis button
    if st.button("🚀 Analyze Social Media Profiles", type="primary"):
        urls = [url for url in [url1, url2, url3, url4] if url.strip()]
        
        if not urls:
            st.error("Please enter at least one social media URL")
            return
        
        # Show loading state
        with st.spinner("🔄 Analyzing social media profiles..."):
            st.info("Extracting insights from URL patterns and platform behavior")
            
            # Process URLs with user agent
            result = asyncio.run(analyze_social_media_urls(urls))
            st.session_state.social_analysis_results = result
        
        st.success("✅ Analysis complete!")
        st.rerun()
    
    # Display results
    if st.session_state.social_analysis_results:
        display_social_media_results(st.session_state.social_analysis_results)

def display_social_media_results(results):
    """Display the social media analysis results in a structured format"""
    st.subheader("📊 Analysis Results")
    
    if isinstance(results, str):
        # Parse the results if they're in string format
        try:
            # Try to extract structured information from the string
            st.markdown("### 🔍 Analysis Summary")
            st.text_area("Detailed Analysis", results, height=300)
        except:
            st.write(results)
        return
    
    # If results are structured, display them nicely
    if isinstance(results, dict):
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("URLs Analyzed", len(results.get('urls', [])))
        with col2:
            st.metric("Platforms Detected", len(set(results.get('platforms', []))))
        with col3:
            st.metric("Success Rate", f"{results.get('success_rate', 0):.1%}")
        
        st.markdown("---")
        
        # Individual URL analyses
        for i, url_analysis in enumerate(results.get('url_analyses', []), 1):
            with st.expander(f"🔗 URL #{i}: {url_analysis.get('platform', 'Unknown')} Analysis"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown("**📋 Basic Info**")
                    st.write(f"**Platform:** {url_analysis.get('platform', 'Unknown')}")
                    st.write(f"**Username:** {url_analysis.get('username', 'Not detected')}")
                    st.write(f"**Content Type:** {url_analysis.get('content_type', 'Profile')}")
                    st.write(f"**Activity Level:** {url_analysis.get('activity_level', 'Unknown')}")
                
                with col2:
                    st.markdown("**🎯 Insights & Analysis**")
                    if 'insights' in url_analysis:
                        st.write(url_analysis['insights'])
                    
                    if 'engagement_indicators' in url_analysis:
                        st.markdown("**💬 Engagement Patterns:**")
                        for indicator in url_analysis['engagement_indicators']:
                            st.write(f"• {indicator}")
                    
                    if 'content_themes' in url_analysis:
                        st.markdown("**🎨 Content Themes:**")
                        for theme in url_analysis['content_themes']:
                            st.write(f"• {theme}")
        
        # Overall insights
        if 'overall_insights' in results:
            st.markdown("### 🔮 Overall Insights")
            st.write(results['overall_insights'])

async def analyze_social_media_urls(urls):
    """Analyze social media URLs using the user agent"""
    try:
        # Use the social media analysis tool from user agent
        social_tool = user_agent.tools[1]  # SocialMediaAnalysisTool is the second tool
        result = await social_tool._arun(urls)
        return result
    except Exception as e:
        st.error(f"Error analyzing URLs: {str(e)}")
        return f"Analysis failed: {str(e)}"

if __name__ == "__main__":
    main() 