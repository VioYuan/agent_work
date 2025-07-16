import sqlite3
import json
from typing import Dict, Any, Optional
import os
from datetime import datetime

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
            
            # Add indexes for better performance (only after ensuring columns exist)
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_google_id ON users (google_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id)')
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
                    (name, email, google_id, picture, auth_type, age, interests, social_links, user_context, last_login)
                    VALUES (?, ?, ?, ?, 'google', ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    profile.get('name'),
                    email,
                    google_id,
                    profile.get('picture'),
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
                    (name, email, password_hash, auth_type, age, interests, social_links, user_context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile.get('name'),
                    email,
                    profile.get('password_hash'),
                    profile.get('auth_type', 'password'),
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
                SELECT id, name, email, password_hash, google_id, picture, auth_type, age, interests, social_links, user_context, created_at, last_login
                FROM users
                WHERE id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                # Handle None values safely for JSON fields
                social_links = row[9]
                if social_links is not None:
                    try:
                        social_links = json.loads(social_links)
                    except (json.JSONDecodeError, TypeError):
                        social_links = []
                else:
                    social_links = []
                
                user_context = row[10]
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
                    'age': row[7],
                    'interests': row[8],
                    'social_links': social_links,
                    'user_context': user_context,
                    'created_at': row[11],
                    'last_login': row[12]
                }
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user profile by email address."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, email, password_hash, google_id, picture, auth_type, age, interests, social_links, user_context, created_at, last_login
                FROM users
                WHERE email = ?
            ''', (email,))
            
            row = cursor.fetchone()
            if row:
                # Handle None values safely for JSON fields
                social_links = row[9]
                if social_links is not None:
                    try:
                        social_links = json.loads(social_links)
                    except (json.JSONDecodeError, TypeError):
                        social_links = []
                else:
                    social_links = []
                
                user_context = row[10]
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
                    'age': row[7],
                    'interests': row[8],
                    'social_links': social_links,
                    'user_context': user_context,
                    'created_at': row[11],
                    'last_login': row[12]
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

    def save_conversation(self, user_id: int, message: str, response: str, satisfaction_score: float):
        """Save a conversation exchange for a specific user."""
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
            
            conn.commit()

    def get_user_conversations(self, user_id: int, limit: int = 10) -> list:
        """Retrieve recent conversations for a specific user only."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message, response, quality_metrics, satisfaction_score, timestamp
                FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
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