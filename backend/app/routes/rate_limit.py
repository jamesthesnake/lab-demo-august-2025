"""
Rate limiting and resource management for AIDO-Lab
Implements token bucket rate limiting and resource caps per IP/user
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import time
import json
import redis
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rate-limit", tags=["rate-limit"])

# Redis client for distributed rate limiting
try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory rate limiting")

# In-memory fallback storage
memory_store = {}

@dataclass
class RateLimit:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    max_concurrent_executions: int = 3
    max_execution_time_seconds: int = 300
    max_memory_mb: int = 512
    max_cpu_cores: float = 0.5

@dataclass
class ResourceUsage:
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    requests_this_day: int = 0
    concurrent_executions: int = 0
    total_execution_time: float = 0
    last_request_time: float = 0
    blocked_until: Optional[float] = None

# Default rate limits
DEFAULT_LIMITS = RateLimit()
PREMIUM_LIMITS = RateLimit(
    requests_per_minute=120,
    requests_per_hour=5000,
    requests_per_day=50000,
    max_concurrent_executions=5,
    max_execution_time_seconds=600,
    max_memory_mb=1024,
    max_cpu_cores=1.0
)

def get_client_id(request: Request) -> str:
    """Get unique client identifier from request"""
    # Try to get user ID from auth header
    auth_header = request.headers.get('authorization')
    if auth_header:
        return hashlib.sha256(auth_header.encode()).hexdigest()[:16]
    
    # Fall back to IP address
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.client.host
    
    return f"ip_{client_ip}"

def get_rate_limits(client_id: str) -> RateLimit:
    """Get rate limits for client (could be based on subscription tier)"""
    # For now, return default limits
    # In production, check user subscription tier from database
    return DEFAULT_LIMITS

def get_usage_key(client_id: str, window: str) -> str:
    """Generate Redis key for usage tracking"""
    now = datetime.utcnow()
    
    if window == "minute":
        time_window = now.strftime("%Y-%m-%d-%H-%M")
    elif window == "hour":
        time_window = now.strftime("%Y-%m-%d-%H")
    elif window == "day":
        time_window = now.strftime("%Y-%m-%d")
    else:
        time_window = "global"
    
    return f"aido:rate_limit:{client_id}:{window}:{time_window}"

def get_resource_usage(client_id: str) -> ResourceUsage:
    """Get current resource usage for client"""
    if REDIS_AVAILABLE:
        try:
            # Get usage from Redis
            minute_key = get_usage_key(client_id, "minute")
            hour_key = get_usage_key(client_id, "hour")
            day_key = get_usage_key(client_id, "day")
            global_key = f"aido:usage:{client_id}"
            
            pipe = redis_client.pipeline()
            pipe.get(minute_key)
            pipe.get(hour_key)
            pipe.get(day_key)
            pipe.hgetall(global_key)
            results = pipe.execute()
            
            usage = ResourceUsage(
                requests_this_minute=int(results[0] or 0),
                requests_this_hour=int(results[1] or 0),
                requests_this_day=int(results[2] or 0),
                concurrent_executions=int(results[3].get('concurrent_executions', 0)),
                total_execution_time=float(results[3].get('total_execution_time', 0)),
                last_request_time=float(results[3].get('last_request_time', 0)),
                blocked_until=float(results[3].get('blocked_until', 0)) if results[3].get('blocked_until') else None
            )
            
            return usage
        except Exception as e:
            logger.error(f"Redis error getting usage: {e}")
    
    # Fallback to memory store
    return memory_store.get(client_id, ResourceUsage())

def update_resource_usage(client_id: str, usage: ResourceUsage):
    """Update resource usage for client"""
    if REDIS_AVAILABLE:
        try:
            # Update Redis
            minute_key = get_usage_key(client_id, "minute")
            hour_key = get_usage_key(client_id, "hour")
            day_key = get_usage_key(client_id, "day")
            global_key = f"aido:usage:{client_id}"
            
            pipe = redis_client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            pipe.incr(day_key)
            pipe.expire(day_key, 86400)
            pipe.hset(global_key, mapping={
                'concurrent_executions': usage.concurrent_executions,
                'total_execution_time': usage.total_execution_time,
                'last_request_time': usage.last_request_time,
                'blocked_until': usage.blocked_until or 0
            })
            pipe.expire(global_key, 86400)
            pipe.execute()
            
            return
        except Exception as e:
            logger.error(f"Redis error updating usage: {e}")
    
    # Fallback to memory store
    memory_store[client_id] = usage

def check_rate_limit(request: Request) -> Dict[str, Any]:
    """Check if request should be rate limited"""
    client_id = get_client_id(request)
    limits = get_rate_limits(client_id)
    usage = get_resource_usage(client_id)
    current_time = time.time()
    
    # Check if client is currently blocked
    if usage.blocked_until and current_time < usage.blocked_until:
        remaining_block_time = usage.blocked_until - current_time
        return {
            "allowed": False,
            "reason": "temporarily_blocked",
            "retry_after": remaining_block_time,
            "message": f"Too many requests. Try again in {remaining_block_time:.0f} seconds."
        }
    
    # Check rate limits
    if usage.requests_this_minute >= limits.requests_per_minute:
        return {
            "allowed": False,
            "reason": "rate_limit_minute",
            "retry_after": 60,
            "message": f"Rate limit exceeded: {limits.requests_per_minute} requests per minute"
        }
    
    if usage.requests_this_hour >= limits.requests_per_hour:
        return {
            "allowed": False,
            "reason": "rate_limit_hour",
            "retry_after": 3600,
            "message": f"Rate limit exceeded: {limits.requests_per_hour} requests per hour"
        }
    
    if usage.requests_this_day >= limits.requests_per_day:
        return {
            "allowed": False,
            "reason": "rate_limit_day",
            "retry_after": 86400,
            "message": f"Rate limit exceeded: {limits.requests_per_day} requests per day"
        }
    
    # Check concurrent executions
    if usage.concurrent_executions >= limits.max_concurrent_executions:
        return {
            "allowed": False,
            "reason": "concurrent_limit",
            "retry_after": 30,
            "message": f"Too many concurrent executions: {limits.max_concurrent_executions} max"
        }
    
    # Update usage counters
    usage.requests_this_minute += 1
    usage.requests_this_hour += 1
    usage.requests_this_day += 1
    usage.last_request_time = current_time
    
    # Check for abuse patterns
    if current_time - usage.last_request_time < 1.0:  # More than 1 request per second
        consecutive_fast_requests = getattr(usage, 'consecutive_fast_requests', 0) + 1
        if consecutive_fast_requests > 10:
            # Block for 5 minutes
            usage.blocked_until = current_time + 300
            update_resource_usage(client_id, usage)
            return {
                "allowed": False,
                "reason": "abuse_detected",
                "retry_after": 300,
                "message": "Abuse detected. Blocked for 5 minutes."
            }
    
    update_resource_usage(client_id, usage)
    
    return {
        "allowed": True,
        "limits": asdict(limits),
        "usage": asdict(usage),
        "remaining": {
            "minute": limits.requests_per_minute - usage.requests_this_minute,
            "hour": limits.requests_per_hour - usage.requests_this_hour,
            "day": limits.requests_per_day - usage.requests_this_day
        }
    }

# Dependency for rate limiting
async def rate_limit_dependency(request: Request):
    """FastAPI dependency for rate limiting"""
    result = check_rate_limit(request)
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=result["message"],
            headers={"Retry-After": str(int(result["retry_after"]))}
        )
    
    return result

@router.get("/status")
async def get_rate_limit_status(request: Request):
    """Get current rate limit status for client"""
    client_id = get_client_id(request)
    limits = get_rate_limits(client_id)
    usage = get_resource_usage(client_id)
    
    return {
        "client_id": client_id,
        "limits": asdict(limits),
        "usage": asdict(usage),
        "remaining": {
            "minute": max(0, limits.requests_per_minute - usage.requests_this_minute),
            "hour": max(0, limits.requests_per_hour - usage.requests_this_hour),
            "day": max(0, limits.requests_per_day - usage.requests_this_day)
        },
        "reset_times": {
            "minute": int(time.time() + 60),
            "hour": int(time.time() + 3600),
            "day": int(time.time() + 86400)
        }
    }

@router.post("/execution/start")
async def start_execution(request: Request, session_id: str):
    """Mark start of code execution for resource tracking"""
    client_id = get_client_id(request)
    usage = get_resource_usage(client_id)
    
    usage.concurrent_executions += 1
    update_resource_usage(client_id, usage)
    
    return {"status": "execution_started", "concurrent_executions": usage.concurrent_executions}

@router.post("/execution/end")
async def end_execution(request: Request, session_id: str, execution_time: float):
    """Mark end of code execution for resource tracking"""
    client_id = get_client_id(request)
    usage = get_resource_usage(client_id)
    
    usage.concurrent_executions = max(0, usage.concurrent_executions - 1)
    usage.total_execution_time += execution_time
    update_resource_usage(client_id, usage)
    
    return {
        "status": "execution_ended",
        "concurrent_executions": usage.concurrent_executions,
        "total_execution_time": usage.total_execution_time
    }

@router.delete("/client/{client_id}/reset")
async def reset_client_limits(client_id: str):
    """Reset rate limits for a specific client (admin only)"""
    if REDIS_AVAILABLE:
        try:
            # Delete all Redis keys for this client
            keys = redis_client.keys(f"aido:*:{client_id}:*")
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis error resetting limits: {e}")
    
    # Remove from memory store
    memory_store.pop(client_id, None)
    
    return {"status": "reset", "client_id": client_id}

@router.get("/stats")
async def get_rate_limit_stats():
    """Get global rate limiting statistics"""
    stats = {
        "redis_available": REDIS_AVAILABLE,
        "memory_store_clients": len(memory_store),
        "total_blocked_clients": 0,
        "active_executions": 0
    }
    
    if REDIS_AVAILABLE:
        try:
            # Count blocked clients and active executions
            for key in redis_client.scan_iter(match="aido:usage:*"):
                usage_data = redis_client.hgetall(key)
                if usage_data.get('blocked_until') and float(usage_data['blocked_until']) > time.time():
                    stats["total_blocked_clients"] += 1
                stats["active_executions"] += int(usage_data.get('concurrent_executions', 0))
        except Exception as e:
            logger.error(f"Redis error getting stats: {e}")
    else:
        # Count from memory store
        current_time = time.time()
        for usage in memory_store.values():
            if usage.blocked_until and current_time < usage.blocked_until:
                stats["total_blocked_clients"] += 1
            stats["active_executions"] += usage.concurrent_executions
    
    return stats
