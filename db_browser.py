#!/usr/bin/env python3
"""
Database Browser for Clinic Scheduler
Simple script to view and manage your SQLite database
"""

import sqlite3
import sys
from datetime import datetime

def connect_db():
    """Connect to the database"""
    try:
        conn = sqlite3.connect('clinic_scheduler.db')
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def show_tables(conn):
    """Show all tables in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\nDatabase Tables:")
    print("=" * 50)
    for table in tables:
        print(f"• {table[0]}")
    print()

def show_table_schema(conn, table_name):
    """Show schema for a specific table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    print(f"\nSchema for '{table_name}':")
    print("=" * 50)
    for col in columns:
        print(f"• {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
    print()

def show_table_data(conn, table_name, limit=10):
    """Show data from a specific table"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"\nNo data found in '{table_name}'")
        return
    
    print(f"\nData from '{table_name}' (showing first {limit} rows):")
    print("=" * 80)
    
    # Get column names
    column_names = [description[0] for description in cursor.description]
    
    # Print header
    header = " | ".join(f"{col:15}" for col in column_names)
    print(header)
    print("-" * len(header))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(f"{str(val):15}" for val in row)
        print(row_str)
    print()

def show_user_stats(conn):
    """Show user statistics"""
    cursor = conn.cursor()
    
    # Count users by role
    cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role;")
    role_counts = cursor.fetchall()
    
    print("\nUser Statistics:")
    print("=" * 30)
    for role, count in role_counts:
        print(f"• {role}: {count} users")
    
    # Show recent users
    cursor.execute("SELECT username, role, created_at FROM users ORDER BY created_at DESC LIMIT 5;")
    recent_users = cursor.fetchall()
    
    print(f"\nRecent Users:")
    print("=" * 50)
    for user in recent_users:
        print(f"• {user[0]} ({user[1]}) - {user[2]}")
    print()

def show_schedule_stats(conn):
    """Show schedule statistics"""
    cursor = conn.cursor()
    
    # Count assignments
    cursor.execute("SELECT COUNT(*) FROM schedule_assignments;")
    total_assignments = cursor.fetchone()[0]
    
    # Count assignments with patients
    cursor.execute("SELECT COUNT(*) FROM schedule_assignments WHERE patient_name IS NOT NULL AND patient_name != '';")
    assigned_slots = cursor.fetchone()[0]
    
    # Count empty slots
    empty_slots = total_assignments - assigned_slots
    
    print("\nSchedule Statistics:")
    print("=" * 30)
    print(f"• Total time slots: {total_assignments}")
    print(f"• Assigned slots: {assigned_slots}")
    print(f"• Empty slots: {empty_slots}")
    print(f"• Fill rate: {(assigned_slots/total_assignments*100):.1f}%" if total_assignments > 0 else "• Fill rate: 0%")
    print()

def interactive_mode():
    """Interactive database browser"""
    conn = connect_db()
    if not conn:
        return
    
    print("Clinic Scheduler Database Browser")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Show all tables")
        print("2. Show table schema")
        print("3. Show table data")
        print("4. Show user statistics")
        print("5. Show schedule statistics")
        print("6. Run custom SQL query")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            show_tables(conn)
        elif choice == "2":
            table_name = input("Enter table name: ").strip()
            show_table_schema(conn, table_name)
        elif choice == "3":
            table_name = input("Enter table name: ").strip()
            limit = input("Enter limit (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            show_table_data(conn, table_name, limit)
        elif choice == "4":
            show_user_stats(conn)
        elif choice == "5":
            show_schedule_stats(conn)
        elif choice == "6":
            query = input("Enter SQL query: ").strip()
            try:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                if rows:
                    print(f"\nQuery Results ({len(rows)} rows):")
                    print("=" * 50)
                    for row in rows:
                        print(row)
                else:
                    print("\nNo results found.")
            except sqlite3.Error as e:
                print(f"SQL Error: {e}")
        else:
            print("Invalid choice. Please try again.")
    
    conn.close()
    print("\nGoodbye!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command line mode
        conn = connect_db()
        if conn:
            if sys.argv[1] == "tables":
                show_tables(conn)
            elif sys.argv[1] == "users":
                show_user_stats(conn)
            elif sys.argv[1] == "schedule":
                show_schedule_stats(conn)
            elif sys.argv[1] == "schema":
                if len(sys.argv) > 2:
                    show_table_schema(conn, sys.argv[2])
                else:
                    print("Please specify table name: python db_browser.py schema <table_name>")
            elif sys.argv[1] == "data":
                if len(sys.argv) > 2:
                    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
                    show_table_data(conn, sys.argv[2], limit)
                else:
                    print("Please specify table name: python db_browser.py data <table_name> [limit]")
            conn.close()
    else:
        # Interactive mode
        interactive_mode()
