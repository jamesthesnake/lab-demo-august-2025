# AIDO-Lab Security Implementation

## Overview
The AIDO-Lab platform now implements enterprise-grade security for arbitrary code execution using containerized sandboxes with multiple layers of protection.

## Security Features

### 🔒 Container Isolation
- **Docker-based execution**: Each session runs in an isolated container
- **Non-root user**: Code executes as `sandbox` user with minimal privileges
- **Read-only root filesystem**: Base system files cannot be modified
- **Temporary filesystems**: Only `/tmp` and `/workspace` are writable with size limits

### 🌐 Network Restrictions
- **Default deny**: All network egress blocked by default
- **Allowlist approach**: Only PyPI and conda repositories accessible
- **No host network access**: Containers cannot reach host services
- **Isolated bridge network**: Custom network with inter-container communication disabled

### ⚡ Resource Limits
- **Memory limit**: 512MB maximum per container
- **CPU limit**: 0.5 CPU cores maximum
- **Disk space**: 100MB workspace limit
- **Process limit**: Maximum 50 processes
- **File descriptor limit**: 1024 open files

### ⏰ Execution Controls
- **30-second timeout**: Hard limit on execution time
- **Automatic cleanup**: Containers killed after timeout
- **Session isolation**: One container per session
- **Panic button**: Emergency kill-all endpoint

### 🛡️ Security Profiles
- **Seccomp**: Syscall filtering to block dangerous operations
- **AppArmor**: Additional access control layer
- **Capability dropping**: Removes CAP_SYS_ADMIN and other dangerous capabilities
- **No new privileges**: Prevents privilege escalation

## API Endpoints

### Security Management
- `POST /api/security/panic` - Emergency kill all containers
- `DELETE /api/security/containers/{id}` - Kill specific container
- `GET /api/security/containers` - List active containers
- `DELETE /api/security/sessions/{id}` - Cleanup session
- `GET /api/security/health` - Security system status

### Code Execution
- `POST /api/chat` - Execute code via LLM (uses secure containers)
- All code execution automatically routed through secure kernel manager

## Security Testing

Run the comprehensive security test suite:

```bash
python test_security.py
```

Tests include:
- Container isolation verification
- Network access restrictions
- Filesystem security
- Resource limit enforcement
- Timeout mechanisms
- Panic button functionality

## Container Configuration

### Dockerfile.secure
- Minimal Python 3.11 base image
- Non-root sandbox user
- Essential packages only (pandas, numpy, matplotlib, etc.)
- No network tools or system utilities

### Security Profiles
- **seccomp-profile.json**: Whitelist of allowed syscalls
- **network-policy.json**: Network access rules
- **docker-compose.secure.yml**: Complete security configuration

## Implementation Details

### SecureKernelManager
- Replaces standard Jupyter kernels
- Docker API integration
- Automatic container lifecycle management
- Artifact collection and cleanup

### Security Router
- Panic button implementation
- Container monitoring
- Session cleanup
- Health checks

## Compliance Features

✅ **No network egress** except controlled mirrors (PyPI, conda)  
✅ **No host mount** except single, size-capped volume  
✅ **seccomp/AppArmor** security profiles active  
✅ **Dropped capabilities** (CAP_SYS_ADMIN, etc.)  
✅ **Read-only rootfs** with minimal writable tmpfs  
✅ **One sandbox per session** with automatic cleanup  
✅ **30-second wall-time limit** with SIGKILL enforcement  
✅ **Panic button endpoint** for emergency container termination  

## Usage

The security layer is transparent to users. All code execution requests automatically use secure containers:

```python
# This code runs in a secure, isolated container
import pandas as pd
data = pd.read_csv('data.csv')
print(data.head())
```

## Monitoring

Check security status:
```bash
curl http://localhost:8000/api/security/health
```

Emergency stop all containers:
```bash
curl -X POST http://localhost:8000/api/security/panic
```

## Architecture

```
User Request → FastAPI → SecureKernelManager → Docker Container
                                           ↓
                                    [Isolated Execution]
                                           ↓
                                    Results + Artifacts
```

The platform treats the LLM as an arbitrary code-execution agent while maintaining complete security isolation through containerization and strict resource controls.
