'use client'

import React, { useState, useEffect } from 'react'
import { GitBranch, GitCommit, GitMerge, Plus, Eye, Copy } from 'lucide-react'

interface Commit {
  sha: string
  message: string
  author: string
  timestamp: string
  branch: string[]
}

interface Branch {
  name: string
  commits: Commit[]
  head: string
}

interface VersionTreeProps {
  sessionId: string
  onCommitSelect?: (commitSha: string) => void
  onBranchFork?: (fromCommit: string, branchName: string) => void
}

export default function VersionTree({ sessionId, onCommitSelect, onBranchFork }: VersionTreeProps) {
  const [branches, setBranches] = useState<Record<string, Branch>>({})
  const [commits, setCommits] = useState<Commit[]>([])
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null)
  const [showForkDialog, setShowForkDialog] = useState(false)
  const [newBranchName, setNewBranchName] = useState('')
  const [forkFromCommit, setForkFromCommit] = useState('')

  useEffect(() => {
    if (sessionId) {
      fetchHistory()
      
      // Set up SSE for real-time updates
      const eventSource = new EventSource(`/api/stream/history/${sessionId}`)
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'commit') {
            setCommits(prev => {
              const exists = prev.find(c => c.sha === data.payload.sha)
              if (!exists) {
                return [data.payload, ...prev]
              }
              return prev
            })
          } else if (data.type === 'tree') {
            setBranches(data.payload.branches)
          }
        } catch (error) {
          console.error('Failed to parse history SSE:', error)
        }
      }

      return () => eventSource.close()
    }
  }, [sessionId])

  const fetchHistory = async () => {
    try {
      const response = await fetch(`/api/git/history/${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        setCommits(data.commits || [])
        setBranches(data.branches || {})
      }
    } catch (error) {
      console.error('Failed to fetch history:', error)
    }
  }

  const handleCommitClick = (commit: Commit) => {
    setSelectedCommit(commit.sha)
    onCommitSelect?.(commit.sha)
  }

  const handleForkBranch = (fromCommit: string) => {
    setForkFromCommit(fromCommit)
    setNewBranchName(`feature-${Date.now()}`)
    setShowForkDialog(true)
  }

  const confirmFork = async () => {
    if (!newBranchName.trim()) return

    try {
      const response = await fetch(`/api/stream/fork/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_commit: forkFromCommit,
          new_branch_name: newBranchName
        })
      })

      if (response.ok) {
        onBranchFork?.(forkFromCommit, newBranchName)
        setShowForkDialog(false)
        setNewBranchName('')
        fetchHistory() // Refresh
      }
    } catch (error) {
      console.error('Failed to fork branch:', error)
    }
  }

  const getCommitIcon = (commit: Commit) => {
    if (commit.branch.length > 1) {
      return <GitMerge className="w-4 h-4 text-purple-400" />
    }
    return <GitCommit className="w-4 h-4 text-cyan-400" />
  }

  const getBranchColor = (branchName: string) => {
    const colors = [
      'border-cyan-400 bg-cyan-500/20',
      'border-purple-400 bg-purple-500/20',
      'border-pink-400 bg-pink-500/20',
      'border-green-400 bg-green-500/20',
      'border-yellow-400 bg-yellow-500/20',
      'border-orange-400 bg-orange-500/20'
    ]
    const hash = branchName.split('').reduce((a, b) => a + b.charCodeAt(0), 0)
    return colors[hash % colors.length]
  }

  return (
    <div className="h-full flex flex-col bg-white/5 backdrop-blur-xl border border-white/20 rounded-2xl">
      {/* Header */}
      <div className="p-4 border-b border-white/20">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-cyan-400" />
          Version Tree
        </h3>
        <p className="text-sm text-gray-400 mt-1">
          {Object.keys(branches).length} branches • {commits.length} commits
        </p>
      </div>

      {/* Branch Overview */}
      <div className="p-4 border-b border-white/20">
        <div className="flex flex-wrap gap-2">
          {Object.entries(branches).map(([name, branch]) => (
            <div
              key={name}
              className={`px-3 py-1 rounded-full text-xs font-medium border ${getBranchColor(name)}`}
            >
              <GitBranch className="w-3 h-3 inline mr-1" />
              {name}
              <span className="ml-1 text-gray-400">({branch.commits.length})</span>
            </div>
          ))}
        </div>
      </div>

      {/* Commit History */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          {commits.map((commit, index) => (
            <div
              key={commit.sha}
              className={`relative flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer hover:bg-white/5 ${
                selectedCommit === commit.sha
                  ? 'border-cyan-400 bg-cyan-500/10'
                  : 'border-white/20 bg-black/20'
              }`}
              onClick={() => handleCommitClick(commit)}
            >
              {/* Timeline line */}
              {index < commits.length - 1 && (
                <div className="absolute left-6 top-12 w-px h-8 bg-white/20"></div>
              )}

              {/* Commit icon */}
              <div className="flex-shrink-0 mt-1">
                {getCommitIcon(commit)}
              </div>

              {/* Commit info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-white font-medium text-sm truncate">
                      {commit.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-400">
                        {commit.author}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(commit.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 mt-2">
                      {commit.branch.map(branchName => (
                        <span
                          key={branchName}
                          className={`px-2 py-1 rounded text-xs ${getBranchColor(branchName)}`}
                        >
                          {branchName}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 ml-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        navigator.clipboard.writeText(commit.sha)
                      }}
                      className="p-1 text-gray-400 hover:text-white transition-colors"
                      title="Copy SHA"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleForkBranch(commit.sha)
                      }}
                      className="p-1 text-gray-400 hover:text-cyan-400 transition-colors"
                      title="Fork from this commit"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* SHA */}
                <div className="mt-2">
                  <code className="text-xs text-gray-500 font-mono">
                    {commit.sha.slice(0, 8)}
                  </code>
                </div>
              </div>
            </div>
          ))}
        </div>

        {commits.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            <GitCommit className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No commits yet</p>
            <p className="text-sm">Start by running some code!</p>
          </div>
        )}
      </div>

      {/* Fork Dialog */}
      {showForkDialog && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-white/20 rounded-2xl p-6 w-96 shadow-2xl">
            <h3 className="text-lg font-semibold text-white mb-4">
              Create New Branch
            </h3>
            <p className="text-gray-400 text-sm mb-4">
              Fork from commit: <code className="text-cyan-400">{forkFromCommit.slice(0, 8)}</code>
            </p>
            <input
              type="text"
              value={newBranchName}
              onChange={(e) => setNewBranchName(e.target.value)}
              placeholder="Enter branch name..."
              className="w-full bg-black/30 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-gray-400 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all mb-4"
              autoFocus
            />
            <div className="flex gap-3">
              <button
                onClick={() => setShowForkDialog(false)}
                className="flex-1 px-4 py-2 bg-white/10 text-gray-300 rounded-xl hover:bg-white/20 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={confirmFork}
                disabled={!newBranchName.trim()}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-cyan-500 to-purple-500 text-white rounded-xl hover:from-cyan-600 hover:to-purple-600 disabled:opacity-50 transition-all"
              >
                Create Branch
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
