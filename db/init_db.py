#!/usr/bin/env python3
# Added: 2025-05-13T17:40:23-04:00 - Script to initialize the model cache database
# Updated: 2025-05-16T08:45:12-04:00 - Added is_ignore field and static-models.json initialization

import os
import sqlite3
import time
import traceback
import json
import shutil
from datetime import datetime

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
        
        # Check if database already exists
        db_exists = os.path.exists(db_path)
        log_debug(f"Checking for model cache database at: {db_path}")
        log_debug(f"Database exists: {db_exists}")
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create models table with is_ignore field
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
            protected BOOLEAN DEFAULT 0,
            is_ignore BOOLEAN DEFAULT 0
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
        
        # If this is a new database, initialize with static models
        if not db_exists:
            log_debug("New database detected. Initializing with static models...")
            initialize_static_models(conn, cursor)
        
        conn.commit()
        conn.close()
        log_debug("Database initialization complete")
        return True
    except Exception as e:
        log_debug(f"Error initializing database: {str(e)}")
        log_debug(traceback.format_exc())
        return False

def initialize_static_models(conn, cursor):
    """Initialize the database with static models from static-models.json"""
    try:
        # Get static_models.json path from environment variable
        static_models_path = os.environ.get('STATIC_MODELS', '/workspace/shared/static-models.json')
        log_debug(f"Looking for static models file at: {static_models_path}")
        
        if not os.path.exists(static_models_path):
            log_debug(f"Static models file not found at {static_models_path}")
            return False
        
        # Load static-models.json
        with open(static_models_path, 'r') as f:
            static_models_data = json.load(f)
            log_debug(f"Loaded static models file with {len(static_models_data.get('no_index', []))} no_index entries")
        
        # Get current time for all records
        current_time = datetime.now().isoformat()
        
        # Process no_index entries
        for model in static_models_data.get('no_index', []):
            path = model.get('path', '')
            if not path:
                continue
                
            # Extract model type and filename
            path_parts = path.split('/')
            filename = os.path.basename(path)
            model_type = "unknown"
            
            # Try to determine model type from path
            if "models" in path_parts and path_parts.index("models") + 1 < len(path_parts):
                model_type = path_parts[path_parts.index("models") + 1]
            
            # Get file size if the file exists
            size_bytes = 0
            if os.path.exists(path):
                size_bytes = os.path.getsize(path)
                log_debug(f"Found static model at {path} with size {size_bytes} bytes")
            else:
                log_debug(f"Static model path does not exist: {path}")
            
            # Insert the model with is_ignore=True
            try:
                cursor.execute('''
                INSERT OR IGNORE INTO models 
                (path, model_type, filename, size_bytes, last_used, use_count, download_date, protected, is_ignore)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (path, model_type, filename, size_bytes, current_time, 0, current_time, 1, 1))
                
                if cursor.rowcount > 0:
                    log_debug(f"Added static model to database: {path}")
                else:
                    log_debug(f"Static model already exists in database: {path}")
            except sqlite3.Error as e:
                log_debug(f"Error adding static model {path} to database: {str(e)}")
        
        # Process symlinks entries if they have different paths
        for symlink in static_models_data.get('symlinks', []):
            target = symlink.get('target', '')
            if not target:
                continue
                
            # Construct full path assuming standard ComfyUI structure
            path = f"/workspace/shared/models/{target}"
            
            # Extract model type and filename
            path_parts = path.split('/')
            filename = os.path.basename(path)
            model_type = "unknown"
            
            # Try to determine model type from path
            if "models" in path_parts and path_parts.index("models") + 1 < len(path_parts):
                model_type = path_parts[path_parts.index("models") + 1]
            
            # Get file size if the file exists
            size_bytes = 0
            if os.path.exists(path):
                size_bytes = os.path.getsize(path)
                log_debug(f"Found symlink model at {path} with size {size_bytes} bytes")
            else:
                log_debug(f"Symlink model path does not exist: {path}")
            
            # Insert the model with is_ignore=True
            try:
                cursor.execute('''
                INSERT OR IGNORE INTO models 
                (path, model_type, filename, size_bytes, last_used, use_count, download_date, protected, is_ignore)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (path, model_type, filename, size_bytes, current_time, 0, current_time, 1, 1))
                
                if cursor.rowcount > 0:
                    log_debug(f"Added symlink model to database: {path}")
                else:
                    log_debug(f"Symlink model already exists in database: {path}")
            except sqlite3.Error as e:
                log_debug(f"Error adding symlink model {path} to database: {str(e)}")
        
        log_debug("Static models initialization complete")
        return True
    except Exception as e:
        log_debug(f"Error initializing static models: {str(e)}")
        log_debug(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Run as a standalone script
    success = init_db()
    if success:
        print("Database initialized successfully.")
    else:
        print("Failed to initialize database.")
