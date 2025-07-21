# Facebook Developer App Setup Guide

This guide will walk you through creating a Facebook Developer app for Instagram and Facebook API integration.

## 🎯 Prerequisites

- A Facebook account (personal or business)
- Phone number for verification
- Valid website or app URL (can use localhost for development)

## 📱 Step-by-Step Setup

### Step 1: Access Facebook Developers Console

1. **Go to Facebook Developers**: https://developers.facebook.com/
2. **Click "Get Started"** in the top right corner
3. **Log in** with your Facebook account
4. **Accept Developer Terms** if prompted

### Step 2: Create Your First App

1. **Click "Create App"** button (green button on the dashboard)
2. **Choose App Type**:
   - Select **"Business"** for most use cases
   - This allows both Instagram and Facebook integration
   - Click **"Next"**

### Step 3: App Details

1. **Fill in App Information**:
   ```
   App Name: Your App Name (e.g., "Hana Social Chat")
   App Contact Email: your-email@example.com
   Business Manager Account: (Select existing or create new)
   ```

2. **Click "Create App"**
3. **Complete Security Check** (solve CAPTCHA if required)

### Step 4: App Dashboard Setup

After creating the app, you'll see the App Dashboard with your **App ID**.

1. **Note your App ID**: This will be your `FACEBOOK_APP_ID` or `INSTAGRAM_CLIENT_ID`
2. **Go to App Settings > Basic** (left sidebar)
3. **Add App Secret**: Click "Show" next to App Secret and copy it
   - This will be your `FACEBOOK_APP_SECRET` or `INSTAGRAM_CLIENT_SECRET`

### Step 5: Configure App Settings

In **Settings > Basic**:

1. **App Domain**: Add your domain
   ```
   localhost (for development)
   yourdomain.com (for production)
   ```

2. **Privacy Policy URL**: Add a valid URL
   ```
   For development: http://localhost:8501/privacy
   For production: https://yourdomain.com/privacy
   ```

3. **Terms of Service URL** (optional but recommended):
   ```
   For development: http://localhost:8501/terms
   For production: https://yourdomain.com/terms
   ```

4. **App Icon**: Upload a 1024x1024 px app icon (optional)

5. **Click "Save Changes"**

### Step 6: Add Instagram Product (for Instagram Integration)

1. **In the left sidebar, click "Add Product"**
2. **Find "Instagram"** section
3. **Click "Set Up"** on **"Instagram Basic Display"**
4. **Click "Create New App"** or **"I don't want to connect an Instagram app"**

#### Instagram Basic Display Setup:

1. **Go to Instagram Basic Display > Basic Display**
2. **Add Instagram App**:
   - Click **"Create New App"**
   - Enter Display Name: `Hana Social Chat`
   - Click **"Create App"**

3. **Add OAuth Redirect URIs**:
   ```
   Development: http://localhost:8501/auth/instagram/callback
   Production: https://yourdomain.com/auth/instagram/callback
   ```

4. **Add Deauthorize Callback URL**:
   ```
   Development: http://localhost:8501/auth/instagram/deauth
   Production: https://yourdomain.com/auth/instagram/deauth
   ```

5. **Add Data Deletion Request URL**:
   ```
   Development: http://localhost:8501/auth/instagram/delete
   Production: https://yourdomain.com/auth/instagram/delete
   ```

### Step 7: Add Facebook Login Product (for Facebook Integration)

1. **In the left sidebar, click "Add Product"**
2. **Find "Facebook Login"** section
3. **Click "Set Up"**

#### Facebook Login Setup:

1. **Go to Facebook Login > Settings**
2. **Add OAuth Redirect URIs**:
   ```
   Development: http://localhost:8501/auth/facebook/callback
   Production: https://yourdomain.com/auth/facebook/callback
   ```

3. **Configure Client OAuth Settings**:
   - ✅ **Client OAuth Login**: Yes
   - ✅ **Web OAuth Login**: Yes
   - ✅ **Force Web OAuth Reauthentication**: No
   - ✅ **Use Strict Mode for Redirect URIs**: Yes

### Step 8: App Permissions and Review

#### For Development (No Review Needed):
Your app can access:
- Basic profile information
- Your own Instagram/Facebook posts
- Test users' data

#### For Production (Review Required):
1. **Go to App Review > Permissions and Features**
2. **Request Advanced Permissions**:
   - `instagram_basic`: To read Instagram profile and media
   - `user_posts`: To read Facebook posts
   - `pages_read_engagement`: To read Page posts

3. **Submit for Review**:
   - Provide app description
   - Upload demo video
   - Explain use case for each permission

### Step 9: Test Users (Development)

1. **Go to Roles > Test Users**
2. **Click "Create Test Users"**
3. **Add test Instagram/Facebook accounts**
4. **Use these accounts for development testing**

### Step 10: Get Your Credentials

From **Settings > Basic**, copy these values:

