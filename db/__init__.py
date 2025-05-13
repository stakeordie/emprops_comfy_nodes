# Added: 2025-05-13T17:12:00-04:00 - Database package initialization
# Updated: 2025-05-13T17:40:23-04:00 - Initialize database on import
from .init_db import init_db

# Initialize the database when the module is imported
init_db()

# Import the model cache database after initialization
from .model_cache import model_cache_db

__all__ = ['model_cache_db', 'init_db']
