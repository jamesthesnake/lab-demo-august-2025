'use client'

import React, { useState, useEffect } from 'react'
import { GitCommit, GitBranch } from 'lucide-react'

interface Commit {
  sha: string
  message: string
  author?: string
  timestamp: string
}

interface SimpleVersionTreeProps {
  sessionId: string
  currentBranch?: string
}

export default function SimpleVersionTree({ sessionId, currentBranch }: SimpleVersionTreeProps) {
  const [commits, setCommits] = useState<Commit[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (sessionId) {
      fetchHistory()
      
      // Listen for git history updates from manual commits
      const handleGitUpdate = () => {
        fetchHistory()
      }
      
      window.addEventListener('gitHistoryUpdate', handleGitUpdate)
      return () => window.removeEventListener('gitHistoryUpdate', handleGitUpdate)
    }
  }, [sessionId, currentBranch])

  const fetchHistory = async () => {
    if (!sessionId) return
    
    setLoading(true)
    try {
      // Add branch parameter if specified
      const url = currentBranch 
        ? `http://localhost:8000/api/git/sessions/${sessionId}/history?branch=${currentBranch}`
        : `http://localhost:8000/api/git/sessions/${sessionId}/history`
      
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setCommits(data.commits || [])
      }
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString()
    } catch {
      return timestamp
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-cyan-400" />
          Version Tree
          {currentBranch && (
            <span className="text-xs bg-cyan-600/20 text-cyan-400 px-2 py-1 rounded">
              {currentBranch}
            </span>
          )}
        </h3>
        <span className="text-xs text-slate-400">
          {commits.length} {commits.length === 1 ? 'commit' : 'commits'}
        </span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
          </div>
        ) : commits.length === 0 ? (
          <div className="text-center py-8">
            <GitCommit className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400 text-sm">No commits yet</p>
            <p className="text-slate-500 text-xs mt-1">Start by running some code!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {commits.map((commit, index) => (
              <div
                key={commit.sha}
                className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-slate-600/50 transition-colors"
              >
                <div className="flex-shrink-0 mt-1">
                  <GitCommit className="w-4 h-4 text-cyan-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-slate-300 bg-slate-700/50 px-2 py-1 rounded">
                      {commit.sha.slice(0, 8)}
                    </span>
                    {index === 0 && (
                      <span className="text-xs bg-cyan-600/20 text-cyan-400 px-2 py-1 rounded">
                        HEAD
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-white mb-1 line-clamp-2">
                    {commit.message || 'No commit message'}
                  </p>
                  <p className="text-xs text-slate-400">
                    {formatTimestamp(commit.timestamp)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
