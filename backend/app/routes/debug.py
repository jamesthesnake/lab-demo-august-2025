"""
Debug and observability routes for AIDO-Lab
Provides debugging endpoints, metrics, and system health monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, List, Any, Optional
import json
import logging
import time
import psutil
import docker
from datetime import datetime, timedelta
from collections import defaultdict, deque

from app.services.git_session_manager import GitSessionManager
from app.services.secure_kernel_manager import SecureKernelManager
from app.models.database import get_db, Session as DBSession, Conversation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])

# Global managers
git_session_manager = GitSessionManager()
secure_kernel_manager = SecureKernelManager()

# Metrics storage (in production, use Redis or Prometheus)
metrics = {
    'execution_times': deque(maxlen=1000),
    'queue_depth': deque(maxlen=1000),
    'oom_kills': 0,
    'container_starts': 0,
    'container_failures': 0,
    'api_requests': defaultdict(int),
    'error_counts': defaultdict(int)
}

@router.get("/health")
async def health_check():
    """System health check endpoint"""
    try:
        # Check Docker daemon
        docker_client = docker.from_env()
        docker_info = docker_client.info()
        docker_healthy = True
    except Exception as e:
        docker_healthy = False
        docker_info = {"error": str(e)}

    # Check system resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Check active containers
    active_containers = 0
    try:
        containers = docker_client.containers.list(filters={'label': 'aido-lab=true'})
        active_containers = len(containers)
    except:
        pass

    health_status = {
        "status": "healthy" if docker_healthy and cpu_percent < 90 and memory.percent < 90 else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "docker": {
            "healthy": docker_healthy,
            "info": docker_info if docker_healthy else None,
            "active_containers": active_containers
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        },
        "metrics": {
            "total_executions": len(metrics['execution_times']),
            "avg_execution_time": sum(metrics['execution_times']) / len(metrics['execution_times']) if metrics['execution_times'] else 0,
            "oom_kills": metrics['oom_kills'],
            "container_starts": metrics['container_starts'],
            "container_failures": metrics['container_failures']
        }
    }

    return health_status

@router.get("/metrics")
async def get_metrics():
    """Prometheus-style metrics endpoint"""
    
    def generate_metrics():
        # Execution time metrics
        if metrics['execution_times']:
            avg_time = sum(metrics['execution_times']) / len(metrics['execution_times'])
            yield f"# HELP aido_execution_time_seconds Average code execution time\n"
            yield f"# TYPE aido_execution_time_seconds gauge\n"
            yield f"aido_execution_time_seconds {avg_time:.3f}\n"
        
        # Container metrics
        yield f"# HELP aido_containers_started_total Total containers started\n"
        yield f"# TYPE aido_containers_started_total counter\n"
        yield f"aido_containers_started_total {metrics['container_starts']}\n"
        
        yield f"# HELP aido_containers_failed_total Total container failures\n"
        yield f"# TYPE aido_containers_failed_total counter\n"
        yield f"aido_containers_failed_total {metrics['container_failures']}\n"
        
        yield f"# HELP aido_oom_kills_total Total OOM kills\n"
        yield f"# TYPE aido_oom_kills_total counter\n"
        yield f"aido_oom_kills_total {metrics['oom_kills']}\n"
        
        # Queue depth
        if metrics['queue_depth']:
            current_queue = metrics['queue_depth'][-1]
            yield f"# HELP aido_queue_depth Current execution queue depth\n"
            yield f"# TYPE aido_queue_depth gauge\n"
            yield f"aido_queue_depth {current_queue}\n"
        
        # API request metrics
        for endpoint, count in metrics['api_requests'].items():
            yield f"# HELP aido_api_requests_total Total API requests by endpoint\n"
            yield f"# TYPE aido_api_requests_total counter\n"
            yield f"aido_api_requests_total{{endpoint=\"{endpoint}\"}} {count}\n"
        
        # Error metrics
        for error_type, count in metrics['error_counts'].items():
            yield f"# HELP aido_errors_total Total errors by type\n"
            yield f"# TYPE aido_errors_total counter\n"
            yield f"aido_errors_total{{type=\"{error_type}\"}} {count}\n"

    return StreamingResponse(generate_metrics(), media_type="text/plain")

@router.get("/sessions/{session_id}/replay")
async def replay_session(session_id: str, db: DBSession = Depends(get_db)):
    """Replay session execution history with container logs"""
    
    # Get session conversations
    conversations = db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).order_by(Conversation.created_at).all()
    
    if not conversations:
        raise HTTPException(status_code=404, detail="Session not found")
    
    replay_data = []
    
    for conv in conversations:
        entry = {
            "id": conv.id,
            "timestamp": conv.created_at.isoformat(),
            "branch": conv.branch_name,
            "prompt": conv.prompt,
            "response": conv.response,
            "code": conv.code_executed,
            "execution_result": json.loads(conv.execution_result) if conv.execution_result else None,
            "artifacts": json.loads(conv.artifacts) if conv.artifacts else []
        }
        
        # Try to get container logs if available
        try:
            container_logs = await secure_kernel_manager.get_execution_logs(session_id, conv.id)
            entry["container_logs"] = container_logs
        except Exception as e:
            entry["container_logs"] = {"error": str(e)}
        
        replay_data.append(entry)
    
    return {
        "session_id": session_id,
        "total_conversations": len(conversations),
        "replay_data": replay_data
    }

@router.get("/sessions/{session_id}/git-log")
async def get_git_log(session_id: str, limit: int = 50):
    """Get detailed git log for session"""
    try:
        history = git_session_manager.get_commit_history(session_id, limit=limit)
        tree = git_session_manager.get_branch_tree(session_id)
        
        return {
            "session_id": session_id,
            "commit_history": history,
            "branch_tree": tree,
            "total_commits": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")

@router.get("/containers")
async def list_debug_containers():
    """List all AIDO-Lab containers with detailed info"""
    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list(
            all=True, 
            filters={'label': 'aido-lab=true'}
        )
        
        container_info = []
        for container in containers:
            info = {
                "id": container.id[:12],
                "name": container.name,
                "status": container.status,
                "created": container.attrs['Created'],
                "labels": container.labels,
                "ports": container.ports,
                "stats": None
            }
            
            # Get container stats if running
            if container.status == 'running':
                try:
                    stats = container.stats(stream=False)
                    cpu_stats = stats['cpu_stats']
                    memory_stats = stats['memory_stats']
                    
                    info["stats"] = {
                        "cpu_percent": calculate_cpu_percent(stats),
                        "memory_usage_mb": memory_stats.get('usage', 0) / (1024 * 1024),
                        "memory_limit_mb": memory_stats.get('limit', 0) / (1024 * 1024)
                    }
                except:
                    pass
            
            container_info.append(info)
        
        return {
            "total_containers": len(container_info),
            "containers": container_info
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list containers: {str(e)}")

@router.post("/containers/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100):
    """Get logs from specific container"""
    try:
        docker_client = docker.from_env()
        container = docker_client.containers.get(container_id)
        
        logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
        
        return {
            "container_id": container_id,
            "logs": logs.split('\n') if logs else []
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@router.post("/metrics/record")
async def record_metric(metric_type: str, value: float, labels: Dict[str, str] = None):
    """Record a custom metric (for internal use)"""
    timestamp = time.time()
    
    if metric_type == "execution_time":
        metrics['execution_times'].append(value)
    elif metric_type == "queue_depth":
        metrics['queue_depth'].append(value)
    elif metric_type == "oom_kill":
        metrics['oom_kills'] += 1
    elif metric_type == "container_start":
        metrics['container_starts'] += 1
    elif metric_type == "container_failure":
        metrics['container_failures'] += 1
    elif metric_type == "api_request":
        endpoint = labels.get('endpoint', 'unknown') if labels else 'unknown'
        metrics['api_requests'][endpoint] += 1
    elif metric_type == "error":
        error_type = labels.get('type', 'unknown') if labels else 'unknown'
        metrics['error_counts'][error_type] += 1
    
    return {"status": "recorded", "metric_type": metric_type, "value": value}

@router.get("/system/docker-events")
async def stream_docker_events():
    """Stream Docker events for monitoring"""
    
    async def generate_events():
        try:
            docker_client = docker.from_env()
            
            for event in docker_client.events(decode=True, filters={'label': 'aido-lab=true'}):
                yield f"data: {json.dumps(event)}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate_events(), media_type="text/plain")

def calculate_cpu_percent(stats):
    """Calculate CPU percentage from Docker stats"""
    try:
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            return round(cpu_percent, 2)
    except:
        pass
    
    return 0.0
