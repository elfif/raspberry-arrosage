#!/usr/bin/env python3
"""
Centralized Redis Connection Module

This module provides a centralized way to handle Redis connections across the project.
It uses the configuration from redis_config.py and provides both connection functions
and utility methods for common Redis operations.
"""

import redis
import json
import sys
import os
from typing import Optional, Any, Dict

# Add the project root to the path to import redis_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from redis_config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
except ImportError:
    # Fallback to default values if config file is not available
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None

def get_redis_connection(host: Optional[str] = None, port: Optional[int] = None, 
                        db: Optional[int] = None, password: Optional[str] = None) -> redis.Redis:
    """
    Create and return a Redis connection with automatic configuration fallback.
    
    Args:
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    
    Returns:
        redis.Redis: Redis connection object with decode_responses=True
    
    Raises:
        redis.ConnectionError: If connection to Redis fails
    """
    # Use provided parameters or fall back to config defaults
    connection_host = host if host is not None else REDIS_HOST
    connection_port = port if port is not None else REDIS_PORT
    connection_db = db if db is not None else REDIS_DB
    connection_password = password if password is not None else REDIS_PASSWORD
    
    try:
        r = redis.Redis(
            host=connection_host,
            port=connection_port,
            db=connection_db,
            password=connection_password,
            decode_responses=True
        )
        # Test connection
        r.ping()
        return r
    except redis.ConnectionError as e:
        raise redis.ConnectionError(f"Failed to connect to Redis at {connection_host}:{connection_port}: {e}")

def check_redis_connection(host: Optional[str] = None, port: Optional[int] = None, 
                          db: Optional[int] = None, password: Optional[str] = None) -> bool:
    """
    Check if Redis connection is available without raising exceptions.
    
    Args:
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        r = get_redis_connection(host, port, db, password)
        r.ping()
        return True
    except:
        return False

def get_json_from_redis(key: str, host: Optional[str] = None, port: Optional[int] = None, 
                       db: Optional[int] = None, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get and parse JSON data from Redis key.
    
    Args:
        key (str): Redis key to retrieve
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    
    Returns:
        Dict[str, Any] or None: Parsed JSON data if successful, None if failed
    """
    try:
        r = get_redis_connection(host, port, db, password)
        data = r.get(key)
        if data is None:
            return None
        
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            # Return raw data if it's not JSON
            return data
            
    except redis.ConnectionError:
        return None
    except Exception:
        return None

def set_json_to_redis(key: str, data: Dict[str, Any], host: Optional[str] = None, 
                     port: Optional[int] = None, db: Optional[int] = None, 
                     password: Optional[str] = None) -> bool:
    """
    Store JSON data in Redis key.
    
    Args:
        key (str): Redis key to store data in
        data (Dict[str, Any]): Data to store (will be JSON serialized)
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        r = get_redis_connection(host, port, db, password)
        json_data = json.dumps(data, indent=2)
        r.set(key, json_data)
        return True
        
    except redis.ConnectionError:
        return False
    except json.JSONEncodeError:
        return False
    except Exception:
        return False

def print_connection_info(host: Optional[str] = None, port: Optional[int] = None, 
                         db: Optional[int] = None, password: Optional[str] = None):
    """
    Print Redis connection information.
    
    Args:
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    """
    connection_host = host if host is not None else REDIS_HOST
    connection_port = port if port is not None else REDIS_PORT
    connection_db = db if db is not None else REDIS_DB
    connection_password = password if password is not None else REDIS_PASSWORD
    
    print(f"🔧 Redis Configuration:")
    print(f"   Host: {connection_host}")
    print(f"   Port: {connection_port}")
    print(f"   Database: {connection_db}")
    print(f"   Password: {'Set' if connection_password else 'None'}")

if __name__ == "__main__":
    print("🔧 Redis Connection Module Test")
    print("=" * 35)
    
    # Print connection info
    print_connection_info()
    print()
    
    # Test connection
    print("🔍 Testing Redis connection...")
    if check_redis_connection():
        print("✅ Redis connection successful!")
        
        # Test basic operations
        try:
            r = get_redis_connection()
            print("📊 Redis info:")
            print(f"   Server version: {r.info()['redis_version']}")
            print(f"   Connected clients: {r.info()['connected_clients']}")
            print(f"   Used memory: {r.info()['used_memory_human']}")
        except Exception as e:
            print(f"⚠️  Could not get Redis info: {e}")
    else:
        print("❌ Redis connection failed!")
        print("💡 Make sure Redis is running and configuration is correct")
