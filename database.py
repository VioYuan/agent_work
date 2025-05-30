import sqlite3
import json
from typing import Dict, Any, Optional
import os

class Database:
    def __init__(self, db_path: str = "chatbot.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER,
                    interests TEXT,
                    social_links TEXT,
                    user_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create conversations table
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
            
            conn.commit()

    def save_user_profile(self, profile: Dict[str, Any]) -> int:
        """Save user profile and return user_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Convert social_links and user_context to JSON strings
            social_links_json = json.dumps(profile.get('social_links', []))
            user_context_json = json.dumps(profile.get('user_context', {}))
            
            cursor.execute('''
                INSERT INTO users (name, age, interests, social_links, user_context)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                profile.get('name'),
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
                SELECT name, age, interests, social_links, user_context
                FROM users
                WHERE id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                # Handle None values safely for JSON fields
                social_links = row[3]
                if social_links is not None:
                    try:
                        social_links = json.loads(social_links)
                    except (json.JSONDecodeError, TypeError):
                        social_links = []
                else:
                    social_links = []
                
                user_context = row[4]
                if user_context is not None:
                    try:
                        user_context = json.loads(user_context)
                    except (json.JSONDecodeError, TypeError):
                        user_context = {}
                else:
                    user_context = {}
                
                return {
                    'id': user_id,
                    'name': row[0],
                    'age': row[1],
                    'interests': row[2],
                    'social_links': social_links,
                    'user_context': user_context
                }
            return None

    def save_conversation(self, user_id: int, message: str, response: str, satisfaction_score: float):
        """Save a conversation exchange."""
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
        """Retrieve recent conversations for a user."""
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
        """Retrieve all users."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name, age FROM users')
            return [{'id': row[0], 'name': row[1], 'age': row[2]} for row in cursor.fetchall()]

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