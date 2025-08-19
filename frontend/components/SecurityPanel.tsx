'use client'

import React, { useState, useEffect } from 'react'
import { Shield, AlertTriangle, Server, Clock, Zap } from 'lucide-react'

interface SecurityStatus {
  status: string
  active_containers: number
  docker_available: boolean
  security_features: {
    seccomp: boolean
    apparmor: boolean
    read_only_rootfs: boolean
    network_isolation: boolean
    resource_limits: boolean
    timeout_enforcement: boolean
  }
}

interface ContainerInfo {
  [key: string]: {
    status: string
    created: string
    session?: string
  }
}

export default function SecurityPanel() {
  const [securityStatus, setSecurityStatus] = useState<SecurityStatus | null>(null)
  const [containers, setContainers] = useState<ContainerInfo>({})
  const [showPanicConfirm, setShowPanicConfirm] = useState(false)
  const [loading, setLoading] = useState(false)

  const fetchSecurityStatus = async () => {
    // Only run on client side
    if (typeof window === 'undefined') return
    
    try {
      const response = await fetch('/api/security/health')
      if (response.ok) {
        const data = await response.json()
        setSecurityStatus(data)
      }
    } catch (error) {
      console.error('Failed to fetch security status:', error)
      // Set default status on error
      setSecurityStatus({
        status: 'unknown',
        active_containers: 0,
        docker_available: false,
        security_features: {
          seccomp: false,
          apparmor: false,
          read_only_rootfs: false,
          network_isolation: false,
          resource_limits: false,
          timeout_enforcement: false
        }
      })
    }
  }

  const fetchContainers = async () => {
    // Only run on client side
    if (typeof window === 'undefined') return
    
    try {
      const response = await fetch('/api/security/containers')
      if (response.ok) {
        const data = await response.json()
        setContainers(data.active_containers || {})
      }
    } catch (error) {
      console.error('Failed to fetch containers:', error)
      setContainers({})
    }
  }

  const handlePanicButton = async () => {
    if (!showPanicConfirm) {
      setShowPanicConfirm(true)
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/security/panic', { method: 'POST' })
      const result = await response.json()
      
      if (response.ok) {
        alert(`Panic button activated! Killed ${result.containers_killed} containers.`)
        await fetchContainers()
      } else {
        alert('Panic button failed: ' + result.detail)
      }
    } catch (error) {
      alert('Panic button error: ' + error)
    } finally {
      setLoading(false)
      setShowPanicConfirm(false)
    }
  }

  const killContainer = async (containerId: string) => {
    if (!confirm(`Kill container ${containerId.slice(0, 12)}?`)) return

    try {
      const response = await fetch(`/api/security/containers/${containerId}`, { 
        method: 'DELETE' 
      })
      
      if (response.ok) {
        await fetchContainers()
      } else {
        const error = await response.json()
        alert('Failed to kill container: ' + error.detail)
      }
    } catch (error) {
      alert('Error killing container: ' + error)
    }
  }

  useEffect(() => {
    // Only fetch on client-side
    if (typeof window !== 'undefined') {
      fetchSecurityStatus()
      fetchContainers()
      
      // Refresh every 5 seconds
      const interval = setInterval(() => {
        fetchSecurityStatus()
        fetchContainers()
      }, 5000)

      return () => clearInterval(interval)
    }
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600'
      case 'unhealthy': return 'text-red-600'
      default: return 'text-yellow-600'
    }
  }

  const getFeatureIcon = (enabled: boolean) => {
    return enabled ? '✅' : '❌'
  }

  return (
    <div className="backdrop-blur-xl bg-white/5 border border-white/20 rounded-2xl p-6 space-y-4 text-white">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2 text-white">
          <Shield className="w-5 h-5 text-cyan-400" />
          Security Status
        </h3>
        
        {/* Panic Button */}
        <div className="flex gap-2">
          {showPanicConfirm ? (
            <>
              <button
                onClick={() => setShowPanicConfirm(false)}
                className="px-3 py-1 text-sm bg-white/10 text-gray-300 rounded-lg hover:bg-white/20 border border-white/20 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handlePanicButton}
                disabled={loading}
                className="px-3 py-1 text-sm bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 disabled:opacity-50 shadow-lg transition-all"
              >
                {loading ? 'Killing...' : 'CONFIRM KILL ALL'}
              </button>
            </>
          ) : (
            <button
              onClick={handlePanicButton}
              className="px-4 py-2 text-sm bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 flex items-center gap-2 shadow-lg hover:shadow-red-500/25 transition-all duration-300 transform hover:scale-105 font-semibold"
            >
              <AlertTriangle className="w-4 h-4" />
              PANIC
            </button>
          )}
        </div>
      </div>

      {/* Security Status */}
      {securityStatus && (
        <div className="space-y-3">
          <div className="flex items-center justify-between bg-black/20 rounded-lg p-3 border border-white/10">
            <span className="font-medium text-gray-300">System Status:</span>
            <span className={`font-semibold px-3 py-1 rounded-full text-sm ${getStatusColor(securityStatus.status)} ${securityStatus.status === 'healthy' ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
              {securityStatus.status.toUpperCase()}
            </span>
          </div>

          <div className="flex items-center justify-between bg-black/20 rounded-lg p-3 border border-white/10">
            <span className="font-medium text-gray-300">Active Containers:</span>
            <span className="font-semibold text-cyan-400 bg-cyan-500/20 px-3 py-1 rounded-full text-sm">
              {securityStatus.active_containers}
            </span>
          </div>

          <div className="flex items-center justify-between bg-black/20 rounded-lg p-3 border border-white/10">
            <span className="font-medium text-gray-300">Docker Available:</span>
            <span className={`font-semibold px-3 py-1 rounded-full text-sm ${securityStatus.docker_available ? 'text-green-400 bg-green-500/20' : 'text-red-400 bg-red-500/20'}`}>
              {securityStatus.docker_available ? 'Yes' : 'No'}
            </span>
          </div>

          {/* Security Features */}
          <div className="border-t border-white/20 pt-4">
            <h4 className="font-medium mb-3 text-white">Security Features:</h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between bg-black/20 rounded-lg p-2 border border-white/10">
                <span className="text-gray-300">Seccomp:</span>
                <span>{getFeatureIcon(securityStatus.security_features.seccomp)}</span>
              </div>
              <div className="flex justify-between bg-black/20 rounded-lg p-2 border border-white/10">
                <span className="text-gray-300">AppArmor:</span>
                <span>{getFeatureIcon(securityStatus.security_features.apparmor)}</span>
              </div>
              <div className="flex justify-between bg-black/20 rounded-lg p-2 border border-white/10">
                <span className="text-gray-300">Read-only FS:</span>
                <span>{getFeatureIcon(securityStatus.security_features.read_only_rootfs)}</span>
              </div>
              <div className="flex justify-between bg-black/20 rounded-lg p-2 border border-white/10">
                <span className="text-gray-300">Network Isolation:</span>
                <span>{getFeatureIcon(securityStatus.security_features.network_isolation)}</span>
              </div>
              <div className="flex justify-between bg-black/20 rounded-lg p-2 border border-white/10">
                <span className="text-gray-300">Resource Limits:</span>
                <span>{getFeatureIcon(securityStatus.security_features.resource_limits)}</span>
              </div>
              <div className="flex justify-between bg-black/20 rounded-lg p-2 border border-white/10">
                <span className="text-gray-300">Timeout Control:</span>
                <span>{getFeatureIcon(securityStatus.security_features.timeout_enforcement)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Active Containers */}
      {Object.keys(containers).length > 0 && (
        <div className="border-t border-white/20 pt-4">
          <h4 className="font-medium mb-3 flex items-center gap-2 text-white">
            <Server className="w-4 h-4 text-purple-400" />
            Active Containers:
          </h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {Object.entries(containers).map(([id, info]) => (
              <div key={id} className="flex items-center justify-between text-sm bg-black/30 p-3 rounded-xl border border-white/10">
                <div>
                  <div className="font-mono text-xs text-cyan-300">
                    {id.slice(0, 12)}
                  </div>
                  <div className="text-xs text-gray-400">
                    Session: {info.session || 'unknown'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    info.status === 'running' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {info.status}
                  </span>
                  <button
                    onClick={() => killContainer(id)}
                    className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 border border-red-500/30 transition-all"
                  >
                    Kill
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security Indicators */}
      <div className="border-t border-white/20 pt-4">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-1 bg-black/20 px-2 py-1 rounded-lg">
            <Clock className="w-3 h-3 text-yellow-400" />
            30s timeout
          </div>
          <div className="flex items-center gap-1 bg-black/20 px-2 py-1 rounded-lg">
            <Zap className="w-3 h-3 text-orange-400" />
            512MB limit
          </div>
          <div className="flex items-center gap-1 bg-black/20 px-2 py-1 rounded-lg">
            <Shield className="w-3 h-3 text-green-400" />
            Sandboxed
          </div>
        </div>
      </div>
    </div>
  )
}
