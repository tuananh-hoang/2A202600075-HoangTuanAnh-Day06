"""
redis_client.py — Redis Client Singleton

Centralized Redis connection management.
Supports both local development and production (Railway Redis).
"""
import logging
from typing import Optional
import redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Singleton Redis client với connection pooling.
    """
    
    _instance: Optional[redis.Redis] = None
    _is_connected: bool = False
    
    @classmethod
    def get_client(cls) -> Optional[redis.Redis]:
        """
        Lấy Redis client instance.
        
        Returns:
            redis.Redis hoặc None nếu Redis disabled hoặc không connect được
        """
        if not settings.redis_enabled:
            logger.info("Redis is disabled in config")
            return None
        
        if cls._instance is None:
            try:
                cls._instance = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,  # Auto decode bytes to str
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                # Test connection
                cls._instance.ping()
                cls._is_connected = True
                logger.info(f"✅ Redis connected: {settings.redis_url}")
            except RedisError as e:
                logger.error(f"❌ Redis connection failed: {e}")
                cls._instance = None
                cls._is_connected = False
        
        return cls._instance
    
    @classmethod
    def is_healthy(cls) -> bool:
        """
        Kiểm tra Redis connection health.
        
        Returns:
            bool: True nếu Redis healthy hoặc disabled, False nếu enabled nhưng down
        """
        if not settings.redis_enabled:
            return True  # Redis disabled = không cần check
        
        if cls._instance is None:
            return False
        
        try:
            cls._instance.ping()
            cls._is_connected = True
            return True
        except RedisError as e:
            logger.warning(f"Redis health check failed: {e}")
            cls._is_connected = False
            return False
    
    @classmethod
    def close(cls):
        """Đóng Redis connection (gọi khi shutdown)."""
        if cls._instance:
            try:
                cls._instance.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")
            finally:
                cls._instance = None
                cls._is_connected = False


def get_redis() -> Optional[redis.Redis]:
    """Helper function để lấy Redis client."""
    return RedisClient.get_client()
