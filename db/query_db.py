#!/usr/bin/env python3
# Added: 2025-05-13T17:38:32-04:00 - Script to query the model cache database

import os
import sqlite3
import sys
import time

def main():
    """
    Query the model cache database and display the results
    """
    # Get the database path
    module_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(module_dir, 'model_cache.db')
    
    # Check if the database exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("The database will be created when a model is downloaded or accessed.")
        
        # Create an empty database for demonstration
        print("Creating an empty database for demonstration...")
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
        
        # Initialize default settings
        cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        ''', ('min_free_space_gb', '10'))
        
        conn.commit()
        conn.close()
        print("Empty database created successfully.")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    # Get command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = "models"
    
    # Execute the requested command
    if command == "models":
        # Query all models
        cursor.execute('''
        SELECT id, path, model_type, filename, size_bytes, last_used, use_count, download_date, protected
        FROM models
        ORDER BY last_used DESC
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            print("No models found in the database.")
        else:
            print(f"Found {len(rows)} models:")
            print("-" * 120)
            print(f"{'ID':<5} {'Filename':<30} {'Type':<15} {'Size (MB)':<10} {'Use Count':<10} {'Last Used':<25} {'Downloaded':<25}")
            print(f"{'Path':^120}")
            print("-" * 120)
            
            for row in rows:
                size_mb = row['size_bytes'] / (1024 * 1024) if row['size_bytes'] else 0
                print(f"{row['id']:<5} {row['filename']:<30} {row['model_type']:<15} {size_mb:<10.2f} {row['use_count']:<10} {row['last_used']:<25} {row['download_date']:<25}")
                print(f"Path: {row['path']}")
                print("-" * 120)
    
    elif command == "settings":
        # Query all settings
        cursor.execute('SELECT key, value FROM settings')
        
        rows = cursor.fetchall()
        
        if not rows:
            print("No settings found in the database.")
        else:
            print(f"Found {len(rows)} settings:")
            print("-" * 50)
            print(f"{'Key':<30} {'Value':<20}")
            print("-" * 50)
            
            for row in rows:
                print(f"{row['key']:<30} {row['value']:<20}")
    
    elif command == "lru":
        # Query least recently used models
        cursor.execute('''
        SELECT id, path, model_type, filename, size_bytes, last_used, use_count, download_date, protected
        FROM models
        WHERE protected = 0
        ORDER BY last_used ASC
        LIMIT 10
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            print("No models found in the database.")
        else:
            print(f"Found {len(rows)} least recently used models:")
            print("-" * 120)
            print(f"{'ID':<5} {'Filename':<30} {'Type':<15} {'Size (MB)':<10} {'Use Count':<10} {'Last Used':<25} {'Downloaded':<25}")
            print(f"{'Path':^120}")
            print("-" * 120)
            
            for row in rows:
                size_mb = row['size_bytes'] / (1024 * 1024) if row['size_bytes'] else 0
                print(f"{row['id']:<5} {row['filename']:<30} {row['model_type']:<15} {size_mb:<10.2f} {row['use_count']:<10} {row['last_used']:<25} {row['download_date']:<25}")
                print(f"Path: {row['path']}")
                print("-" * 120)
    
    elif command == "stats":
        # Get statistics about the models
        cursor.execute('SELECT COUNT(*) as count, SUM(size_bytes) as total_size FROM models')
        stats = cursor.fetchone()
        
        if stats and stats['count'] > 0:
            total_size_gb = stats['total_size'] / (1024 * 1024 * 1024) if stats['total_size'] else 0
            print(f"Total models: {stats['count']}")
            print(f"Total size: {total_size_gb:.2f} GB")
            
            # Get model types
            cursor.execute('SELECT model_type, COUNT(*) as count FROM models GROUP BY model_type')
            types = cursor.fetchall()
            
            if types:
                print("\nModel types:")
                for t in types:
                    print(f"  {t['model_type']}: {t['count']} models")
            
            # Get most used models
            cursor.execute('''
            SELECT filename, use_count FROM models 
            ORDER BY use_count DESC LIMIT 5
            ''')
            most_used = cursor.fetchall()
            
            if most_used:
                print("\nMost used models:")
                for m in most_used:
                    print(f"  {m['filename']}: {m['use_count']} uses")
        else:
            print("No models found in the database.")
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: models, settings, lru, stats")
    
    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
