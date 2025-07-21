# Social Media API Setup Guide

This guide will help you set up social media API authentication for fetching recent posts from various platforms.

## 🔑 Required API Keys

You'll need to obtain API credentials from each platform you want to integrate:

### 📱 Instagram (Meta/Facebook)
1. Go to [Facebook Developers](https://developers.facebook.com/apps)
2. Create a new app or use existing one
3. Add "Instagram Basic Display" product
4. Set up OAuth redirect URIs: `http://localhost:8501/auth/instagram/callback`
5. Get your:
   - `INSTAGRAM_CLIENT_ID`
   - `INSTAGRAM_CLIENT_SECRET`

**Required permissions:** `user_profile`, `user_media`

### 🐦 Twitter/X
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new project and app
3. Enable OAuth 2.0 with PKCE
4. Set callback URL: `http://localhost:8501/auth/twitter/callback`
5. Get your:
   - `TWITTER_CLIENT_ID`
   - `TWITTER_CLIENT_SECRET`
   - `TWITTER_BEARER_TOKEN` (optional)

**Required scopes:** `tweet.read`, `users.read`, `follows.read`, `offline.access`

### 💼 LinkedIn
1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
2. Create a new app
3. Add "Sign In with LinkedIn" product
4. Set OAuth 2.0 redirect URL: `http://localhost:8501/auth/linkedin/callback`
5. Get your:
   - `LINKEDIN_CLIENT_ID`
   - `LINKEDIN_CLIENT_SECRET`

**Required scopes:** `r_liteprofile`, `r_emailaddress`, `w_member_social`

### 📘 Facebook
1. Go to [Facebook Developers](https://developers.facebook.com/apps)
2. Create a new app or use existing one
3. Add "Facebook Login" product
4. Set OAuth redirect URIs: `http://localhost:8501/auth/facebook/callback`
5. Get your:
   - `FACEBOOK_APP_ID`
   - `FACEBOOK_APP_SECRET`

**Required permissions:** `email`, `public_profile`, `user_posts`, `pages_read_engagement`

## 🔧 Environment Configuration

Create a `.env` file in your project root with the following variables:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Instagram API Configuration
INSTAGRAM_CLIENT_ID=your-instagram-client-id
INSTAGRAM_CLIENT_SECRET=your-instagram-client-secret

# Twitter/X API Configuration
TWITTER_CLIENT_ID=your-twitter-client-id
TWITTER_CLIENT_SECRET=your-twitter-client-secret
TWITTER_BEARER_TOKEN=your-twitter-bearer-token

# LinkedIn API Configuration
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret

# Facebook API Configuration
FACEBOOK_APP_ID=your-facebook-app-id
FACEBOOK_APP_SECRET=your-facebook-app-secret

# Application Configuration
REDIRECT_BASE_URL=http://localhost:8501
```

## 🚀 How It Works

### Authentication Flow
1. **User clicks "Connect [Platform]"** → Redirected to platform's OAuth page
2. **User grants permissions** → Platform redirects back with authorization code
3. **App exchanges code for token** → Stores access token securely in database
4. **Fetch recent posts** → Uses stored token to get user's recent content

### Data Fetched
- **Instagram**: Recent photos/videos with captions, timestamps, engagement
- **Twitter/X**: Recent tweets with metrics, retweets, replies
- **LinkedIn**: Recent posts, profile updates, professional content
- **Facebook**: Recent posts, photos, status updates

### Security Features
- ✅ **Secure token storage** - Tokens encrypted in database
- ✅ **Token expiration handling** - Automatic refresh when possible
- ✅ **User consent** - Users explicitly grant permissions
- ✅ **Rate limiting** - Respects API rate limits
- ✅ **Error handling** - Graceful fallbacks for API failures

## 📊 Features Available

### 🔗 Account Management
- Connect/disconnect social media accounts
- View connected accounts status
- Refresh expired tokens
- Account-specific settings

### 📈 Data Analysis
- Sentiment analysis of recent posts
- Engagement metrics and trends
- Content themes and topics
- Cross-platform insights

### 💬 Chat Integration
- AI analysis of social media content
- Personalized responses based on recent activity
- Social context in conversations
- Content-aware recommendations

## 🔒 Privacy & Security

### Data Protection
- User data never shared with third parties
- Tokens stored encrypted in local database
- Users can disconnect accounts anytime
- No permanent storage of post content (only analysis)

### API Compliance
- Follows platform API terms of service
- Respects rate limits and quotas
- Only requests necessary permissions
- Secure OAuth 2.0 implementation

## 🛠️ Development Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API credentials
```

### 3. Run Application
```bash
streamlit run app.py
```

### 4. Test Social Media Integration
1. Navigate to "🔗 Social Media Accounts" page
2. Click "Connect" for any platform
3. Complete OAuth flow
4. View fetched posts and analysis

## 📝 API Documentation

### Instagram Graph API
- [Basic Display API](https://developers.facebook.com/docs/instagram-basic-display-api)
- [Getting Started](https://developers.facebook.com/docs/instagram-basic-display-api/getting-started)

### Twitter API v2
- [OAuth 2.0 Authorization](https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code)
- [API Reference](https://developer.twitter.com/en/docs/api-reference-index)

### LinkedIn API
- [OAuth 2.0 Flow](https://docs.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)
- [API Documentation](https://docs.microsoft.com/en-us/linkedin/)

### Facebook Graph API
- [OAuth 2.0 Login](https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow)
- [Graph API Reference](https://developers.facebook.com/docs/graph-api)

## 🎯 Next Steps

1. **Get API credentials** from each platform you want to support
2. **Update .env file** with your credentials
3. **Test OAuth flows** with your accounts
4. **Customize data analysis** based on your needs
5. **Add more platforms** as desired

## 💡 Tips & Troubleshooting

### Common Issues
- **Redirect URI mismatch**: Ensure callback URLs match exactly
- **Insufficient permissions**: Check required scopes for each platform
- **Token expiration**: Implement refresh token logic
- **Rate limiting**: Add appropriate delays between API calls

### Best Practices
- Use environment variables for all credentials
- Implement proper error handling
- Respect API rate limits
- Provide clear user consent flows
- Regular token validation and refresh

---

For more detailed implementation examples, see the `social_media_auth.py` module and the social media account management pages in the application. 