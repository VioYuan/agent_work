import sqlite3
import json
from typing import Dict, Any, Optional, List
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path: str = "chatbot.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create users table with both password and Google OAuth support
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    google_id TEXT,
                    picture TEXT,
                    auth_type TEXT DEFAULT 'password',
                    age INTEGER,
                    interests TEXT,
                    social_links TEXT,
                    user_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Handle schema migration - add missing columns to existing tables
            self._migrate_schema(cursor)
            
            # Create conversations table with user-specific access
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    quality_metrics TEXT,
                    satisfaction_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create sentiment analysis table for daily tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sentiment_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    conversation_id INTEGER,
                    sentiment_score REAL,
                    emotions_detected TEXT,
                    engagement_level REAL,
                    mood_progression TEXT,
                    main_topics TEXT,
                    emotional_summary TEXT,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date DATE,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            ''')
            
            # Create social media accounts table for OAuth tokens
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS social_media_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    platform TEXT NOT NULL,
                    platform_user_id TEXT,
                    platform_username TEXT,
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expires_at TIMESTAMP,
                    account_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, platform)
                )
            ''')
            
            # Add indexes for better performance (only after ensuring columns exist)
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_google_id ON users (google_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentiment_user_date ON sentiment_analysis (user_id, date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_social_media_user_platform ON social_media_accounts (user_id, platform)')
            except sqlite3.OperationalError:
                # If indexes fail, continue - they'll be created after migration
                pass
            
            conn.commit()

    def _migrate_schema(self, cursor):
        """Handle database schema migrations for existing tables."""
        try:
            # Get current column names for users table
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            # List of columns that should exist in the users table
            required_columns = [
                ('email', 'TEXT UNIQUE'),
                ('password_hash', 'TEXT'),
                ('google_id', 'TEXT'),
                ('picture', 'TEXT'),
                ('auth_type', 'TEXT DEFAULT "password"'),
                ('occupation', 'TEXT'),
                ('last_login', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]
            
            # Add missing columns
            for column_name, column_definition in required_columns:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_definition}')
                        print(f"Added column: {column_name}")
                    except sqlite3.OperationalError as e:
                        # Column might already exist, skip
                        print(f"Could not add column {column_name}: {e}")
            
            # Now create indexes after ensuring columns exist
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_google_id ON users (google_id)')
            except sqlite3.OperationalError:
                pass
                
        except sqlite3.OperationalError:
            # If migration fails, the table might not exist yet, which is fine
            pass

    def save_user_profile(self, profile: Dict[str, Any]) -> int:
        """Save user profile and return user_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Convert social_links and user_context to JSON strings
            social_links_json = json.dumps(profile.get('social_links', []))
            user_context_json = json.dumps(profile.get('user_context', {}))
            
            # Check if this is updating an existing user or creating new
            google_id = profile.get('google_id')
            email = profile.get('email')
            
            if google_id:
                # Google authentication user
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (name, email, google_id, picture, auth_type, occupation, age, interests, social_links, user_context, last_login)
                    VALUES (?, ?, ?, ?, 'google', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    profile.get('name'),
                    email,
                    google_id,
                    profile.get('picture'),
                    profile.get('occupation'),
                    profile.get('age'),
                    profile.get('interests'),
                    social_links_json,
                    user_context_json
                ))
                
                # Get the user ID
                cursor.execute('SELECT id FROM users WHERE google_id = ?', (google_id,))
                result = cursor.fetchone()
                user_id = result[0] if result else None
            else:
                # Password authentication user
                cursor.execute('''
                    INSERT INTO users 
                    (name, email, password_hash, auth_type, occupation, age, interests, social_links, user_context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile.get('name'),
                    email,
                    profile.get('password_hash'),
                    profile.get('auth_type', 'password'),
                    profile.get('occupation'),
                    profile.get('age'),
                    profile.get('interests'),
                    social_links_json,
                    user_context_json
                ))
                user_id = cursor.lastrowid
            
            conn.commit()
            return user_id

    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user profile by user_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, email, password_hash, google_id, picture, auth_type, occupation, age, interests, social_links, user_context, created_at, last_login
                FROM users
                WHERE id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                # Handle None values safely for JSON fields
                social_links = row[10]  # Updated index
                if social_links is not None:
                    try:
                        social_links = json.loads(social_links)
                    except (json.JSONDecodeError, TypeError):
                        social_links = []
                else:
                    social_links = []
                
                user_context = row[11]  # Updated index
                if user_context is not None:
                    try:
                        user_context = json.loads(user_context)
                    except (json.JSONDecodeError, TypeError):
                        user_context = {}
                else:
                    user_context = {}
                
                return {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'password_hash': row[3],
                    'google_id': row[4],
                    'picture': row[5],
                    'auth_type': row[6],
                    'occupation': row[7],
                    'age': row[8],
                    'interests': row[9],
                    'social_links': social_links,
                    'user_context': user_context,
                    'created_at': row[12],  # Updated index
                    'last_login': row[13]   # Updated index
                }
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user profile by email address."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, email, password_hash, google_id, picture, auth_type, occupation, age, interests, social_links, user_context, created_at, last_login
                FROM users
                WHERE email = ?
            ''', (email,))
            
            row = cursor.fetchone()
            if row:
                # Handle None values safely for JSON fields
                social_links = row[10]  # Updated index
                if social_links is not None:
                    try:
                        social_links = json.loads(social_links)
                    except (json.JSONDecodeError, TypeError):
                        social_links = []
                else:
                    social_links = []
                
                user_context = row[11]  # Updated index
                if user_context is not None:
                    try:
                        user_context = json.loads(user_context)
                    except (json.JSONDecodeError, TypeError):
                        user_context = {}
                else:
                    user_context = {}
                
                return {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'password_hash': row[3],
                    'google_id': row[4],
                    'picture': row[5],
                    'auth_type': row[6],
                    'occupation': row[7],
                    'age': row[8],
                    'interests': row[9],
                    'social_links': social_links,
                    'user_context': user_context,
                    'created_at': row[12],
                    'last_login': row[13]
                }
            return None

    def get_user_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user profile by Google ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, email, google_id, picture, verified_email, age, interests, social_links, user_context, created_at, last_login
                FROM users
                WHERE google_id = ?
            ''', (google_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'google_id': row[3],
                    'picture': row[4],
                    'verified_email': row[5],
                    'age': row[6],
                    'interests': row[7],
                    'social_links': json.loads(row[8]) if row[8] else [],
                    'user_context': json.loads(row[9]) if row[9] else {},
                    'created_at': row[10],
                    'last_login': row[11]
                }
            return None

    def update_user_login(self, user_id: int):
        """Update the last login timestamp for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user_id,))
            conn.commit()

    def save_conversation(self, user_id: int, message: str, response: str, satisfaction_score: float) -> int:
        """Save a conversation exchange for a specific user and return conversation ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversations 
                (user_id, message, response, satisfaction_score)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                message,
                response,
                satisfaction_score
            ))
            
            conversation_id = cursor.lastrowid
            conn.commit()
            return conversation_id

    def get_user_conversations(self, user_id: int, limit: int = 10) -> list:
        """Retrieve recent conversations for a specific user only."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get the most recent conversations first, then reverse to show oldest first
            cursor.execute('''
                SELECT message, response, quality_metrics, satisfaction_score, timestamp
                FROM (
                    SELECT message, response, quality_metrics, satisfaction_score, timestamp
                    FROM conversations
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
                ORDER BY timestamp ASC
            ''', (user_id, limit))
            
            conversations = []
            for row in cursor.fetchall():
                # Handle None quality_metrics safely
                quality_metrics = row[2]
                if quality_metrics is not None:
                    try:
                        quality_metrics = json.loads(quality_metrics)
                    except (json.JSONDecodeError, TypeError):
                        quality_metrics = {}
                else:
                    quality_metrics = {}
                
                conversations.append({
                    'message': row[0],
                    'response': row[1],
                    'quality_metrics': quality_metrics,
                    'satisfaction_score': row[3],
                    'timestamp': row[4]
                })
            return conversations

    def get_user_conversations_by_session(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve conversations grouped by login session with aggregate scores."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, get session metadata
                cursor.execute('''
                    SELECT DATE(timestamp) as session_date,
                           COUNT(*) as conversation_count,
                           AVG(satisfaction_score) as avg_satisfaction,
                           MIN(timestamp) as session_start,
                           MAX(timestamp) as session_end
                    FROM conversations
                    WHERE user_id = ?
                    GROUP BY DATE(timestamp)
                    ORDER BY session_date DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                sessions = []
                for row in cursor.fetchall():
                    session_date = row[0]
                    
                    # Get individual conversations for this session in chronological order
                    cursor.execute('''
                        SELECT message, response, timestamp
                        FROM conversations
                        WHERE user_id = ? AND DATE(timestamp) = ?
                        ORDER BY timestamp ASC
                    ''', (user_id, session_date))
                    
                    # Create conversation pairs in correct order
                    conversation_pairs = []
                    for conv_row in cursor.fetchall():
                        conversation_pairs.append({
                            'message': conv_row[0].strip(),
                            'response': conv_row[1].strip(),
                            'timestamp': conv_row[2]
                        })
                    
                    # Calculate session metrics
                    total_chars = sum(len(msg['message']) + len(msg['response']) for msg in conversation_pairs)
                    
                    sessions.append({
                        'session_date': session_date,
                        'conversation_count': row[1],
                        'avg_satisfaction': round(row[2], 2) if row[2] else 0.0,
                        'conversation_pairs': conversation_pairs,
                        'session_start': row[3],
                        'session_end': row[4],
                        'total_characters': total_chars,
                        'is_long_session': len(conversation_pairs) > 5 or total_chars > 2000
                    })
                
                return sessions
        except Exception as e:
            print(f"Error getting user conversations by session: {str(e)}")
            return []

    def get_all_users(self) -> list:
        """Retrieve all users (admin function)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name, email, google_id, age, interests, social_links, user_context, created_at, last_login FROM users')
            users = []
            for row in cursor.fetchall():
                # Handle None values safely for JSON fields
                social_links = row[6]
                if social_links is not None:
                    try:
                        social_links = json.loads(social_links)
                    except (json.JSONDecodeError, TypeError):
                        social_links = []
                else:
                    social_links = []
                
                user_context = row[7]
                if user_context is not None:
                    try:
                        user_context = json.loads(user_context)
                    except (json.JSONDecodeError, TypeError):
                        user_context = {}
                else:
                    user_context = {}
                
                users.append({
                    'id': row[0], 
                    'name': row[1], 
                    'email': row[2],
                    'google_id': row[3],
                    'age': row[4],
                    'interests': row[5],
                    'social_links': social_links,
                    'user_context': user_context,
                    'created_at': row[8],
                    'last_login': row[9]
                })
            return users

    def delete_user_profile(self, user_id: int) -> bool:
        """Delete a user profile and associated conversations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First delete all conversations associated with the user
                cursor.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
                
                # Then delete the user profile
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user profile: {str(e)}")
            return False

    def delete_user(self, user_id: int) -> bool:
        """Delete a user (alias for delete_user_profile)."""
        return self.delete_user_profile(user_id)

    def get_user_conversation_count(self, user_id: int) -> int:
        """Get total conversation count for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM conversations WHERE user_id = ?', (user_id,))
            return cursor.fetchone()[0]

    def update_user_profile(self, user_id: int, profile_updates: Dict[str, Any]) -> bool:
        """Update specific fields in a user profile."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                update_fields = []
                values = []
                
                for field, value in profile_updates.items():
                    if field in ['social_links', 'user_context']:
                        # Convert to JSON for storage
                        value = json.dumps(value)
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                
                if update_fields:
                    values.append(user_id)
                    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
                    cursor.execute(query, values)
                    conn.commit()
                
            return True
        except Exception as e:
            print(f"Error updating user profile: {str(e)}")
            return False

    def save_sentiment_analysis(self, user_id: int, conversation_id: int, sentiment_data: Dict[str, Any]) -> bool:
        """Save sentiment analysis data for a conversation."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO sentiment_analysis 
                    (user_id, conversation_id, sentiment_score, emotions_detected, engagement_level, 
                     mood_progression, main_topics, emotional_summary, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    conversation_id,
                    sentiment_data.get('sentiment_score', 0.5),
                    json.dumps(sentiment_data.get('emotions_detected', [])),
                    sentiment_data.get('engagement_level', 0.5),
                    sentiment_data.get('mood_progression', ''),
                    json.dumps(sentiment_data.get('main_topics', [])),
                    sentiment_data.get('emotional_summary', ''),
                    sentiment_data.get('date', datetime.now().date().isoformat())
                ))
                
                conn.commit()
            return True
        except Exception as e:
            print(f"Error saving sentiment analysis: {str(e)}")
            return False

    def get_daily_sentiment_summary(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily sentiment summaries for the last N days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT date, 
                           AVG(sentiment_score) as avg_sentiment,
                           AVG(engagement_level) as avg_engagement,
                           COUNT(*) as conversation_count,
                           GROUP_CONCAT(emotional_summary, ' | ') as daily_summary
                    FROM sentiment_analysis 
                    WHERE user_id = ? AND date >= date('now', '-{} days')
                    GROUP BY date 
                    ORDER BY date DESC
                '''.format(days), (user_id,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'date': row[0],
                        'avg_sentiment': round(row[1], 2) if row[1] else 0.5,
                        'avg_engagement': round(row[2], 2) if row[2] else 0.5,
                        'conversation_count': row[3],
                        'daily_summary': row[4] or 'No conversations today'
                    })
                
                return results
        except Exception as e:
            print(f"Error getting daily sentiment summary: {str(e)}")
            return []

    def get_recent_sentiment_analysis(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent sentiment analyses for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT s.sentiment_score, s.emotions_detected, s.engagement_level,
                           s.mood_progression, s.main_topics, s.emotional_summary,
                           s.analysis_date, c.message, c.response
                    FROM sentiment_analysis s
                    JOIN conversations c ON s.conversation_id = c.id
                    WHERE s.user_id = ?
                    ORDER BY s.analysis_date DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                results = []
                for row in cursor.fetchall():
                    emotions = row[1]
                    topics = row[4]
                    
                    # Parse JSON fields safely
                    try:
                        emotions = json.loads(emotions) if emotions else []
                        topics = json.loads(topics) if topics else []
                    except:
                        emotions = []
                        topics = []
                    
                    results.append({
                        'sentiment_score': row[0],
                        'emotions_detected': emotions,
                        'engagement_level': row[2],
                        'mood_progression': row[3],
                        'main_topics': topics,
                        'emotional_summary': row[5],
                        'analysis_date': row[6],
                        'user_message': row[7],
                        'ai_response': row[8]
                    })
                
                return results
        except Exception as e:
            print(f"Error getting recent sentiment analysis: {str(e)}")
            return []

    def save_social_media_account(self, user_id: int, platform: str, account_data: Dict[str, Any]) -> bool:
        """Save or update social media account authentication data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate token expiration if provided
                token_expires_at = None
                if 'expires_in' in account_data:
                    expires_in = account_data['expires_in']
                    token_expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO social_media_accounts 
                    (user_id, platform, platform_user_id, platform_username, access_token, 
                     refresh_token, token_expires_at, account_data, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    user_id,
                    platform,
                    account_data.get('user_id', account_data.get('id')),
                    account_data.get('username', account_data.get('name')),
                    account_data.get('access_token'),
                    account_data.get('refresh_token'),
                    token_expires_at,
                    json.dumps(account_data)
                ))
                
                conn.commit()
            return True
        except Exception as e:
            print(f"Error saving social media account: {str(e)}")
            return False

    def get_social_media_accounts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all connected social media accounts for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT platform, platform_user_id, platform_username, access_token,
                           refresh_token, token_expires_at, account_data, created_at, 
                           updated_at, is_active
                    FROM social_media_accounts
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                accounts = []
                for row in cursor.fetchall():
                    # Parse account data safely
                    account_data = {}
                    try:
                        account_data = json.loads(row[6]) if row[6] else {}
                    except:
                        account_data = {}
                    
                    # Check if token is expired
                    is_expired = False
                    if row[5]:  # token_expires_at
                        try:
                            expires_at = datetime.fromisoformat(row[5])
                            is_expired = datetime.now() > expires_at
                        except:
                            is_expired = False
                    
                    accounts.append({
                        'platform': row[0],
                        'platform_user_id': row[1],
                        'platform_username': row[2],
                        'access_token': row[3],
                        'refresh_token': row[4],
                        'token_expires_at': row[5],
                        'account_data': account_data,
                        'created_at': row[7],
                        'updated_at': row[8],
                        'is_active': bool(row[9]),
                        'is_expired': is_expired
                    })
                
                return accounts
        except Exception as e:
            print(f"Error getting social media accounts: {str(e)}")
            return []

    def get_social_media_account(self, user_id: int, platform: str) -> Optional[Dict[str, Any]]:
        """Get a specific social media account for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT platform, platform_user_id, platform_username, access_token,
                           refresh_token, token_expires_at, account_data, created_at, 
                           updated_at, is_active
                    FROM social_media_accounts
                    WHERE user_id = ? AND platform = ? AND is_active = 1
                ''', (user_id, platform))
                
                row = cursor.fetchone()
                if row:
                    # Parse account data safely
                    account_data = {}
                    try:
                        account_data = json.loads(row[6]) if row[6] else {}
                    except:
                        account_data = {}
                    
                    # Check if token is expired
                    is_expired = False
                    if row[5]:  # token_expires_at
                        try:
                            expires_at = datetime.fromisoformat(row[5])
                            is_expired = datetime.now() > expires_at
                        except:
                            is_expired = False
                    
                    return {
                        'platform': row[0],
                        'platform_user_id': row[1],
                        'platform_username': row[2],
                        'access_token': row[3],
                        'refresh_token': row[4],
                        'token_expires_at': row[5],
                        'account_data': account_data,
                        'created_at': row[7],
                        'updated_at': row[8],
                        'is_active': bool(row[9]),
                        'is_expired': is_expired
                    }
                
                return None
        except Exception as e:
            print(f"Error getting social media account: {str(e)}")
            return None

    def update_social_media_token(self, user_id: int, platform: str, access_token: str, 
                                 refresh_token: str = None, expires_in: int = None) -> bool:
        """Update social media account tokens."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate token expiration if provided
                token_expires_at = None
                if expires_in:
                    token_expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                
                if refresh_token:
                    cursor.execute('''
                        UPDATE social_media_accounts 
                        SET access_token = ?, refresh_token = ?, token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND platform = ?
                    ''', (access_token, refresh_token, token_expires_at, user_id, platform))
                else:
                    cursor.execute('''
                        UPDATE social_media_accounts 
                        SET access_token = ?, token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND platform = ?
                    ''', (access_token, token_expires_at, user_id, platform))
                
                conn.commit()
            return True
        except Exception as e:
            print(f"Error updating social media token: {str(e)}")
            return False

    def disconnect_social_media_account(self, user_id: int, platform: str) -> bool:
        """Disconnect a social media account by setting it as inactive."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE social_media_accounts 
                    SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND platform = ?
                ''', (user_id, platform))
                
                conn.commit()
            return True
        except Exception as e:
            print(f"Error disconnecting social media account: {str(e)}")
            return False

    def save_social_media_posts(self, user_id: int, platform: str, posts: List[Dict[str, Any]]) -> bool:
        """Save fetched social media posts for analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create a table for social media posts if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS social_media_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        platform TEXT,
                        post_id TEXT,
                        content TEXT,
                        media_url TEXT,
                        post_url TEXT,
                        created_at_platform TIMESTAMP,
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        post_data TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, platform, post_id)
                    )
                ''')
                
                # Insert posts
                for post in posts:
                    cursor.execute('''
                        INSERT OR REPLACE INTO social_media_posts
                        (user_id, platform, post_id, content, media_url, post_url, 
                         created_at_platform, post_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        platform,
                        post.get('id'),
                        post.get('text', ''),
                        post.get('media_url', post.get('full_picture')),
                        post.get('url', post.get('permalink', post.get('permalink_url'))),
                        post.get('created_at', post.get('timestamp', post.get('created_time'))),
                        json.dumps(post)
                    ))
                
                conn.commit()
            return True
        except Exception as e:
            print(f"Error saving social media posts: {str(e)}")
            return False

    def get_social_media_posts(self, user_id: int, platform: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get saved social media posts for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if platform:
                    cursor.execute('''
                        SELECT platform, post_id, content, media_url, post_url,
                               created_at_platform, fetched_at, post_data
                        FROM social_media_posts
                        WHERE user_id = ? AND platform = ?
                        ORDER BY created_at_platform DESC
                        LIMIT ?
                    ''', (user_id, platform, limit))
                else:
                    cursor.execute('''
                        SELECT platform, post_id, content, media_url, post_url,
                               created_at_platform, fetched_at, post_data
                        FROM social_media_posts
                        WHERE user_id = ?
                        ORDER BY created_at_platform DESC
                        LIMIT ?
                    ''', (user_id, limit))
                
                posts = []
                for row in cursor.fetchall():
                    # Parse post data safely
                    post_data = {}
                    try:
                        post_data = json.loads(row[7]) if row[7] else {}
                    except:
                        post_data = {}
                    
                    posts.append({
                        'platform': row[0],
                        'post_id': row[1],
                        'content': row[2],
                        'media_url': row[3],
                        'post_url': row[4],
                        'created_at_platform': row[5],
                        'fetched_at': row[6],
                        'post_data': post_data
                    })
                
                return posts
        except Exception as e:
            print(f"Error getting social media posts: {str(e)}")
            return [] 