```bash
# For Instagram
INSTAGRAM_CLIENT_ID=your-app-id-here
INSTAGRAM_CLIENT_SECRET=your-app-secret-here

# For Facebook  
FACEBOOK_APP_ID=your-app-id-here
FACEBOOK_APP_SECRET=your-app-secret-here
```

## 🔧 Environment Configuration

Add these to your `.env` file:

```bash
# Instagram API Configuration
INSTAGRAM_CLIENT_ID=1234567890123456
INSTAGRAM_CLIENT_SECRET=abcdef1234567890abcdef1234567890

# Facebook API Configuration  
FACEBOOK_APP_ID=1234567890123456
FACEBOOK_APP_SECRET=abcdef1234567890abcdef1234567890
```

## 🔄 OAuth Flow URLs

Your app will use these OAuth endpoints:

### Instagram OAuth:
```
Authorization URL: https://api.instagram.com/oauth/authorize
Token Exchange URL: https://api.instagram.com/oauth/access_token
```

### Facebook OAuth:
```
Authorization URL: https://www.facebook.com/v18.0/dialog/oauth
Token Exchange URL: https://graph.facebook.com/v18.0/oauth/access_token
```

## 📋 Required Callback URLs

Set these in your app configuration:

```bash
# Instagram Callbacks
http://localhost:8501/auth/instagram/callback
http://localhost:8501/auth/instagram/deauth  
http://localhost:8501/auth/instagram/delete

# Facebook Callbacks
http://localhost:8501/auth/facebook/callback
```

## 🧪 Testing Your Setup

### 1. Test Instagram Connection:
```python
# In your app, try connecting Instagram
from social_media_auth import SocialMediaManager

manager = SocialMediaManager()
platforms = manager.get_supported_platforms()
print("Available platforms:", platforms)
```

### 2. Test OAuth Flow:
1. Run your Streamlit app: `streamlit run app.py`
2. Navigate to "🔗 Social Media Accounts"
3. Click "Connect Instagram" or "Connect Facebook"
4. Complete OAuth flow
5. Check if posts are fetched successfully

## 🚨 Common Issues & Solutions

### Issue 1: "Invalid OAuth redirect URI"
**Solution**: Ensure redirect URIs in Facebook app settings match exactly:
```
✅ Correct: http://localhost:8501/auth/instagram/callback
❌ Wrong: http://localhost:8501/auth/instagram/callback/
❌ Wrong: https://localhost:8501/auth/instagram/callback
```

### Issue 2: "App Not Live"
**Solution**: 
- For development: Use test users only
- For production: Submit app for review

### Issue 3: "Invalid App Secret"
**Solution**: 
- Regenerate app secret in Settings > Basic
- Update your `.env` file immediately
- Restart your application

### Issue 4: "Permissions Not Granted"
**Solution**:
- Check required permissions in App Review
- For Instagram: `instagram_basic` permission
- For Facebook: `user_posts`, `public_profile` permissions

## 🔒 Security Best Practices

### 1. Protect Your App Secret:
```bash
# ❌ Never commit to version control
FACEBOOK_APP_SECRET=your-real-secret

# ✅ Use environment variables
FACEBOOK_APP_SECRET=${FACEBOOK_APP_SECRET}
```

### 2. Use HTTPS in Production:
```bash
# Development (HTTP OK)
http://localhost:8501/auth/instagram/callback

# Production (HTTPS Required)  
https://yourdomain.com/auth/instagram/callback
```

### 3. Validate Redirect URIs:
- Only add necessary redirect URIs
- Use exact matches, no wildcards
- Remove unused URIs

### 4. Monitor App Usage:
- Check Analytics tab for API usage
- Monitor for unusual activity
- Set up alerts for quota limits

## 📊 App Analytics & Monitoring

### 1. View Usage Statistics:
- Go to **Analytics > Overview**
- Monitor API calls and user activity
- Check rate limit usage

### 2. Monitor Errors:
- Check **Analytics > Errors**
- Review common error patterns
- Fix issues proactively

### 3. Track Performance:
- Monitor response times
- Check success rates
- Optimize API usage

## 🎯 Next Steps

1. ✅ **App Created**: Facebook Developer app set up
2. ✅ **Credentials Obtained**: App ID and Secret copied
3. ✅ **Products Added**: Instagram Basic Display and/or Facebook Login
4. ✅ **Callbacks Configured**: OAuth redirect URIs set
5. 🔄 **Test Integration**: Connect accounts in your app
6. 🚀 **Deploy**: Submit for review when ready for production

## 📞 Support Resources

- **Facebook Developers Documentation**: https://developers.facebook.com/docs/
- **Instagram Basic Display API**: https://developers.facebook.com/docs/instagram-basic-display-api
- **Facebook Login Documentation**: https://developers.facebook.com/docs/facebook-login/
- **Developer Support**: https://developers.facebook.com/support/

---

Your Facebook Developer app is now ready to integrate with your social media authentication system! 🎉 