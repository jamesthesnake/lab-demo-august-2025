'use client'

import React, { useState, useEffect } from 'react'
import { Play, Save, FileCode, Copy, Download } from 'lucide-react'

interface CodeEditorProps {
  code: string
  onChange: (code: string) => void
  onExecute?: () => void
  isExecuting?: boolean
  language?: string
}

export default function CodeEditor({ 
  code, 
  onChange, 
  onExecute, 
  isExecuting = false,
  language = 'python' 
}: CodeEditorProps) {
  const [localCode, setLocalCode] = useState(code)

  useEffect(() => {
    setLocalCode(code)
  }, [code])

  const handleCodeChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newCode = e.target.value
    setLocalCode(newCode)
    onChange(newCode)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      const textarea = e.target as HTMLTextAreaElement
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const newCode = localCode.substring(0, start) + '    ' + localCode.substring(end)
      setLocalCode(newCode)
      onChange(newCode)
      
      // Set cursor position after the inserted tab
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 4
      }, 0)
    } else if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault()
      onExecute?.()
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(localCode)
  }

  const downloadCode = () => {
    const blob = new Blob([localCode], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `code.${language}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const lineCount = localCode.split('\n').length

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/20">
        <div className="flex items-center gap-2">
          <FileCode className="w-5 h-5 text-green-400" />
          <h3 className="text-lg font-semibold text-white">Code Editor</h3>
          <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs font-medium">
            {language.toUpperCase()}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {onExecute && (
            <button
              onClick={onExecute}
              disabled={isExecuting}
              className="px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg hover:from-green-600 hover:to-emerald-600 disabled:opacity-50 font-bold shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 text-sm"
            >
              <Play className="w-5 h-5" />
              {isExecuting ? 'Running...' : 'Run Code'}
            </button>
          )}
          <div className="w-px h-6 bg-white/20"></div>
          <button
            onClick={copyToClipboard}
            className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/10"
            title="Copy code"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={downloadCode}
            className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/10"
            title="Download code"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 flex">
        {/* Line numbers */}
        <div className="bg-black/20 border-r border-white/20 p-4 text-right text-gray-500 text-sm font-mono select-none">
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i + 1} className="leading-6">
              {i + 1}
            </div>
          ))}
        </div>

        {/* Code area */}
        <div className="flex-1 relative">
          <textarea
            value={localCode}
            onChange={handleCodeChange}
            onKeyDown={handleKeyDown}
            className="w-full h-full p-4 bg-transparent text-white font-mono text-sm leading-6 resize-none focus:outline-none"
            placeholder="# Write your Python code here..."
            spellCheck={false}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/20 bg-black/20">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <span>{lineCount} lines</span>
            <span>{localCode.length} characters</span>
          </div>
          <div className="text-gray-500">
            Press Ctrl+Enter to run • Tab for indentation
          </div>
        </div>
      </div>
    </div>
  )
}
