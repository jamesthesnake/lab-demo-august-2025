'use client'

import { useState } from 'react'
import { GitBranch, Save, X, MessageSquare } from 'lucide-react'

interface GitCommitPanelProps {
  sessionId: string
  currentBranch: string
  code: string
  onCommit: (message: string, description?: string) => Promise<void>
  isCommitting: boolean
}

export default function GitCommitPanel({ 
  sessionId, 
  currentBranch, 
  code, 
  onCommit, 
  isCommitting 
}: GitCommitPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [commitMessage, setCommitMessage] = useState('')
  const [commitDescription, setCommitDescription] = useState('')

  const handleCommit = async () => {
    if (!commitMessage.trim()) return
    
    try {
      await onCommit(commitMessage, commitDescription || undefined)
      setCommitMessage('')
      setCommitDescription('')
      setIsOpen(false)
    } catch (error) {
      console.error('Commit failed:', error)
    }
  }

  const handleCancel = () => {
    setCommitMessage('')
    setCommitDescription('')
    setIsOpen(false)
  }

  const generateSuggestion = () => {
    const lines = code.trim().split('\n')
    const firstLine = lines[0]?.trim() || ""
    
    // Generate message based on code patterns
    if (code.includes('plt.') || code.includes('matplotlib')) {
      setCommitMessage("Create data visualization")
    } else if (code.includes('pd.') || code.includes('pandas')) {
      if (code.includes('.read_')) {
        setCommitMessage("Load and analyze data")
      } else if (code.includes('.plot') || code.includes('.hist')) {
        setCommitMessage("Generate data plots")
      } else {
        setCommitMessage("Process data with pandas")
      }
    } else if (code.includes('np.') || code.includes('numpy')) {
      setCommitMessage("Perform numerical computation")
    } else if (code.includes('def ')) {
      const funcMatch = code.match(/def\s+(\w+)\s*\(/);
      const funcName = funcMatch ? funcMatch[1] : '';
      setCommitMessage(funcName ? `Define function: ${funcName}` : "Define new function")
    } else if (code.includes('class ')) {
      const classMatch = code.match(/class\s+(\w+)[\s\(:]/);
      const className = classMatch ? classMatch[1] : '';
      setCommitMessage(className ? `Create class: ${className}` : "Create new class")
    } else if (code.includes('print(')) {
      setCommitMessage("Display output")
    } else {
      setCommitMessage("Update code")
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        disabled={!code.trim() || isCommitting}
        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500/20 to-emerald-500/20 
                   hover:from-green-500/30 hover:to-emerald-500/30 border border-green-500/30 
                   rounded-lg text-green-300 transition-all duration-200 disabled:opacity-50 
                   disabled:cursor-not-allowed"
      >
        <Save className="w-4 h-4" />
        {isCommitting ? 'Committing...' : 'Commit Changes'}
      </button>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800/90 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <GitBranch className="w-5 h-5 text-green-400" />
            <h3 className="text-lg font-semibold text-white">Commit Changes</h3>
          </div>
          <button
            onClick={handleCancel}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Branch Info */}
          <div className="flex items-center gap-2 text-sm text-gray-300">
            <span>Branch:</span>
            <span className="px-2 py-1 bg-cyan-500/20 rounded text-cyan-300 font-mono">
              {currentBranch}
            </span>
          </div>

          {/* Commit Message */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">
                Commit Message *
              </label>
              <button
                onClick={generateSuggestion}
                className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
              >
                Generate suggestion
              </button>
            </div>
            <input
              type="text"
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              placeholder="Brief description of changes..."
              className="w-full px-3 py-2 bg-slate-700/50 border border-white/10 rounded-lg 
                         text-white placeholder-gray-400 focus:outline-none focus:ring-2 
                         focus:ring-green-500/50 focus:border-green-500/50"
              maxLength={72}
            />
            <div className="text-xs text-gray-400 text-right">
              {commitMessage.length}/72
            </div>
          </div>

          {/* Commit Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Description (optional)
            </label>
            <textarea
              value={commitDescription}
              onChange={(e) => setCommitDescription(e.target.value)}
              placeholder="Detailed explanation of what changed and why..."
              rows={3}
              className="w-full px-3 py-2 bg-slate-700/50 border border-white/10 rounded-lg 
                         text-white placeholder-gray-400 focus:outline-none focus:ring-2 
                         focus:ring-green-500/50 focus:border-green-500/50 resize-none"
              maxLength={500}
            />
            <div className="text-xs text-gray-400 text-right">
              {commitDescription.length}/500
            </div>
          </div>

          {/* Code Preview */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">
              Code Preview
            </label>
            <div className="bg-slate-900/50 border border-white/10 rounded-lg p-3 max-h-32 overflow-y-auto">
              <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                {code.slice(0, 200)}{code.length > 200 ? '...' : ''}
              </pre>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-white/10">
          <button
            onClick={handleCancel}
            disabled={isCommitting}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleCommit}
            disabled={!commitMessage.trim() || isCommitting}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 
                       hover:from-green-600 hover:to-emerald-600 text-white rounded-lg 
                       transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            {isCommitting ? 'Committing...' : 'Commit'}
          </button>
        </div>
      </div>
    </div>
  )
}
