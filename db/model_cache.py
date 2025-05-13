import os
import sqlite3
import time
import traceback
from datetime import datetime
import threading

# Added: 2025-05-13T17:10:27-04:00 - Model cache database implementation

def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class ModelCacheDB:
    """
    SQLite database for tracking model usage and managing cache
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelCacheDB, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the database connection"""
        if self._initialized:
            return
            
        # Get the database path
        module_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(module_dir, 'model_cache.db')
        log_debug(f"Model cache database path: {self.db_path}")
        
        # Database should already be initialized by init_db.py
        # Just verify it exists
        if not os.path.exists(self.db_path):
            log_debug(f"Warning: Database file not found at {self.db_path}")
            log_debug("Attempting to initialize database...")
            from .init_db import init_db
            init_db()
        
        self._initialized = True
    
    def register_model(self, path, model_type, size_bytes):
        """
        Register a model in the database when it's downloaded
        
        Args:
            path (str): Full path to the model file
            model_type (str): Type of model (checkpoint, lora, vae, etc.)
            size_bytes (int): Size of the model in bytes
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            log_debug(f"Registering model: {path}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get just the filename from the path
            filename = os.path.basename(path)
            
            # Check if the model already exists
            cursor.execute('SELECT id FROM models WHERE path = ?', (path,))
            existing = cursor.fetchone()
            
            current_time = datetime.now().isoformat()
            
            if existing:
                # Update existing model
                cursor.execute('''
                UPDATE models 
                SET size_bytes = ?, last_used = ?, use_count = use_count + 1
                WHERE path = ?
                ''', (size_bytes, current_time, path))
                log_debug(f"Updated existing model: {path}")
            else:
                # Insert new model
                cursor.execute('''
                INSERT INTO models (path, model_type, filename, size_bytes, last_used, use_count, download_date, protected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (path, model_type, filename, size_bytes, current_time, 1, current_time, 0))
                log_debug(f"Inserted new model: {path}")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log_debug(f"Error registering model: {str(e)}")
            return False
    
    def update_model_usage(self, path):
        """
        Update the last_used timestamp and increment use_count for a model
        
        Args:
            path (str): Full path to the model file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            log_debug(f"Updating model usage: {path}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_time = datetime.now().isoformat()
            
            # Get current use count for logging
            cursor.execute('SELECT use_count FROM models WHERE path = ?', (path,))
            row = cursor.fetchone()
            old_count = row[0] if row else 0
            
            # Update the model usage
            cursor.execute('''
            UPDATE models 
            SET last_used = ?, use_count = use_count + 1
            WHERE path = ?
            ''', (current_time, path))
            
            # If rows were affected, log the update
            if cursor.rowcount > 0:
                log_debug(f"Updated model usage in database: {path}")
                log_debug(f"Incremented use_count from {old_count} to {old_count + 1}")
                log_debug(f"Updated last_used timestamp to {current_time}")
            
            # If no rows were affected, the model doesn't exist in the database
            else:
                # Try to get the file size
                size_bytes = 0
                if os.path.exists(path):
                    size_bytes = os.path.getsize(path)
                
                # Get the model type from the path
                model_type = "unknown"
                path_parts = path.split(os.sep)
                if "models" in path_parts:
                    models_index = path_parts.index("models")
                    if models_index + 1 < len(path_parts):
                        model_type = path_parts[models_index + 1]
                
                # Insert the model
                filename = os.path.basename(path)
                cursor.execute('''
                INSERT INTO models (path, model_type, filename, size_bytes, last_used, use_count, download_date, protected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (path, model_type, filename, size_bytes, current_time, 1, current_time, 0))
                log_debug(f"Added missing model to database: {path}")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log_debug(f"Error updating model usage: {str(e)}")
            return False
    
    def get_model_info(self, path):
        """
        Get information about a model
        
        Args:
            path (str): Full path to the model file
        
        Returns:
            dict: Model information or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, path, model_type, filename, size_bytes, last_used, use_count, download_date, protected
            FROM models
            WHERE path = ?
            ''', (path,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'path': row[1],
                    'model_type': row[2],
                    'filename': row[3],
                    'size_bytes': row[4],
                    'last_used': row[5],
                    'use_count': row[6],
                    'download_date': row[7],
                    'protected': bool(row[8])
                }
            return None
        except Exception as e:
            log_debug(f"Error getting model info: {str(e)}")
            return None
    
    def get_all_models(self):
        """
        Get information about all models
        
        Returns:
            list: List of model information dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, path, model_type, filename, size_bytes, last_used, use_count, download_date, protected
            FROM models
            ORDER BY last_used DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            models = []
            for row in rows:
                models.append({
                    'id': row[0],
                    'path': row[1],
                    'model_type': row[2],
                    'filename': row[3],
                    'size_bytes': row[4],
                    'last_used': row[5],
                    'use_count': row[6],
                    'download_date': row[7],
                    'protected': bool(row[8])
                })
            return models
        except Exception as e:
            log_debug(f"Error getting all models: {str(e)}")
            return []
    
    def get_least_recently_used_models(self, limit=10):
        """
        Get the least recently used models
        
        Args:
            limit (int): Maximum number of models to return
        
        Returns:
            list: List of model information dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, path, model_type, filename, size_bytes, last_used, use_count, download_date, protected
            FROM models
            WHERE protected = 0
            ORDER BY last_used ASC
            LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            models = []
            for row in rows:
                models.append({
                    'id': row[0],
                    'path': row[1],
                    'model_type': row[2],
                    'filename': row[3],
                    'size_bytes': row[4],
                    'last_used': row[5],
                    'use_count': row[6],
                    'download_date': row[7],
                    'protected': bool(row[8])
                })
            return models
        except Exception as e:
            log_debug(f"Error getting least recently used models: {str(e)}")
            return []
    
    def delete_model(self, path):
        """
        Delete a model from the database
        
        Args:
            path (str): Full path to the model file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            log_debug(f"Deleting model from database: {path}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM models WHERE path = ?', (path,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log_debug(f"Error deleting model: {str(e)}")
            return False
    
    def get_setting(self, key, default=None):
        """
        Get a setting from the database
        
        Args:
            key (str): Setting key
            default: Default value if setting doesn't exist
        
        Returns:
            str: Setting value
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row[0]
            return default
        except Exception as e:
            log_debug(f"Error getting setting: {str(e)}")
            return default
    
    def set_setting(self, key, value):
        """
        Set a setting in the database
        
        Args:
            key (str): Setting key
            value (str): Setting value
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
            ''', (key, value))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log_debug(f"Error setting setting: {str(e)}")
            return False

# Create a singleton instance
model_cache_db = ModelCacheDB()
