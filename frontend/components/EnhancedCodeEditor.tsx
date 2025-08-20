'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Play, Download, Upload, Copy, RotateCcw, Save } from 'lucide-react'

interface EnhancedCodeEditorProps {
  code: string
  onChange: (code: string) => void
  onExecute: () => void
  isExecuting?: boolean
  onSave?: () => void
  isSaving?: boolean
}

export default function EnhancedCodeEditor({ 
  code, 
  onChange, 
  onExecute, 
  isExecuting = false,
  onSave,
  isSaving = false
}: EnhancedCodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [lineNumbers, setLineNumbers] = useState<number[]>([])

  // Update line numbers when code changes
  useEffect(() => {
    const lines = code.split('\n').length
    setLineNumbers(Array.from({ length: lines }, (_, i) => i + 1))
  }, [code])

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl/Cmd + Enter to execute
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      onExecute()
    }
    
    // Ctrl/Cmd + S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault()
      onSave?.()
    }

    // Tab for indentation
    if (e.key === 'Tab') {
      e.preventDefault()
      const textarea = textareaRef.current
      if (!textarea) return

      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const newCode = code.substring(0, start) + '    ' + code.substring(end)
      onChange(newCode)
      
      // Restore cursor position
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 4
      }, 0)
    }
  }

  // Copy code to clipboard
  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code)
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }

  // Download code as .py file
  const downloadCode = () => {
    const blob = new Blob([code], { type: 'text/python' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aido_lab_${Date.now()}.py`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Upload code from file
  const uploadCode = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.py,.txt'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        const reader = new FileReader()
        reader.onload = (e) => {
          const content = e.target?.result as string
          onChange(content)
        }
        reader.readAsText(file)
      }
    }
    input.click()
  }

  // Clear code
  const clearCode = () => {
    onChange('# Start coding here...\n')
  }

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-gray-700 bg-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-300">Python Editor</span>
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <kbd className="px-1.5 py-0.5 bg-gray-700 rounded text-xs">Ctrl+Enter</kbd>
            <span>to run</span>
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={copyCode}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Copy code"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={downloadCode}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Download as .py file"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={uploadCode}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Upload .py file"
          >
            <Upload className="w-4 h-4" />
          </button>
          <button
            onClick={clearCode}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Clear code"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          {onSave && (
            <button
              onClick={onSave}
              disabled={isSaving}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
              title="Save to git (Ctrl+S)"
            >
              <Save className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 flex relative">
        {/* Line numbers */}
        <div className="w-12 bg-gray-800 border-r border-gray-700 py-4 text-right text-xs text-gray-500 font-mono select-none">
          {lineNumbers.map(num => (
            <div key={num} className="px-2 leading-6 h-6">
              {num}
            </div>
          ))}
        </div>

        {/* Code textarea */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={code}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full h-full p-4 bg-transparent text-white font-mono text-sm leading-6 resize-none focus:outline-none"
            style={{
              lineHeight: '1.5rem',
              tabSize: 4,
            }}
            placeholder="# Start coding here...
import pandas as pd
import matplotlib.pyplot as plt

# Your Python code here"
            spellCheck={false}
          />
          
          {/* Syntax highlighting overlay would go here */}
          <div className="absolute inset-0 pointer-events-none">
            {/* This is where we could add syntax highlighting */}
          </div>
        </div>
      </div>

      {/* Execute button */}
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={onExecute}
          disabled={isExecuting}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors"
        >
          {isExecuting ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Execute Code
            </>
          )}
        </button>
        
        {/* Shortcuts hint */}
        <div className="mt-2 text-xs text-gray-400 text-center">
          <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-xs mr-1">Ctrl+Enter</kbd>
          to execute •
          <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-xs mx-1">Ctrl+S</kbd>
          to save •
          <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-xs ml-1">Tab</kbd>
          to indent
        </div>
      </div>
    </div>
  )
}
