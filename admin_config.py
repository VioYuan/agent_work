import sqlite3
import os
from typing import List, Optional

class AdminConfig:
    def __init__(self, db_path: str = "chatbot.db"):
        self.db_path = db_path
        self._init_admin_db()
    
    def _init_admin_db(self):
        """Initialize the admin configuration table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create admin_users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    added_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Add default admin if none exist
            cursor.execute('SELECT COUNT(*) FROM admin_users WHERE is_active = 1')
            admin_count = cursor.fetchone()[0]
            
            if admin_count == 0:
                # Add default admin - you can change this to your email
                default_admin = os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
                cursor.execute('''
                    INSERT INTO admin_users (email, added_by)
                    VALUES (?, ?)
                ''', (default_admin, 'system'))
            
            conn.commit()
    
    def is_admin(self, email: str) -> bool:
        """Check if an email belongs to an admin user."""
        if not email:
            return False
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM admin_users 
                WHERE email = ? AND is_active = 1
            ''', (email.lower().strip(),))
            return cursor.fetchone() is not None
    
    def add_admin(self, email: str, added_by: str) -> bool:
        """Add a new admin user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO admin_users (email, added_by, is_active)
                    VALUES (?, ?, 1)
                ''', (email.lower().strip(), added_by))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error adding admin: {e}")
            return False
    
    def remove_admin(self, email: str) -> bool:
        """Remove admin privileges (set inactive)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE admin_users SET is_active = 0 
                    WHERE email = ?
                ''', (email.lower().strip(),))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error removing admin: {e}")
            return False
    
    def get_all_admins(self) -> List[dict]:
        """Get list of all admin users."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT email, added_by, created_at, is_active
                FROM admin_users
                ORDER BY created_at DESC
            ''')
            
            admins = []
            for row in cursor.fetchall():
                admins.append({
                    'email': row[0],
                    'added_by': row[1],
                    'created_at': row[2],
                    'is_active': bool(row[3])
                })
            return admins
    
    def get_active_admins(self) -> List[str]:
        """Get list of active admin emails."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT email FROM admin_users 
                WHERE is_active = 1
            ''')
            return [row[0] for row in cursor.fetchall()] 