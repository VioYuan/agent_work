import streamlit as st
import asyncio
from agents.user_agent import UserAgent
from agents.chatbot_agent import ChatbotAgent
from agents.management_agent import ManagementAgent
from database import Database
from auth import SimpleAuth, show_login_page
from admin_config import AdminConfig
import json
import os
import time
from datetime import datetime

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
auth = SimpleAuth()
admin_config = AdminConfig()

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
if 'chat_loading' not in st.session_state:
    st.session_state.chat_loading = False
if 'pending_message' not in st.session_state:
    st.session_state.pending_message = None
if 'last_analysis_time' not in st.session_state:
    st.session_state.last_analysis_time = None
if 'last_input' not in st.session_state:
    st.session_state.last_input = ""
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'cached_session_conversations' not in st.session_state:
    st.session_state.cached_session_conversations = None
if 'cached_user_id' not in st.session_state:
    st.session_state.cached_user_id = None
if 'cached_daily_summaries' not in st.session_state:
    st.session_state.cached_daily_summaries = None
if 'cached_recent_sentiment' not in st.session_state:
    st.session_state.cached_recent_sentiment = None

def main():
    # Check authentication first
    if not auth.is_authenticated():
        show_login_page()
        return
    
    st.title("🌸 Hana-chan's Social Media & Chat System")
    
    # Get current user info for display
    current_user = auth.get_current_user()
    if current_user:
        # User info in sidebar
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 User Profile")
        
        # Display user avatar if available
        if current_user.get('picture'):
            st.sidebar.image(current_user['picture'], width=60)
        
        st.sidebar.write(f"**{current_user['name']}**")
        st.sidebar.write(f"📧 {current_user.get('email', 'No email')}")
        
        # Logout button
        if st.sidebar.button("Logout"):
            auth.logout()
            # Clear all cached data on logout
            st.session_state.cached_user_id = None
            st.session_state.cached_session_conversations = None
            st.session_state.cached_daily_summaries = None
            st.session_state.cached_recent_sentiment = None
            st.rerun()
    
    # Sidebar for navigation
    navigation_options = [
        "🏠 Profile Setup", 
        "💬 Hana Chat", 
        "📱 Social Media Analysis"
    ]
    
    # Check if current user is admin
    current_user = auth.get_current_user()
    is_admin = False
    if current_user and current_user.get('email'):
        is_admin = admin_config.is_admin(current_user['email'])
    
    # Add admin options if user is admin
    if is_admin:
        navigation_options.extend([
            "👥 User Management",
            "⚙️ Admin Panel"
        ])
    else:
        navigation_options.append("👤 My Account")
    
    page = st.sidebar.selectbox("Choose a page", navigation_options)
    
    if page == "🏠 Profile Setup":
        show_profile_setup()
    elif page == "💬 Hana Chat":
        show_chat()
    elif page == "📱 Social Media Analysis":
        show_social_media_analysis()
    elif page == "👥 User Management" and is_admin:
        show_user_management()
    elif page == "⚙️ Admin Panel" and is_admin:
        show_admin_panel()
    elif page == "👤 My Account":
        show_my_account()
    else:
        st.error("Access denied or page not found")

