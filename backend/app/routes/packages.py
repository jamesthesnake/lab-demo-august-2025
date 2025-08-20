from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()

class PackageInstallRequest(BaseModel):
    package: str

class PackageUninstallRequest(BaseModel):
    package: str

class InstalledPackage(BaseModel):
    name: str
    version: str
    size: str = ""

class PackageListResponse(BaseModel):
    packages: List[InstalledPackage]
    total: int

@router.get("/api/packages/{session_id}")
async def list_packages(session_id: str) -> PackageListResponse:
    """List all installed packages in the session environment"""
    try:
        # Get list of installed packages using pip list --format=json
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to list packages: {result.stderr}")
            raise HTTPException(status_code=500, detail="Failed to list packages")
        
        # Parse the JSON output
        packages_data = json.loads(result.stdout)
        
        # Convert to our format
        packages = []
        for pkg in packages_data:
            packages.append(InstalledPackage(
                name=pkg["name"],
                version=pkg["version"],
                size=""  # pip list doesn't provide size info
            ))
        
        # Sort packages alphabetically
        packages.sort(key=lambda x: x.name.lower())
        
        return PackageListResponse(packages=packages, total=len(packages))
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Package listing timed out")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse package list")
    except Exception as e:
        logger.error(f"Error listing packages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/packages/{session_id}/install")
async def install_package(session_id: str, request: PackageInstallRequest):
    """Install a Python package using pip"""
    package_name = request.package.strip()
    
    if not package_name:
        raise HTTPException(status_code=400, detail="Package name is required")
    
    # Validate package name (basic security check)
    if any(char in package_name for char in [';', '&', '|', '`', '$']):
        raise HTTPException(status_code=400, detail="Invalid package name")
    
    try:
        logger.info(f"Installing package: {package_name}")
        
        # Install package using pip
        result = subprocess.run(
            ["pip", "install", package_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for installation
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            logger.error(f"Package installation failed: {error_msg}")
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to install {package_name}: {error_msg}"
            )
        
        logger.info(f"Successfully installed package: {package_name}")
        
        return {
            "success": True,
            "message": f"Successfully installed {package_name}",
            "output": result.stdout
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, 
            detail=f"Package installation timed out for {package_name}"
        )
    except Exception as e:
        logger.error(f"Error installing package {package_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/packages/{session_id}/uninstall")
async def uninstall_package(session_id: str, request: PackageUninstallRequest):
    """Uninstall a Python package using pip"""
    package_name = request.package.strip()
    
    if not package_name:
        raise HTTPException(status_code=400, detail="Package name is required")
    
    # Prevent uninstalling critical packages
    protected_packages = {'pip', 'setuptools', 'wheel', 'python'}
    if package_name.lower() in protected_packages:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot uninstall protected package: {package_name}"
        )
    
    try:
        logger.info(f"Uninstalling package: {package_name}")
        
        # Uninstall package using pip
        result = subprocess.run(
            ["pip", "uninstall", package_name, "-y"],  # -y for yes to all prompts
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            logger.error(f"Package uninstallation failed: {error_msg}")
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to uninstall {package_name}: {error_msg}"
            )
        
        logger.info(f"Successfully uninstalled package: {package_name}")
        
        return {
            "success": True,
            "message": f"Successfully uninstalled {package_name}",
            "output": result.stdout
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, 
            detail=f"Package uninstallation timed out for {package_name}"
        )
    except Exception as e:
        logger.error(f"Error uninstalling package {package_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/packages/{session_id}/environment")
async def get_environment_info(session_id: str):
    """Get Python environment information"""
    try:
        # Get Python version
        python_result = subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Get pip version
        pip_result = subprocess.run(
            ["pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "python_version": python_result.stdout.strip() if python_result.returncode == 0 else "Unknown",
            "pip_version": pip_result.stdout.strip() if pip_result.returncode == 0 else "Unknown",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error getting environment info: {e}")
        return {
            "python_version": "Unknown",
            "pip_version": "Unknown",
            "session_id": session_id
        }
