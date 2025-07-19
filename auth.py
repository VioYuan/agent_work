import streamlit as st
import hashlib
import secrets
import time
from database import Database
from google_auth import GoogleOAuth
import re

class SimpleAuth:
    def __init__(self):
        self.db = Database()
        self.google_oauth = GoogleOAuth()
    
    def hash_password(self, password):
        """Hash password with salt for security"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return salt + password_hash.hex()
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        salt = hashed_password[:32]
        password_hash = hashed_password[32:]
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() == password_hash
    
    def is_valid_email(self, email):
        """Check if email format is valid"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def create_account(self, name, email, password):
        """Create a new user account"""
        # Validate inputs
        if not name or len(name.strip()) < 2:
            return False, "Name must be at least 2 characters long"
        
        if not self.is_valid_email(email):
            return False, "Please enter a valid email address"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        # Check if email already exists
        existing_user = self.db.get_user_by_email(email)
        if existing_user:
            if existing_user.get('auth_type') == 'google':
                return False, "This email is already registered with a different authentication method."
            else:
                return False, "An account with this email already exists"
        
        # Create user profile
        hashed_password = self.hash_password(password)
        user_profile = {
            'name': name.strip(),
            'email': email.lower().strip(),
            'password_hash': hashed_password,
            'auth_type': 'password',
            'social_links': [],
            'user_context': {}
        }
        
        try:
            user_id = self.db.save_user_profile(user_profile)
            return True, user_id
        except Exception as e:
            return False, f"Failed to create account: {str(e)}"
    
    def login_with_password(self, email, password):
        """Login with email and password"""
        if not email or not password:
            return False, "Please enter both email and password"
        
        # Get user by email
        user = self.db.get_user_by_email(email.lower().strip())
        if not user:
            return False, "No account found with this email"
        
        # Check if this is a password-based account
        if user.get('auth_type') not in ['password', 'hybrid'] or not user.get('password_hash'):
            if user.get('auth_type') == 'google':
                return False, "This email is registered with a different authentication method."
            else:
                return False, "This account uses a different login method"
        
        # Verify password
        if self.verify_password(password, user['password_hash']):
            # Update last login
            self.db.update_user_login(user['id'])
            return True, user['id']
        else:
            return False, "Incorrect password"
    
    def login_with_google(self, google_user_info):
        """Login or create account with Google"""
        # Check if user already exists
        existing_user = self.db.get_user_by_email(google_user_info['email'])
        
        if existing_user:
            # Check if this was originally a password account
            if existing_user.get('auth_type') == 'password':
                return False, "This email is already registered with a password. Please use your email and password to sign in."
            
            # Update Google info and last login
            self.db.update_user_profile(existing_user['id'], {
                'google_id': google_user_info.get('id'),
                'picture': google_user_info.get('picture', ''),
                'auth_type': 'google'
            })
            self.db.update_user_login(existing_user['id'])
            return True, existing_user['id']
        else:
            # Create new Google user
            user_profile = {
                'name': google_user_info.get('name', ''),
                'email': google_user_info['email'],
                'google_id': google_user_info.get('id'),
                'picture': google_user_info.get('picture', ''),
                'auth_type': 'google',
                'social_links': [],
                'user_context': {}
            }
            
            try:
                user_id = self.db.save_user_profile(user_profile)
                return True, user_id
            except Exception as e:
                return False, f"Failed to create account: {str(e)}"
    
    def logout(self):
        """Clear authentication session"""
        keys_to_clear = [
            'user_id', 'user_context', 'conversation_history', 
            'satisfaction_metrics', 'social_analysis_results',
            'authenticated', 'user_info'
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Also logout from Google OAuth
        self.google_oauth.logout()
    
    def is_authenticated(self):
        """Check if user is currently authenticated"""
        return st.session_state.get('authenticated', False) and st.session_state.get('user_id') is not None
    
    def get_current_user(self):
        """Get current authenticated user information"""
        if not self.is_authenticated():
            return None
        
        user_id = st.session_state.get('user_id')
        return self.db.get_user_profile(user_id)
    
    def change_password(self, user_id, old_password, new_password):
        """Change user password"""
        user = self.db.get_user_profile(user_id)
        if not user or user.get('auth_type') != 'password':
            return False, "Password change not available for this account type"
        
        # Verify old password
        if not self.verify_password(old_password, user['password_hash']):
            return False, "Current password is incorrect"
        
        # Validate new password
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters long"
        
        # Update password
        new_hash = self.hash_password(new_password)
        success = self.db.update_user_profile(user_id, {'password_hash': new_hash})
        
        if success:
            return True, "Password updated successfully"
        else:
            return False, "Failed to update password"

def show_login_page():
    """Display the login/signup page"""
    st.title("🌸 Welcome to Hana-chan's Social Media & Chat System")
    
    auth = SimpleAuth()
    
    # Check for existing Google authentication first
    # google_user = auth.google_oauth.get_user_from_token()
    # if google_user:
    #     # User is authenticated with Google, log them in
    #     success, result = auth.login_with_google(google_user)
    #     if success:
    #         st.session_state['authenticated'] = True
    #         st.session_state['user_id'] = result
    #         st.success("✅ Welcome back! You're signed in with Google.")
    #         time.sleep(1)
    #         st.rerun()
    #     else:
    #         st.error(f"❌ {result}")
    #         auth.google_oauth.logout()  # Clear invalid token
    
    # Create tabs for different login methods
    # tab1, tab2, tab3 = st.tabs(["🔐 Login", "✨ Create Account", "🔐 Google Login"])
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Create Account"])
    
    with tab1:
        st.header("Login to Your Account")
        
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="your@email.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Your password")
            
            col1, col2 = st.columns(2)
            with col1:
                login_submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("Forgot Password?", use_container_width=True):
                    st.info("Contact support to reset your password")
        
        if login_submitted:
            success, result = auth.login_with_password(email, password)
            
            if success:
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = result
                st.success("✅ Login successful!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ {result}")
    
    with tab2:
        st.header("Create New Account")
        
        with st.form("signup_form"):
            name = st.text_input("👤 Full Name", placeholder="Your name")
            email = st.text_input("📧 Email", placeholder="your@email.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Choose a strong password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
            
            agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            signup_submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
        
        if signup_submitted:
            if not agree_terms:
                st.error("❌ Please agree to the Terms of Service")
            elif password != confirm_password:
                st.error("❌ Passwords do not match")
            else:
                success, result = auth.create_account(name, email, password)
                
                if success:
                    st.session_state['authenticated'] = True
                    st.session_state['user_id'] = result
                    st.success("✅ Account created successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {result}")
    
    # with tab3:
    #     st.header("Sign in with Google")
        
    #     if not auth.google_oauth.is_configured():
    #         st.warning("🔧 **Google Sign-in Setup Required**")
    #         st.markdown("""
    #         To enable Google sign-in, you need to:
            
    #         1. **Create a Google Cloud Project** at [Google Cloud Console](https://console.cloud.google.com/)
    #         2. **Enable Google+ API**
    #         3. **Create OAuth 2.0 credentials**
    #         4. **Set environment variables:**
    #            ```bash
    #            export GOOGLE_CLIENT_ID="your-client-id"
    #            export GOOGLE_CLIENT_SECRET="your-client-secret"
    #            export GOOGLE_REDIRECT_URI="http://localhost:8501"
    #            export JWT_SECRET_KEY="your-secret-key"
    #            ```
    #         5. **Add authorized redirect URI:** `http://localhost:8501`
            
    #         📖 [Detailed Setup Guide](https://developers.google.com/identity/protocols/oauth2)
    #         """)
    #     else:
    #         # Check for Google OAuth callback
    #         google_user = auth.google_oauth.show_login_button()
    #         if google_user:
    #             # Handle successful Google authentication
    #             success, result = auth.login_with_google(google_user)
    #             if success:
    #                 st.session_state['authenticated'] = True
    #                 st.session_state['user_id'] = result
    #                 st.success("✅ Google sign-in successful!")
    #                 time.sleep(1)
    #                 st.rerun()
    #             else:
    #                 st.error(f"❌ {result}")
    #                 auth.google_oauth.logout()
    
    # App features preview
    st.markdown("---")
    st.markdown("### ✨ What you'll get:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🤖 Personalized AI Chat**
        - Chat with Hana-chan
        - Context-aware responses
        - Conversation history
        """)
    
    with col2:
        st.markdown("""
        **📱 Social Media Analysis**
        - Instagram, Twitter, Threads
        - Profile insights
        - Content analysis
        """)
    
    with col3:
        st.markdown("""
        **🔒 Secure & Private**
        - Your data is protected
        - Private conversations
        - Profile customization
        """) 