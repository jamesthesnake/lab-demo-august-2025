'use client'

import React, { useState, useEffect } from 'react'
import { Package, Plus, Trash2, Download, AlertCircle, CheckCircle } from 'lucide-react'

interface InstalledPackage {
  name: string
  version: string
  size?: string
}

interface PackageManagerProps {
  sessionId: string
}

export default function PackageManager({ sessionId }: PackageManagerProps) {
  const [packages, setPackages] = useState<InstalledPackage[]>([])
  const [newPackage, setNewPackage] = useState('')
  const [installing, setInstalling] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Fetch installed packages
  const fetchPackages = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/packages/${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        setPackages(data.packages || [])
      }
    } catch (err) {
      console.error('Failed to fetch packages:', err)
    } finally {
      setLoading(false)
    }
  }

  // Install a new package
  const installPackage = async () => {
    if (!newPackage.trim()) return

    setInstalling(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch(`http://localhost:8000/api/packages/${sessionId}/install`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ package: newPackage.trim() }),
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess(`Successfully installed ${newPackage}`)
        setNewPackage('')
        fetchPackages() // Refresh package list
      } else {
        setError(data.error || 'Failed to install package')
      }
    } catch (err) {
      setError('Network error occurred')
    } finally {
      setInstalling(false)
    }
  }

  // Uninstall a package
  const uninstallPackage = async (packageName: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/packages/${sessionId}/uninstall`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ package: packageName }),
      })

      if (response.ok) {
        setSuccess(`Successfully uninstalled ${packageName}`)
        fetchPackages() // Refresh package list
      } else {
        const data = await response.json()
        setError(data.error || 'Failed to uninstall package')
      }
    } catch (err) {
      setError('Network error occurred')
    }
  }

  useEffect(() => {
    fetchPackages()
  }, [sessionId])

  // Clear messages after 3 seconds
  useEffect(() => {
    if (success || error) {
      const timer = setTimeout(() => {
        setSuccess(null)
        setError(null)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [success, error])

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-gray-700">
        <Package className="w-5 h-5 text-blue-400" />
        <h3 className="font-semibold">Package Manager</h3>
        <span className="text-xs bg-gray-700 px-2 py-1 rounded">
          {packages.length} installed
        </span>
      </div>

      {/* Install new package */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={newPackage}
            onChange={(e) => setNewPackage(e.target.value)}
            placeholder="Package name (e.g., requests, numpy)"
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
            onKeyPress={(e) => e.key === 'Enter' && installPackage()}
            disabled={installing}
          />
          <button
            onClick={installPackage}
            disabled={installing || !newPackage.trim()}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium flex items-center gap-2"
          >
            {installing ? (
              <Download className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            {installing ? 'Installing...' : 'Install'}
          </button>
        </div>

        {/* Status messages */}
        {error && (
          <div className="mt-2 p-2 bg-red-900/50 border border-red-700 rounded text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {success && (
          <div className="mt-2 p-2 bg-green-900/50 border border-green-700 rounded text-sm flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-green-300">{success}</span>
          </div>
        )}
      </div>

      {/* Package list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-400">
            <Download className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading packages...
          </div>
        ) : packages.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
            <Package className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No packages installed</p>
            <p className="text-xs mt-1">Install packages to get started</p>
          </div>
        ) : (
          <div className="p-2">
            {packages.map((pkg) => (
              <div
                key={pkg.name}
                className="flex items-center justify-between p-3 hover:bg-gray-800 rounded group"
              >
                <div className="flex-1">
                  <div className="font-medium text-sm">{pkg.name}</div>
                  <div className="text-xs text-gray-400">
                    v{pkg.version}
                    {pkg.size && ` • ${pkg.size}`}
                  </div>
                </div>
                <button
                  onClick={() => uninstallPackage(pkg.name)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded transition-all"
                  title={`Uninstall ${pkg.name}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick install suggestions */}
      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-gray-400 mb-2">Quick Install:</div>
        <div className="flex flex-wrap gap-1">
          {['numpy', 'pandas', 'matplotlib', 'seaborn', 'requests', 'scikit-learn'].map((pkg) => (
            <button
              key={pkg}
              onClick={() => setNewPackage(pkg)}
              className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors"
            >
              {pkg}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
