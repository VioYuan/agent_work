import streamlit as st
import os
import hashlib

class GoogleOAuth:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8501')
    
    def is_configured(self):
        """Check if Google OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)
    
    def get_user_from_token(self):
        """Mock: Get user info from stored token"""
        # For now, return None (no persistent Google login)
        return None
    
    def logout(self):
        """Mock: Remove authentication token"""
        # Clear any Google-related session state
        if 'google_user_info' in st.session_state:
            del st.session_state['google_user_info']
    
    def show_login_button(self):
        """Show Google login information and setup instructions"""
        if not self.is_configured():
            st.warning("🔧 **Google OAuth Setup Required**")
            st.markdown("""
            To enable real Google sign-in, you need to:
            
            1. **Create a Google Cloud Project** at [Google Cloud Console](https://console.cloud.google.com/)
            2. **Enable Google+ API or Google Identity Services**
            3. **Create OAuth 2.0 credentials**
            4. **Set environment variables:**
               ```bash
               export GOOGLE_CLIENT_ID="your-client-id"
               export GOOGLE_CLIENT_SECRET="your-client-secret"
               export GOOGLE_REDIRECT_URI="http://localhost:8501"
               export JWT_SECRET_KEY="your-secret-key"
               ```
            5. **Add authorized redirect URI:** `http://localhost:8501`
            6. **Install required packages:**
               ```bash
               pip install google-auth google-auth-oauthlib google-auth-httplib2 PyJWT extra-streamlit-components
               ```
            
            📖 **Setup Guide:** See `GOOGLE_OAUTH_SETUP.md` for detailed instructions
            
            ---
            
            **Demo Mode Available:** For now, you can still create accounts using email/password in the other tabs.
            """)
            
            # Show a demo button for testing
            st.info("🚧 **Demo Mode**: Since Google OAuth isn't configured, you can simulate it for testing:")
            
            with st.form("google_demo_form"):
                demo_email = st.text_input("📧 Your Google Email", placeholder="your@gmail.com")
                demo_name = st.text_input("👤 Your Name", placeholder="Your Full Name")
                demo_submitted = st.form_submit_button("Simulate Google Sign-in", type="secondary")
            
            if demo_submitted and demo_email and demo_name:
                # Create simulated Google user info
                google_user_info = {
                    'id': f"google_demo_{hashlib.md5(demo_email.encode()).hexdigest()}",
                    'email': demo_email,
                    'name': demo_name,
                    'picture': f"https://ui-avatars.com/api/?name={demo_name.replace(' ', '+')}&background=4285f4&color=fff",
                    'verified_email': True
                }
                return google_user_info
            
            return False
        else:
            # OAuth is configured but packages might not be installed
            st.error("❌ **Google OAuth packages not installed**")
            st.markdown("""
            The Google OAuth credentials are configured, but the required packages are not installed.
            
            **To fix this, run:**
            ```bash
            pip install google-auth google-auth-oauthlib google-auth-httplib2 PyJWT extra-streamlit-components
            ```
            
            **Then restart the app.**
            """)
            return False 