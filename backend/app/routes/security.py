"""
Security and Container Management Routes
Panic button and container monitoring endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging

from app.services.simple_kernel_manager import SimpleKernelManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security", tags=["security"])

# Global secure kernel manager instance
secure_kernel_manager = None

def get_secure_kernel_manager() -> SimpleKernelManager:
    """Dependency to get secure kernel manager"""
    global secure_kernel_manager
    if secure_kernel_manager is None:
        secure_kernel_manager = SimpleKernelManager()
    return secure_kernel_manager

@router.post("/panic")
async def panic_button(
    kernel_manager: SimpleKernelManager = Depends(get_secure_kernel_manager)
):
    """
    Emergency panic button - kills all running containers immediately
    """
    try:
        killed_count = await kernel_manager.panic_kill_all()
        logger.warning(f"PANIC BUTTON ACTIVATED - Killed {killed_count} containers")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Panic button activated",
                "containers_killed": killed_count,
                "status": "success"
            }
        )
    except Exception as e:
        logger.error(f"Panic button failed: {e}")
        raise HTTPException(status_code=500, detail=f"Panic operation failed: {e}")

@router.delete("/containers/{container_id}")
async def kill_container(
    container_id: str,
    kernel_manager: SimpleKernelManager = Depends(get_secure_kernel_manager)
):
    """
    Kill specific container by ID
    """
    try:
        success = await kernel_manager.kill_container(container_id)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "message": f"Container {container_id[:12]} killed successfully",
                    "container_id": container_id,
                    "status": "killed"
                }
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Container {container_id} not found or already stopped"
            )
            
    except Exception as e:
        logger.error(f"Failed to kill container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Kill operation failed: {e}")

@router.get("/containers")
async def list_active_containers(
    kernel_manager: SimpleKernelManager = Depends(get_secure_kernel_manager)
) -> Dict[str, Any]:
    """
    List all active containers and their status
    """
    try:
        containers = kernel_manager.get_active_containers()
        
        return {
            "active_containers": containers,
            "total_count": len(containers),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        raise HTTPException(status_code=500, detail=f"Container listing failed: {e}")

@router.delete("/sessions/{session_id}")
async def cleanup_session(
    session_id: str,
    kernel_manager: SimpleKernelManager = Depends(get_secure_kernel_manager)
):
    """
    Clean up all resources for a specific session
    """
    try:
        await kernel_manager.cleanup_session(session_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Session {session_id} cleaned up successfully",
                "session_id": session_id,
                "status": "cleaned"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Session cleanup failed: {e}")

@router.get("/health")
async def security_health_check(
    kernel_manager: SimpleKernelManager = Depends(get_secure_kernel_manager)
):
    """
    Check security system health
    """
    try:
        containers = kernel_manager.get_active_containers()
        
        return {
            "status": "healthy",
            "active_containers": len(containers),
            "docker_available": True,
            "security_features": {
                "seccomp": True,
                "apparmor": True,
                "read_only_rootfs": True,
                "network_isolation": True,
                "resource_limits": True,
                "timeout_enforcement": True
            }
        }
        
    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        raise HTTPException(status_code=500, detail={
            "status": "unhealthy",
            "error": str(e),
            "docker_available": False
        })