def show_profile_setup():
    st.header("👤 User Profile Setup")
    
    # Get current user
    current_user = auth.get_current_user()
    if not current_user:
        st.error("User not found!")
        return
    
    # Show current profile information
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if current_user.get('picture'):
            st.image(current_user['picture'], width=100)
    
    with col2:
        st.markdown(f"### Welcome, {current_user['name']}! 👋")
        st.markdown(f"**Email:** {current_user.get('email', 'No email')}")
        st.markdown(f"**Member since:** {current_user.get('created_at', 'Unknown')}")
        
        # Show conversation count
        conv_count = db.get_user_conversation_count(current_user['id'])
        st.markdown(f"**Total conversations:** {conv_count}")
    
    st.markdown("---")
    
    # Check if user has completed profile setup
    if current_user.get('interests') and current_user.get('social_links'):
        st.success("✅ Your profile is set up!")
        
        # Show current social media links if available
        if current_user.get('social_links'):
            st.subheader("📱 Your Social Media Profiles")
            for i, link in enumerate(current_user['social_links'], 1):
                st.write(f"{i}. {link}")
            
            if st.button("Re-analyze Social Media"):
                with st.spinner("Re-analyzing your social media profiles..."):
                    result = asyncio.run(analyze_social_media_urls(current_user['social_links']))
                    st.session_state.social_analysis_results = result
                    st.success("✅ Social media analysis updated!")
                    st.rerun()
    
    # Profile update form - Always show this section for editing
    with st.expander("✏️ Update Your Profile", expanded=not (current_user.get('interests') and current_user.get('social_links'))):
        with st.form("profile_update_form"):
            st.subheader("👤 Update Personal Information")
            
            # Add name field for editing
            name = st.text_input(
                "Full Name", 
                value=current_user.get('name', ''),
                help="Update your display name"
            )
            
            # Add occupation field
            occupation_options = [
                "Select your occupation...",
                "Student",
                "Software Engineer", 
                "Teacher/Educator",
                "Healthcare Worker",
                "Artist/Creative Professional",
                "Business Professional",
                "Entrepreneur",
                "Engineer (Non-Software)",
                "Marketing/Sales",
                "Finance/Accounting",
                "Lawyer/Legal Professional",
                "Researcher/Scientist",
                "Designer (Graphic/UX/UI)",
                "Writer/Journalist",
                "Consultant",
                "Manager/Executive",
                "Customer Service",
                "Retail/Service Industry",
                "Government/Public Service",
                "Non-Profit Worker",
                "Freelancer/Self-Employed",
                "Retired",
                "Unemployed/Job Seeking",
                "Other"
            ]
            
            current_occupation = current_user.get('occupation', '')
            # Find the index of current occupation, default to 0 if not found
            try:
                occupation_index = occupation_options.index(current_occupation) if current_occupation in occupation_options else 0
            except ValueError:
                occupation_index = 0
            
            occupation = st.selectbox(
                "Occupation", 
                options=occupation_options,
                index=occupation_index,
                help="Choose your occupation or job type"
            )
            
            interests = st.text_area(
                "Interests and Hobbies", 
                value=current_user.get('interests', ''),
                help="Tell us about your interests, hobbies, and what you're passionate about"
            )
            
            age = st.number_input(
                "Age", 
                min_value=0, 
                max_value=120, 
                value=current_user.get('age', 0) if current_user.get('age') else 0,
                help="Your age (optional)"
            )
            
            st.subheader("📱 Update Social Media Links")
            
            # Pre-fill existing social media links
            existing_links = current_user.get('social_links', [])
            
            col1, col2 = st.columns(2)
            
            with col1:
                instagram = st.text_input(
                    "📸 Instagram Profile", 
                    value=next((link for link in existing_links if 'instagram.com' in link), ''),
                    placeholder="https://www.instagram.com/username/"
                )
                twitter = st.text_input(
                    "🐦 Twitter/X Profile", 
                    value=next((link for link in existing_links if 'twitter.com' in link or 'x.com' in link), ''),
                    placeholder="https://twitter.com/username"
                )
            
            with col2:
                threads = st.text_input(
                    "🧵 Threads Profile", 
                    value=next((link for link in existing_links if 'threads.com' in link), ''),
                    placeholder="https://www.threads.com/@username"
                )
                linkedin = st.text_input(
                    "💼 LinkedIn Profile", 
                    value=next((link for link in existing_links if 'linkedin.com' in link), ''),
                    placeholder="https://www.linkedin.com/in/username/"
                )
            
            if st.form_submit_button("Update Profile", type="primary"):
                # Validate name
                if not name or len(name.strip()) < 2:
                    st.error("❌ Name must be at least 2 characters long")
                    return
                
                # Collect all social media links
                social_links = [link.strip() for link in [instagram, twitter, threads, linkedin] 
                              if link and link.strip()]
                
                # Update profile
                profile_updates = {
                    'name': name.strip() if name else current_user.get('name', ''),
                    'occupation': occupation if occupation != "Select your occupation..." else '',
                    'interests': interests.strip() if interests else '',
                    'age': age if age > 0 else None,
                    'social_links': social_links
                }
                
                # Process with user agent if social links changed
                existing_links = current_user.get('social_links', [])
                if social_links != existing_links or not current_user.get('user_context'):
                    with st.spinner("🔄 Re-analyzing your profile..."):
                        result = asyncio.run(process_user_profile({
                            'name': name.strip(),
                            'occupation': occupation if occupation != "Select your occupation..." else '',
                            'age': age,
                            'interests': interests
                        }, social_links))
                        
                        profile_updates['user_context'] = {
                            "profile_analysis": str(result["profile_analysis"]),
                            "social_analysis": str(result["social_analysis"]),
                            "combined_context": str(result["combined_context"])
                        }
                
                # Save updates to database
                if db.update_user_profile(current_user['id'], profile_updates):
                    st.success("✅ Profile updated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to update profile.")
    
    # Password change for password-based accounts
    if current_user.get('auth_type') in ['password', 'hybrid']:
        with st.expander("🔒 Change Password"):
            with st.form("password_change_form"):
                st.subheader("🔒 Update Your Password")
                old_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Change Password", type="secondary"):
                    if not old_password or not new_password:
                        st.error("❌ Please fill in all fields")
                    elif new_password != confirm_password:
                        st.error("❌ New passwords do not match")
                    else:
                        success, message = auth.change_password(current_user['id'], old_password, new_password)
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")

