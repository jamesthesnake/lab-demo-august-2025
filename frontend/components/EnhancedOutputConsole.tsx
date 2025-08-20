'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Copy, Download, Search, X, ChevronDown, ChevronUp } from 'lucide-react'

interface EnhancedOutputConsoleProps {
  output: string
  isExecuting?: boolean
}

export default function EnhancedOutputConsole({ output, isExecuting = false }: EnhancedOutputConsoleProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const outputRef = useRef<HTMLPreElement>(null)

  // Auto-scroll to bottom when new output arrives
  useEffect(() => {
    if (outputRef.current && !isCollapsed) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [output, isCollapsed])

  // Copy output to clipboard
  const copyOutput = async () => {
    try {
      await navigator.clipboard.writeText(output)
    } catch (err) {
      console.error('Failed to copy output:', err)
    }
  }

  // Download output as text file
  const downloadOutput = () => {
    const blob = new Blob([output], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aido_lab_output_${Date.now()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Highlight search terms in output
  const highlightSearchTerm = (text: string) => {
    if (!searchTerm) return text
    
    const regex = new RegExp(`(${searchTerm})`, 'gi')
    return text.replace(regex, '<mark class="bg-yellow-400 text-black">$1</mark>')
  }

  const displayOutput = output || `# Console Output
# Ready for code execution...
# 
# Tips:
# - Use print() to see output
# - Variables persist between executions
# - Import libraries as needed
# - Plots will auto-save and appear in Plots & Tables panel`

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-700 bg-gray-800">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 text-gray-400 hover:text-white rounded transition-colors"
          >
            {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
          <span className="text-sm font-medium text-gray-300">Output Console</span>
          {isExecuting && (
            <div className="flex items-center gap-1 text-xs text-yellow-400">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
              Running...
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowSearch(!showSearch)}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Search output"
          >
            <Search className="w-4 h-4" />
          </button>
          <button
            onClick={copyOutput}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Copy output"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={downloadOutput}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Download output"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search bar */}
      {showSearch && (
        <div className="p-3 border-b border-gray-700 bg-gray-800">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search in output..."
              className="flex-1 px-3 py-1 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={() => {
                setSearchTerm('')
                setShowSearch(false)
              }}
              className="p-1 text-gray-400 hover:text-white rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Output content */}
      {!isCollapsed && (
        <div className="flex-1 p-4">
          <pre
            ref={outputRef}
            className="w-full h-full p-4 bg-black/20 border border-white/10 rounded-xl text-amber-300 overflow-auto text-sm font-mono shadow-inner leading-relaxed"
            dangerouslySetInnerHTML={{
              __html: highlightSearchTerm(displayOutput)
            }}
          />
        </div>
      )}

      {/* Collapsed state */}
      {isCollapsed && (
        <div className="p-4 text-center text-gray-400">
          <div className="text-sm">Console collapsed</div>
          <div className="text-xs mt-1">Click to expand</div>
        </div>
      )}
    </div>
  )
}
