'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Terminal, Copy, Trash2, Download, AlertCircle, CheckCircle } from 'lucide-react'

interface OutputEntry {
  id: string
  type: 'stdout' | 'stderr' | 'info' | 'error' | 'success'
  content: string
  timestamp: Date
}

interface OutputConsoleProps {
  output?: string
  error?: string
  isExecuting?: boolean
  onClear?: () => void
}

export default function OutputConsole({ 
  output = '', 
  error = '', 
  isExecuting = false,
  onClear 
}: OutputConsoleProps) {
  const [entries, setEntries] = useState<OutputEntry[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (output) {
      const newEntry: OutputEntry = {
        id: Date.now().toString(),
        type: 'stdout',
        content: output,
        timestamp: new Date()
      }
      setEntries(prev => [...prev, newEntry])
    }
  }, [output])

  useEffect(() => {
    if (error) {
      const newEntry: OutputEntry = {
        id: Date.now().toString(),
        type: 'stderr',
        content: error,
        timestamp: new Date()
      }
      setEntries(prev => [...prev, newEntry])
    }
  }, [error])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [entries])

  const clearConsole = () => {
    setEntries([])
    onClear?.()
  }

  const copyOutput = () => {
    const allOutput = entries.map(entry => 
      `[${entry.timestamp.toLocaleTimeString()}] ${entry.content}`
    ).join('\n')
    navigator.clipboard.writeText(allOutput)
  }

  const downloadOutput = () => {
    const allOutput = entries.map(entry => 
      `[${entry.timestamp.toLocaleTimeString()}] ${entry.content}`
    ).join('\n')
    const blob = new Blob([allOutput], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'output.txt'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getEntryIcon = (type: string) => {
    switch (type) {
      case 'stderr':
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      default:
        return <Terminal className="w-4 h-4 text-cyan-400" />
    }
  }

  const getEntryColor = (type: string) => {
    switch (type) {
      case 'stderr':
      case 'error':
        return 'text-red-300 bg-red-900/20 border-red-500/30'
      case 'success':
        return 'text-green-300 bg-green-900/20 border-green-500/30'
      case 'info':
        return 'text-blue-300 bg-blue-900/20 border-blue-500/30'
      default:
        return 'text-gray-300 bg-black/20 border-white/20'
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/20">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-cyan-400" />
          <h3 className="text-lg font-semibold text-white">Output Console</h3>
          {isExecuting && (
            <div className="flex items-center gap-2 text-yellow-400">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
              <span className="text-sm">Running...</span>
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={copyOutput}
            disabled={entries.length === 0}
            className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/10 disabled:opacity-50"
            title="Copy output"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={downloadOutput}
            disabled={entries.length === 0}
            className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/10 disabled:opacity-50"
            title="Download output"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={clearConsole}
            disabled={entries.length === 0}
            className="p-2 text-gray-400 hover:text-red-400 transition-colors rounded-lg hover:bg-red-500/10 disabled:opacity-50"
            title="Clear console"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Console Output */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm"
      >
        {entries.length === 0 && !isExecuting ? (
          <div className="text-center py-8 text-gray-400">
            <Terminal className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No output yet</p>
            <p className="text-sm">Run some code to see results here</p>
          </div>
        ) : (
          <div className="space-y-2">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className={`p-3 rounded-lg border ${getEntryColor(entry.type)}`}
              >
                <div className="flex items-start gap-2">
                  {getEntryIcon(entry.type)}
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs opacity-70">
                        {entry.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <pre className="whitespace-pre-wrap break-words">
                      {entry.content}
                    </pre>
                  </div>
                </div>
              </div>
            ))}
            
            {isExecuting && (
              <div className="p-3 rounded-lg border border-yellow-500/30 bg-yellow-900/20 text-yellow-300">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin"></div>
                  <span>Executing code...</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/20 bg-black/20">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <span>{entries.length} entries</span>
            {entries.length > 0 && (
              <span>
                Last: {entries[entries.length - 1]?.timestamp.toLocaleTimeString()}
              </span>
            )}
          </div>
          <div className="text-gray-500">
            Auto-scroll enabled
          </div>
        </div>
      </div>
    </div>
  )
}