def show_user_management():
    st.header("👥 User Management")
    
    # Verify admin access
    current_user = auth.get_current_user()
    if not current_user or not admin_config.is_admin(current_user['email']):
        st.error("🚫 Access denied. Admin privileges required.")
        st.info("This page is only accessible to system administrators.")
        return
    
    # Admin-only view
    st.success(f"👋 Admin access granted for {current_user['name']}")
    st.info("🔧 **Admin View**: This page shows all users for management purposes.")
    
    # Show all users
    users = db.get_all_users()
    if users:
        st.subheader("Registered Users")
        for user in users:
            # Handle missing keys gracefully
            user_name = user.get('name', 'Unknown User')
            user_email = user.get('email', 'No email')
            user_age = user.get('age', 'Unknown')
            
            with st.expander(f"{user_name} ({user_email})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**👤 User Details:**")
                    st.write(f"**ID:** {user['id']}")
                    st.write(f"**Name:** {user_name}")
                    st.write(f"**Email:** {user_email}")
                    st.write(f"**Occupation:** {user.get('occupation', 'Not specified')}")
                    st.write(f"**Age:** {user_age}")
                    st.write(f"**Google ID:** {user.get('google_id', 'Not linked')}")
                    st.write(f"**Created:** {user.get('created_at', 'Unknown')}")
                    st.write(f"**Last Login:** {user.get('last_login', 'Unknown')}")
                
                with col2:
                    # Show user avatar if available
                    if user.get('picture'):
                        st.image(user['picture'], width=80)
                    
                    # Conversation count
                    conv_count = db.get_user_conversation_count(user['id'])
                    st.metric("💬 Total Conversations", conv_count)
                
                # Show user details with safe key access
                interests = user.get('interests', 'Not specified')
                st.write(f"**Interests:** {interests}")
                
                social_links = user.get('social_links', [])
                if social_links:
                    st.write(f"**Social Links:** {len(social_links)} profiles")
                    for i, link in enumerate(social_links[:3], 1):  # Show first 3
                        st.write(f"  {i}. {link}")
                    if len(social_links) > 3:
                        st.write(f"  ... and {len(social_links) - 3} more")
                else:
                    st.write("**Social Links:** None")
                
                # Show user context if available (without nested expander)
                user_context = user.get('user_context', {})
                if user_context:
                    st.markdown("**User Context Summary:**")
                    if isinstance(user_context, dict):
                        if 'profile_analysis' in user_context:
                            st.write("🔍 **Profile Analysis:**")
                            profile_text = str(user_context['profile_analysis'])
                            st.write(profile_text[:200] + "..." if len(profile_text) > 200 else profile_text)
                        if 'social_analysis' in user_context:
                            st.write("📱 **Social Analysis:**")
                            social_text = str(user_context['social_analysis'])
                            st.write(social_text[:200] + "..." if len(social_text) > 200 else social_text)
                    else:
                        st.write("Context available but not in expected format")
                
                # Admin actions
                st.markdown("---")
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if st.button(f"Delete User", key=f"delete_{user['id']}", type="secondary"):
                        if db.delete_user(user['id']):
                            st.success(f"Deleted user {user_name}")
                            st.rerun()
                        else:
                            st.error("Failed to delete user")
                
                with col_b:
                    # Show button to view full context
                    if user_context:
                        if st.button(f"View Full Context", key=f"context_{user['id']}"):
                            st.session_state[f"show_context_{user['id']}"] = True
                            st.rerun()
        
        # Show full context outside of expanders if requested
        for user in users:
            if st.session_state.get(f"show_context_{user['id']}", False):
                st.markdown("---")
                st.subheader(f"Full Context for {user.get('name', 'Unknown User')}")
                
                user_context = user.get('user_context', {})
                if isinstance(user_context, dict):
                    if 'profile_analysis' in user_context:
                        st.markdown("### 🔍 Profile Analysis")
                        st.write(user_context['profile_analysis'])
                    if 'social_analysis' in user_context:
                        st.markdown("### 📱 Social Analysis")
                        st.write(user_context['social_analysis'])
                    if 'combined_context' in user_context:
                        st.markdown("### 🎯 Combined Context")
                        st.write(user_context['combined_context'])
                else:
                    st.write("Context not in expected format")
                
                if st.button(f"Hide Context", key=f"hide_context_{user['id']}"):
                    st.session_state[f"show_context_{user['id']}"] = False
                    st.rerun()
    else:
        st.info("No users registered yet.")

async def process_user_profile(user_profile, social_links):
    # Process with user agent
    result = await user_agent.process({
        "user_profile": user_profile,
        "social_links": social_links
    })
    return result

