#!/usr/bin/env python3
# Added: 2025-05-13T17:40:23-04:00 - Script to initialize the model cache database

import os
import sqlite3
import time
import traceback

def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

def init_db():
    """Initialize the database schema"""
    try:
        # Get the database path
        module_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(module_dir, 'model_cache.db')
        log_debug(f"Initializing model cache database at: {db_path}")
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create models table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            model_type TEXT,
            filename TEXT,
            size_bytes INTEGER,
            last_used TIMESTAMP,
            use_count INTEGER DEFAULT 0,
            download_date TIMESTAMP,
            protected BOOLEAN DEFAULT 0
        )
        ''')
        
        # Create settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        # Initialize default settings if they don't exist
        cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        ''', ('min_free_space_gb', '10'))
        
        conn.commit()
        conn.close()
        log_debug("Database initialization complete")
        return True
    except Exception as e:
        log_debug(f"Error initializing database: {str(e)}")
        return False

if __name__ == "__main__":
    # Run as a standalone script
    success = init_db()
    if success:
        print("Database initialized successfully.")
    else:
        print("Failed to initialize database.")
