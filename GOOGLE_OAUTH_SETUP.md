# Google OAuth Setup Guide

This guide will help you set up Google OAuth authentication for the Hana-chan Social Media & Chat System.

## Prerequisites

- A Google account
- Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "Hana Chan App")
5. Click "Create"

## Step 2: Enable Required APIs

1. In your Google Cloud project, go to the [API Library](https://console.cloud.google.com/apis/library)
2. Search for and enable the following APIs:
   - **Google+ API** (or Google People API)
   - **Google Identity Services API**

## Step 3: Create OAuth 2.0 Credentials

1. Go to [Credentials page](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen first:
   - Choose "External" for user type
   - Fill in required fields:
     - App name: "Hana-chan Chat System"
     - User support email: your email
     - Developer contact information: your email
   - Add scopes: `../auth/userinfo.email`, `../auth/userinfo.profile`, `openid`
   - Add test users (your email) if in testing mode

4. Create OAuth client ID:
   - Application type: **Web application**
   - Name: "Hana-chan Web Client"
   - Authorized redirect URIs: 
     - `http://localhost:8501` (for local development)
     - Add your production URL if deploying

5. Click "Create"
6. **Important**: Copy the Client ID and Client Secret - you'll need these!

## Step 4: Configure Environment Variables

Create or update your `.env` file with the following:

```bash
# OpenAI API (existing)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8501
JWT_SECRET_KEY=your-strong-random-secret-key
```

### Generating a JWT Secret Key

You can generate a secure JWT secret key using Python:

```bash
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

## Step 5: Test the Integration

1. Restart your Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Go to the "Google Login" tab
3. You should see a blue "Sign in with Google" button
4. Click it to test the OAuth flow

## Security Considerations

### For Production Deployment

1. **Update redirect URIs**: Add your production domain to authorized redirect URIs
2. **Use HTTPS**: Ensure your production app uses HTTPS
3. **Secure environment variables**: Use proper secret management
4. **Review OAuth consent screen**: Make sure it's production-ready

### OAuth Consent Screen Status

- **Testing**: Only test users can sign in
- **In production**: Anyone with a Google account can sign in (requires verification)

## Troubleshooting

### Common Issues

1. **"Error 400: redirect_uri_mismatch"**
   - Make sure `GOOGLE_REDIRECT_URI` matches exactly what's in Google Cloud Console
   - Don't include trailing slashes

2. **"Access blocked: This app's request is invalid"**
   - Check that your OAuth consent screen is properly configured
   - Ensure required scopes are added

3. **"Error 401: unauthorized_client"**
   - Verify your Client ID and Client Secret are correct
   - Check that the OAuth client type is "Web application"

4. **Cookie/Token Issues**
   - Clear browser cookies and try again
   - Make sure `JWT_SECRET_KEY` is set and consistent

### Getting Help

- Check the browser's developer console for error messages
- Verify all environment variables are set correctly
- Ensure APIs are enabled in Google Cloud Console

## Features After Setup

Once configured, users can:

✅ **Sign in with Google** - One-click authentication
✅ **Separate from email/password** - No conflicts between auth methods  
✅ **Persistent login** - Stay logged in across browser sessions
✅ **Secure token management** - JWT tokens with expiration
✅ **Profile picture sync** - Google profile pictures automatically imported

## Example Environment File

```bash
# Copy this template to your .env file and fill in your values

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Google OAuth Configuration  
GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8501
JWT_SECRET_KEY=your-32-character-random-string-here
```

That's it! Your Google OAuth integration should now be working. Users can choose between creating an account with email/password or signing in with their Google account. 