def show_my_account():
    st.header("👤 My Account")
    
    # Get current user
    current_user = auth.get_current_user()
    if not current_user:
        st.error("User not found!")
        return
    
    # Show current profile information
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if current_user.get('picture'):
            st.image(current_user['picture'], width=100)
        else:
            st.markdown("📸 No profile picture")
    
    with col2:
        st.markdown(f"### Welcome, {current_user['name']}! 👋")
        st.markdown(f"**Email:** {current_user.get('email', 'No email')}")
        st.markdown(f"**Account Type:** {current_user.get('auth_type', 'Unknown').title()}")
        st.markdown(f"**Member since:** {current_user.get('created_at', 'Unknown')}")
        st.markdown(f"**Last login:** {current_user.get('last_login', 'Unknown')}")
        
        # Show conversation count
        conv_count = db.get_user_conversation_count(current_user['id'])
        st.markdown(f"**Total conversations:** {conv_count}")
    
    st.markdown("---")
    
    # Account Information
    st.subheader("📊 Account Details")
    
    # Personal Information
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Personal Information:**")
        st.write(f"**Occupation:** {current_user.get('occupation', 'Not specified')}")
        st.write(f"**Age:** {current_user.get('age', 'Not specified')}")
        interests = current_user.get('interests', 'Not specified')
        st.write(f"**Interests:** {interests}")
    
    with col2:
        st.markdown("**Social Media Links:**")
        social_links = current_user.get('social_links', [])
        if social_links:
            for i, link in enumerate(social_links, 1):
                st.write(f"{i}. {link}")
        else:
            st.write("No social media links added")
    
    # User Context Summary (if available)
    user_context = current_user.get('user_context', {})
    if user_context:
        st.subheader("🔍 Profile Analysis Summary")
        
        if isinstance(user_context, dict):
            if 'profile_analysis' in user_context:
                with st.expander("📋 Profile Analysis"):
                    profile_text = str(user_context['profile_analysis'])
                    st.write(profile_text[:500] + "..." if len(profile_text) > 500 else profile_text)
            
            if 'social_analysis' in user_context:
                with st.expander("📱 Social Media Analysis"):
                    social_text = str(user_context['social_analysis'])
                    st.write(social_text[:500] + "..." if len(social_text) > 500 else social_text)
    
    # Recent Conversations
    st.subheader("💬 Recent Chat Sessions")
    
    # Add refresh button
    col_refresh, col_info = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh", help="Refresh chat sessions from database"):
            st.session_state.cached_session_conversations = db.get_user_conversations_by_session(current_user['id'], limit=5)
            st.session_state.cached_user_id = current_user['id']
            st.rerun()
    
    with col_info:
        if st.session_state.cached_session_conversations is not None:
            st.caption("💡 Chat sessions are cached for better performance. Use refresh if needed.")
    
    # Check if we need to load session conversations from database
    if (st.session_state.cached_session_conversations is None or 
        st.session_state.cached_user_id != current_user['id']):
        # Load session conversations from database only once per session
        st.session_state.cached_session_conversations = db.get_user_conversations_by_session(current_user['id'], limit=5)
        st.session_state.cached_user_id = current_user['id']
    
    session_conversations = st.session_state.cached_session_conversations
    
    if session_conversations:
        for i, session in enumerate(session_conversations, 1):
            # Create session header with metrics
            session_date = session['session_date']
            conv_count = session['conversation_count']
            avg_score = session['avg_satisfaction']
            
            # Determine session quality emoji
            if avg_score >= 8.0:
                quality_emoji = "🌟"
            elif avg_score >= 6.0:
                quality_emoji = "😊"
            elif avg_score >= 4.0:
                quality_emoji = "😐"
            else:
                quality_emoji = "😕"
            
            # Session duration calculation
            session_start = session['session_start']
            session_end = session['session_end']
            
            with st.expander(f"{quality_emoji} Session {i} - {session_date} ({conv_count} chats, Score: {avg_score}/10)"):
                # Session overview
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                
                with col_stats1:
                    st.metric("💬 Total Chats", conv_count)
                
                with col_stats2:
                    st.metric("⭐ Avg Score", f"{avg_score}/10")
                
                with col_stats3:
                    if session_start and session_end:
                        st.metric("⏰ Session Time", f"{session_start.split()[1][:5]} - {session_end.split()[1][:5]}")
                
                st.markdown("---")
                
                # Show conversations with smart truncation
                conversation_pairs = session['conversation_pairs']
                is_long = session['is_long_session']
                
                if is_long and len(conversation_pairs) > 3:
                    # Show first 2 and last 1 conversations for long sessions
                    st.markdown("**🔹 First conversations:**")
                    for j, pair in enumerate(conversation_pairs[:2], 1):
                        with st.container():
                            st.markdown(f"**Chat {j}:**")
                            st.markdown(f"**You:** {pair['message'][:200]}{'...' if len(pair['message']) > 200 else ''}")
                            st.markdown(f"**Hana-chan:** {pair['response'][:200]}{'...' if len(pair['response']) > 200 else ''}")
                            st.markdown("")
                    
                    # Show middle conversation count
                    middle_count = len(conversation_pairs) - 3
                    if middle_count > 0:
                        st.markdown(f"**📋 ... {middle_count} more conversations in this session ...**")
                        st.markdown("")
                    
                    # Show last conversation
                    if len(conversation_pairs) > 2:
                        st.markdown("**🔹 Latest conversation:**")
                        last_pair = conversation_pairs[-1]
                        st.markdown(f"**You:** {last_pair['message'][:200]}{'...' if len(last_pair['message']) > 200 else ''}")
                        st.markdown(f"**Hana-chan:** {last_pair['response'][:200]}{'...' if len(last_pair['response']) > 200 else ''}")
                    
                    # Show full session option
                    if st.button(f"📖 Show All {conv_count} Conversations", key=f"show_all_{i}"):
                        st.markdown("**🔹 Complete Session:**")
                        for j, pair in enumerate(conversation_pairs, 1):
                            with st.container():
                                st.markdown(f"**Chat {j}:**")
                                st.markdown(f"**You:** {pair['message']}")
                                st.markdown(f"**Hana-chan:** {pair['response']}")
                                if j < len(conversation_pairs):
                                    st.markdown("---")
                else:
                    # Show all conversations for shorter sessions
                    st.markdown("**🔹 Complete Session:**")
                    for j, pair in enumerate(conversation_pairs, 1):
                        with st.container():
                            st.markdown(f"**Chat {j}:**")
                            st.markdown(f"**You:** {pair['message']}")
                            st.markdown(f"**Hana-chan:** {pair['response']}")
                            if j < len(conversation_pairs):
                                st.markdown("---")
                
                # Session summary
                if session['total_characters'] > 0:
                    st.markdown("---")
                    st.caption(f"📊 Session stats: {session['total_characters']} characters total")
    else:
        st.info("No chat sessions yet. Start chatting with Hana-chan!")
    
    # Sentiment Analysis Summary
    st.subheader("📊 Emotional Insights & Daily Summary")
    
    # Add refresh button for sentiment data too
    col_refresh_sent, col_info_sent = st.columns([1, 4])
    with col_refresh_sent:
        if st.button("🔄 Refresh Insights", help="Refresh emotional insights from database"):
            st.session_state.cached_daily_summaries = None
            st.session_state.cached_recent_sentiment = None
            st.rerun()
    
    with col_info_sent:
        if st.session_state.cached_daily_summaries is not None:
            st.caption("📊 Emotional insights are cached for better performance.")
    
    # Load daily sentiment summaries (cached)
    if (st.session_state.cached_daily_summaries is None or 
        st.session_state.cached_user_id != current_user['id']):
        st.session_state.cached_daily_summaries = db.get_daily_sentiment_summary(current_user['id'], days=7)
    
    daily_summaries = st.session_state.cached_daily_summaries
    
    if daily_summaries:
        st.markdown("**📈 Your Week at a Glance:**")
        
        # Create columns for metrics
        col1, col2, col3 = st.columns(3)
        
        # Calculate weekly averages
        week_sentiment = sum(day['avg_sentiment'] for day in daily_summaries) / len(daily_summaries)
        week_engagement = sum(day['avg_engagement'] for day in daily_summaries) / len(daily_summaries)
        total_conversations = sum(day['conversation_count'] for day in daily_summaries)
        
        with col1:
            sentiment_emoji = "😊" if week_sentiment > 0.7 else "😐" if week_sentiment > 0.4 else "😔"
            st.metric("Weekly Mood", f"{sentiment_emoji} {week_sentiment:.1f}/1.0")
        
        with col2:
            engagement_emoji = "🚀" if week_engagement > 0.7 else "👍" if week_engagement > 0.4 else "😴"
            st.metric("Engagement Level", f"{engagement_emoji} {week_engagement:.1f}/1.0")
        
        with col3:
            st.metric("Total Chats", f"💬 {total_conversations}")
        
        # Daily breakdown
        st.markdown("**📅 Daily Breakdown:**")
        for day in daily_summaries:
            with st.expander(f"{day['date']} - {day['conversation_count']} conversations"):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    mood_emoji = "😊" if day['avg_sentiment'] > 0.7 else "😐" if day['avg_sentiment'] > 0.4 else "😔"
                    st.metric("Daily Mood", f"{mood_emoji} {day['avg_sentiment']}/1.0")
                
                with col_b:
                    energy_emoji = "⚡" if day['avg_engagement'] > 0.7 else "👍" if day['avg_engagement'] > 0.4 else "😴"
                    st.metric("Energy Level", f"{energy_emoji} {day['avg_engagement']}/1.0")
                
                st.markdown("**Daily Summary:**")
                # Split long summaries and show key points
                summary_parts = day['daily_summary'].split(' | ')
                for part in summary_parts[:3]:  # Show first 3 summaries
                    if part.strip():
                        st.write(f"• {part.strip()}")
                
                if len(summary_parts) > 3:
                    st.write(f"• ... and {len(summary_parts) - 3} more conversations")
    
    # Recent Emotional Analysis
    if (st.session_state.cached_recent_sentiment is None or 
        st.session_state.cached_user_id != current_user['id']):
        st.session_state.cached_recent_sentiment = db.get_recent_sentiment_analysis(current_user['id'], limit=3)
    
    recent_sentiment = st.session_state.cached_recent_sentiment
    
    if recent_sentiment:
        st.markdown("**🎭 Recent Emotional Patterns:**")
        
        for i, analysis in enumerate(recent_sentiment, 1):
            with st.expander(f"Analysis {i} - {analysis['analysis_date'][:10]}"):
                col_x, col_y = st.columns(2)
                
                with col_x:
                    st.markdown("**Emotions Detected:**")
                    emotions = analysis['emotions_detected']
                    if emotions:
                        emotion_text = ", ".join([f"**{emotion}**" for emotion in emotions[:4]])
                        st.markdown(emotion_text)
                    else:
                        st.write("Neutral conversation")
                
                with col_y:
                    st.markdown("**Main Topics:**")
                    topics = analysis['main_topics']
                    if topics:
                        topic_text = ", ".join([f"*{topic}*" for topic in topics[:3]])
                        st.markdown(topic_text)
                    else:
                        st.write("General conversation")
                
                if analysis['emotional_summary']:
                    st.markdown(f"**Summary:** {analysis['emotional_summary']}")
                
                if analysis['mood_progression']:
                    st.markdown(f"**Mood Journey:** {analysis['mood_progression']}")
    else:
        st.info("💫 Start chatting with Hana-chan to see your emotional insights!")
    
    # Quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Edit Profile", use_container_width=True):
            st.info("Go to 'Profile Setup' page to edit your profile")
    
    with col2:
        if st.button("Start Chat", use_container_width=True):
            st.info("Go to 'Hana Chat' page to start chatting")
    
    with col3:
        if st.button("Analyze Social Media", use_container_width=True):
            st.info("Go to 'Social Media Analysis' page for insights")

