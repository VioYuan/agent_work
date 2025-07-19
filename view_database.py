#!/usr/bin/env python3
"""
Database Content Viewer for Hana-chan Social Media & Chat System
Usage: python view_database.py
"""

import sqlite3
import json
from datetime import datetime
import sys

class DatabaseViewer:
    def __init__(self, db_path="chatbot.db"):
        self.db_path = db_path
    
    def print_separator(self, title=""):
        print("=" * 80)
        if title:
            print(f" {title} ".center(80, "="))
        print("=" * 80)
    
    def view_users(self):
        """Display all users in a readable format"""
        self.print_separator("USERS TABLE")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, email, auth_type, age, interests, 
                       social_links, created_at, last_login
                FROM users ORDER BY created_at DESC
            ''')
            
            users = cursor.fetchall()
            
            print(f"Total Users: {len(users)}")
            print()
            
            for user in users:
                user_id, name, email, auth_type, age, interests, social_links, created_at, last_login = user
                
                print(f"👤 User ID: {user_id}")
                print(f"   Name: {name}")
                print(f"   Email: {email or 'Not provided'}")
                print(f"   Auth Type: {auth_type or 'password'}")
                print(f"   Age: {age or 'Not specified'}")
                print(f"   Interests: {interests or 'Not specified'}")
                
                # Parse social links
                try:
                    if social_links:
                        links = json.loads(social_links)
                        if links:
                            print(f"   Social Links: {len(links)} link(s)")
                            for i, link in enumerate(links, 1):
                                print(f"     {i}. {link}")
                        else:
                            print(f"   Social Links: None")
                    else:
                        print(f"   Social Links: None")
                except:
                    print(f"   Social Links: Error parsing")
                
                print(f"   Created: {created_at}")
                print(f"   Last Login: {last_login or 'Never'}")
                print("-" * 60)
    
    def view_admins(self):
        """Display all admin users"""
        self.print_separator("ADMIN USERS TABLE")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, email, added_by, created_at, is_active
                FROM admin_users ORDER BY created_at DESC
            ''')
            
            admins = cursor.fetchall()
            
            print(f"Total Admins: {len(admins)}")
            print()
            
            for admin in admins:
                admin_id, email, added_by, created_at, is_active = admin
                status = "🟢 Active" if is_active else "🔴 Inactive"
                
                print(f"⚙️  Admin ID: {admin_id}")
                print(f"   Email: {email}")
                print(f"   Status: {status}")
                print(f"   Added by: {added_by}")
                print(f"   Created: {created_at}")
                print("-" * 40)
    
    def view_conversations(self, limit=10):
        """Display recent conversations"""
        self.print_separator(f"RECENT CONVERSATIONS (Last {limit})")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.id, c.user_id, u.name, c.message, c.response, 
                       c.satisfaction_score, c.timestamp
                FROM conversations c
                LEFT JOIN users u ON c.user_id = u.id
                ORDER BY c.timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            conversations = cursor.fetchall()
            
            print(f"Total Conversations in DB: {self.get_conversation_count()}")
            print(f"Showing last {len(conversations)} conversations:")
            print()
            
            for conv in conversations:
                conv_id, user_id, user_name, message, response, satisfaction, timestamp = conv
                
                print(f"💬 Conversation ID: {conv_id}")
                print(f"   User: {user_name or f'ID {user_id}'} (ID: {user_id})")
                print(f"   Time: {timestamp}")
                print(f"   User Message: {message[:100]}{'...' if len(message) > 100 else ''}")
                print(f"   AI Response: {response[:100]}{'...' if len(response) > 100 else ''}")
                print(f"   Satisfaction: {satisfaction or 'Not rated'}")
                print("-" * 60)
    
    def get_conversation_count(self):
        """Get total conversation count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM conversations')
            return cursor.fetchone()[0]
    
    def view_statistics(self):
        """Display database statistics"""
        self.print_separator("DATABASE STATISTICS")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # User stats
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE auth_type = "password"')
            password_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE auth_type = "google"')
            google_users = cursor.fetchone()[0]
            
            # Admin stats
            cursor.execute('SELECT COUNT(*) FROM admin_users WHERE is_active = 1')
            active_admins = cursor.fetchone()[0]
            
            # Conversation stats
            cursor.execute('SELECT COUNT(*) FROM conversations')
            total_conversations = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT AVG(conversations_per_user) FROM (
                    SELECT COUNT(*) as conversations_per_user 
                    FROM conversations 
                    GROUP BY user_id
                )
            ''')
            avg_conversations = cursor.fetchone()[0] or 0
            
            print(f"👥 Users:")
            print(f"   Total Users: {total_users}")
            print(f"   Password Users: {password_users}")
            print(f"   Google Users: {google_users}")
            print()
            print(f"⚙️  Admins:")
            print(f"   Active Admins: {active_admins}")
            print()
            print(f"💬 Conversations:")
            print(f"   Total Conversations: {total_conversations}")
            print(f"   Average per User: {avg_conversations:.1f}")
            print()
            print(f"📊 Database File: {self.db_path}")
    
    def search_user(self, search_term):
        """Search for users by name or email"""
        self.print_separator(f"SEARCH RESULTS FOR: '{search_term}'")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, email, auth_type, created_at
                FROM users 
                WHERE name LIKE ? OR email LIKE ?
                ORDER BY created_at DESC
            ''', (f'%{search_term}%', f'%{search_term}%'))
            
            users = cursor.fetchall()
            
            if users:
                print(f"Found {len(users)} user(s):")
                print()
                for user in users:
                    user_id, name, email, auth_type, created_at = user
                    print(f"👤 {name} (ID: {user_id})")
                    print(f"   Email: {email or 'Not provided'}")
                    print(f"   Type: {auth_type}")
                    print(f"   Created: {created_at}")
                    print("-" * 40)
            else:
                print("No users found matching that search term.")

def main():
    """Main function with interactive menu"""
    viewer = DatabaseViewer()
    
    print("🌸 Hana-chan Database Viewer")
    print("=" * 40)
    
    while True:
        print("\nChoose an option:")
        print("1. View all users")
        print("2. View admin users") 
        print("3. View recent conversations")
        print("4. View database statistics")
        print("5. Search users")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        try:
            if choice == '1':
                viewer.view_users()
            elif choice == '2':
                viewer.view_admins()
            elif choice == '3':
                limit = input("How many conversations to show? (default 10): ").strip()
                limit = int(limit) if limit.isdigit() else 10
                viewer.view_conversations(limit)
            elif choice == '4':
                viewer.view_statistics()
            elif choice == '5':
                search_term = input("Enter search term (name or email): ").strip()
                if search_term:
                    viewer.search_user(search_term)
            elif choice == '6':
                print("Goodbye! 👋")
                break
            else:
                print("Invalid choice. Please try again.")
        except Exception as e:
            print(f"Error: {e}")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 