def show_admin_panel():
    st.header("⚙️ Admin Panel")
    
    # Get current user to verify admin status
    current_user = auth.get_current_user()
    if not current_user or not admin_config.is_admin(current_user['email']):
        st.error("🚫 Access denied. Admin privileges required.")
        return
    
    st.success(f"👋 Welcome, Admin {current_user['name']}!")
    
    # Admin Statistics
    st.subheader("📊 System Statistics")
    
    # Get system stats
    all_users = db.get_all_users()
    total_users = len(all_users)
    admin_users = admin_config.get_active_admins()
    
    # Calculate total conversations
    total_conversations = 0
    for user in all_users:
        total_conversations += db.get_user_conversation_count(user['id'])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", total_users)
    with col2:
        st.metric("Admin Users", len(admin_users))
    with col3:
        st.metric("Total Conversations", total_conversations)
    with col4:
        avg_conversations = round(total_conversations / total_users, 1) if total_users > 0 else 0
        st.metric("Avg Conversations/User", avg_conversations)
    
    st.markdown("---")
    
    # Admin Management
    st.subheader("👥 Admin Management")
    
    # Current Admins
    st.markdown("**Current Admins:**")
    admins = admin_config.get_all_admins()
    
    for admin in admins:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            status_icon = "✅" if admin['is_active'] else "❌"
            st.write(f"{status_icon} {admin['email']}")
        with col2:
            st.write(f"Added by: {admin['added_by']}")
        with col3:
            st.write(f"Date: {admin['created_at']}")
        with col4:
            if admin['is_active'] and admin['email'] != current_user['email']:
                if st.button("Remove", key=f"remove_admin_{admin['email']}", type="secondary"):
                    if admin_config.remove_admin(admin['email']):
                        st.success(f"Removed admin privileges from {admin['email']}")
                        st.rerun()
                    else:
                        st.error("Failed to remove admin")
    
    # Add New Admin
    st.markdown("**Add New Admin:**")
    with st.form("add_admin_form"):
        new_admin_email = st.text_input("Email address", placeholder="admin@example.com")
        add_admin_submitted = st.form_submit_button("Add Admin", type="primary")
        
        if add_admin_submitted:
            if not new_admin_email:
                st.error("Please enter an email address")
            elif admin_config.add_admin(new_admin_email, current_user['email']):
                st.success(f"Added {new_admin_email} as admin")
                st.rerun()
            else:
                st.error("Failed to add admin (email might already be an admin)")
    
    st.markdown("---")
    
    # User Account Types Breakdown
    st.subheader("📈 User Analysis")
    
    # Count by auth type
    password_users = len([u for u in all_users if u.get('auth_type') == 'password'])
    google_users = len([u for u in all_users if u.get('auth_type') == 'google'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Password Users", password_users)
        st.metric("Google Users", google_users)
    
    with col2:
        # Recent user registrations
        recent_users = sorted(all_users, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        st.markdown("**Recent Registrations:**")
        for user in recent_users:
            st.write(f"• {user['name']} ({user.get('auth_type', 'unknown')}) - {user.get('created_at', 'Unknown')}")
    
    # System Actions
    st.markdown("---")
    st.subheader("🛠️ System Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export User Data", use_container_width=True):
            st.info("Feature coming soon: Export user data to CSV")
    
    with col2:
        if st.button("System Health Check", use_container_width=True):
            st.success("✅ System is running normally")
            st.info(f"Database: Connected\nAdmin users: {len(admin_users)}\nTotal users: {total_users}")
    
    with col3:
        if st.button("View System Logs", use_container_width=True):
            st.info("Feature coming soon: System logs viewer")

def show_chat():
    st.header("💬 Hana Chat")
    
    # Get current authenticated user
    current_user = auth.get_current_user()
    if not current_user:
        st.error("User not found!")
        return
    
    # Check if user has completed profile setup
    if not current_user.get('interests'):
        st.warning("⚠️ Please complete your profile setup first!")
        st.markdown("👉 Go to the **Profile Setup** page to get started.")
        return
    
    # Load user's conversation history
    if not st.session_state.conversation_history:
        # Load conversation history from database
        conversations = db.get_user_conversations(current_user['id'], limit=20)
        chat_history = []
        for conv in conversations:
            chat_history.append({"role": "user", "content": conv['message']})
            chat_history.append({"role": "assistant", "content": conv['response']})
        # Conversations are now in correct chronological order (oldest first)
        st.session_state.conversation_history = chat_history
    
    # Load user context
    if not st.session_state.user_context and current_user.get('user_context'):
        st.session_state.user_context = current_user['user_context']
    
    user_name = current_user['name']
    
    # Social media style chat header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; text-align: center;">
        <h2>💬 Chat with Hana-chan</h2>
        <p>Hey {user_name}! 👋 Let's have a conversation!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat container with social media styling
    chat_container = st.container()
    
    with chat_container:
        # Display conversation history with social media styling
        for i, message in enumerate(st.session_state.conversation_history):
            if message["role"] == "user":
                # User message - right aligned, blue bubble
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; padding: 12px 16px; border-radius: 18px; 
                                max-width: 70%; word-wrap: break-word; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        {message['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # AI message - left aligned, gray bubble
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                    <div style="background: #f0f2f5; color: #1c1e21; padding: 12px 16px; 
                                border-radius: 18px; max-width: 70%; word-wrap: break-word; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <strong>🌸 Hana-chan:</strong> {message['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Show typing indicator if loading
    if st.session_state.chat_loading:
        st.markdown("""
        <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
            <div style="background: #f0f2f5; color: #1c1e21; padding: 12px 16px; 
                        border-radius: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
                        display: flex; align-items: center;">
                <strong>🌸 Hana-chan:</strong>
                <div style="margin-left: 10px; display: flex; align-items: center;">
                    <div class="typing-indicator">
                        <div class="typing-circle"></div>
                        <div class="typing-circle"></div>
                        <div class="typing-circle"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .typing-circle {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #999;
            animation: typing 1.4s ease-in-out infinite;
        }
        
        .typing-circle:nth-child(1) {
            animation-delay: 0ms;
        }
        
        .typing-circle:nth-child(2) {
            animation-delay: 200ms;
        }
        
        .typing-circle:nth-child(3) {
            animation-delay: 400ms;
        }
        
        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.4;
            }
            30% {
                transform: translateY(-10px);
                opacity: 1;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Chat input with social media styling
    st.markdown("---")
    
    # Initialize message counter if not exists
    if 'message_counter' not in st.session_state:
        st.session_state.message_counter = 0
    
    # Input area with dynamic key to force refresh
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_input(
            "💬 Type your message...",
            placeholder="What's on your mind?",
            key=f"chat_input_{st.session_state.message_counter}",
            label_visibility="collapsed"
        )
    
    with col2:
        send_button = st.button("Send", use_container_width=True, type="primary")
    
    # Handle message sending
    if send_button and user_input:
        # Increment counter to create new input field
        st.session_state.message_counter += 1
        
        # Add user message to conversation history immediately
        st.session_state.conversation_history.append({"role": "user", "content": user_input})
        
        # Set loading state and rerun to show typing indicator
        st.session_state.chat_loading = True
        st.session_state.pending_message = user_input
        st.rerun()
    
    # Process pending message if there is one
    if st.session_state.get('pending_message') and st.session_state.chat_loading:
        message = st.session_state.pending_message
        # Clear the pending message
        st.session_state.pending_message = None
        
        # Process message
        asyncio.run(process_message_async(message))
        
        # Clear loading state
        st.session_state.chat_loading = False
        
        # Rerun to update the chat with the response
        st.rerun()
    
    # Show conversation analysis status (non-blocking)
    if st.session_state.last_analysis_time:
        time_since = time.time() - st.session_state.last_analysis_time
        if time_since < 300:  # Show for 5 minutes after analysis
            st.info(f"📊 Conversation analysis completed {int(time_since)}s ago")
    
    # Show analysis results in expander (not always visible)
    if st.session_state.satisfaction_metrics and st.session_state.last_analysis_time and time.time() - st.session_state.last_analysis_time < 300:
        with st.expander("📊 Recent Conversation Analysis"):
            metrics = st.session_state.satisfaction_metrics
            if isinstance(metrics, dict):
                col1, col2 = st.columns(2)
                with col1:
                    if "satisfaction_score" in metrics:
                        st.metric("😊 Satisfaction", f"{metrics['satisfaction_score']:.1f}/10")
                with col2:
                    if "quality_metrics" in metrics and "engagement" in metrics["quality_metrics"]:
                        st.metric("💬 Engagement", f"{metrics['quality_metrics']['engagement']:.1f}/10")
                
                if "recommendations" in metrics:
                    st.markdown("**💡 Suggestions:**")
                    for rec in metrics["recommendations"][:3]:  # Show only top 3
                        st.markdown(f"• {rec}")

async def process_message_async(message):
    """Process message asynchronously without blocking the UI"""
    try:
        # Get current user for saving to database
        current_user = auth.get_current_user()
        if not current_user:
            st.error("User not authenticated!")
            return
        
        # Process with chatbot agent
        response = await chatbot_agent.process({
            "message": message,
            "context": st.session_state.user_context or {},
            "history": st.session_state.conversation_history,
            "user_profile": {
                "name": current_user.get('name', ''),
                "age": current_user.get('age', ''),
                "occupation": current_user.get('occupation', ''),
                "interests": current_user.get('interests', ''),
                "auth_type": current_user.get('auth_type', '')
            }
        })
        
        # Update conversation history with just the assistant response
        st.session_state.conversation_history.append({"role": "assistant", "content": response})
        
        # Save conversation to database immediately
        conversation_id = None
        if current_user:
            conversation_id = db.save_conversation(
                user_id=current_user['id'],
                message=message,
                response=response,
                satisfaction_score=0.8  # Default score, will be updated by background analysis
            )
        
        # Start background analysis (non-blocking) with conversation ID
        asyncio.create_task(background_conversation_analysis(current_user['id'], conversation_id))
        
    except Exception as e:
        st.error(f"Error processing message: {str(e)}")

async def background_conversation_analysis(user_id, conversation_id):
    """Run conversation analysis in the background"""
    try:
        # Wait a bit to avoid overwhelming the system
        await asyncio.sleep(2)
        
        # Process with management agent (includes sentiment analysis now)
        result = await management_agent.process({
            "conversation": st.session_state.conversation_history,
            "user_context": st.session_state.user_context or {}
        })
        
        # Update session state with all analysis results
        st.session_state.satisfaction_metrics = result
        st.session_state.last_analysis_time = time.time()
        
        # Save sentiment analysis to database if we have the data
        if conversation_id and "sentiment_analysis" in result:
            db.save_sentiment_analysis(
                user_id=user_id,
                conversation_id=conversation_id,
                sentiment_data=result["sentiment_analysis"]
            )
        
        # Refresh cached conversations if this user's cache exists
        if (st.session_state.cached_user_id == user_id and 
            st.session_state.cached_session_conversations is not None):
            # Update the cached conversations with the latest data
            st.session_state.cached_session_conversations = db.get_user_conversations_by_session(user_id, limit=5)
        
        # Refresh cached sentiment data if this user's cache exists
        if (st.session_state.cached_user_id == user_id and 
            (st.session_state.cached_daily_summaries is not None or 
             st.session_state.cached_recent_sentiment is not None)):
            # Update sentiment caches with the latest data
            st.session_state.cached_daily_summaries = db.get_daily_sentiment_summary(user_id, days=7)
            st.session_state.cached_recent_sentiment = db.get_recent_sentiment_analysis(user_id, limit=3)
        
    except Exception as e:
        # Silently handle errors in background task
        print(f"Background analysis error: {str(e)}")
        pass

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
        if st.button("Instagram Example"):
            st.session_state.example_url = "https://www.instagram.com/lalalalisa_m/"
    with col2:
        if st.button("Twitter Example"):
            st.session_state.example_url = "https://twitter.com/elonmusk"
    with col3:
        if st.button("Threads Example"):
            st.session_state.example_url = "https://www.threads.com/@zuck"
    with col4:
        if st.button("LinkedIn Example"):
            st.session_state.example_url = "https://www.linkedin.com/in/satyanadella/"
    
    # Show example URL if selected
    if hasattr(st.session_state, 'example_url'):
        st.info(f"Example URL: {st.session_state.example_url}")
        if st.button("Use This Example"):
            url1 = st.session_state.example_url
            st.rerun()
    
    # Analysis button
    if st.button("Analyze Social Media Profiles", type="primary"):
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
            st.markdown("### 🎯 Overall Insights")
            st.write(results['overall_insights'])
        
        # Recommendations
        if 'recommendations' in results:
            st.markdown("### 💡 Recommendations")
            for rec in results['recommendations']:
                st.markdown(f"• {rec}")
    else:
        st.write(results)

async def analyze_social_media_urls(urls):
    """Analyze social media URLs using the user agent"""
    try:
        result = await user_agent.process({
            "social_media_urls": urls
        })
        return result
    except Exception as e:
        return f"Error analyzing URLs: {str(e)}"

if __name__ == "__main__":
    main() 