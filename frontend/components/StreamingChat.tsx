'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Send, Code, Play, GitBranch, FileText, Image, AlertCircle } from 'lucide-react'

interface StreamEvent {
  type: string
  payload: any
}

interface StreamingChatProps {
  sessionId: string
  onCodeGenerated?: (code: string, autoExecute?: boolean) => void
}

export default function StreamingChat({ sessionId, onCodeGenerated }: StreamingChatProps) {
  const [messages, setMessages] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentResponse, setCurrentResponse] = useState<any>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Extract code blocks from markdown text
  const extractCodeFromText = (text: string): string | null => {
    // Look for Python code blocks
    const pythonCodeMatch = text.match(/```(?:python|py)?\n([\s\S]*?)\n```/i)
    if (pythonCodeMatch) {
      return pythonCodeMatch[1].trim()
    }
    
    // Look for any code blocks
    const codeMatch = text.match(/```\n?([\s\S]*?)\n?```/)
    if (codeMatch) {
      return codeMatch[1].trim()
    }
    
    // Look for inline code that looks like Python
    const inlineMatch = text.match(/`([^`]*(?:import|def|print|pandas|numpy|plt)[^`]*)`/)
    if (inlineMatch) {
      return inlineMatch[1].trim()
    }
    
    return null
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentResponse])

  const handleSendMessage = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)
    setCurrentResponse({
      id: Date.now() + 1,
      type: 'assistant',
      content: '',
      code: '',
      result: null,
      artifacts: [],
      branch: null,
      commit: null,
      timestamp: new Date().toISOString()
    })

    // Start SSE stream via POST request
    try {
      const response = await fetch(`/api/stream/chat/${sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input })
      })

      if (!response.ok) {
        throw new Error('Failed to start stream')
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: StreamEvent = JSON.parse(line.slice(6))
              
              setCurrentResponse(prev => {
                const updated = { ...prev }
                
                switch (data.type) {
                  case 'text':
                    updated.content += data.payload
                    break
                  
                  case 'code':
                    updated.code = data.payload
                    // Trigger code generation callback
                    if (onCodeGenerated && data.payload) {
                      onCodeGenerated(data.payload, false)
                    }
                    break
                  
                  case 'result':
                    updated.result = data.payload
                    break
                  
                  case 'artifact':
                    updated.artifacts = [...(updated.artifacts || []), data.payload]
                    break
                  
                  case 'commit':
                    updated.commit = data.payload.sha
                    updated.branch = data.payload.branch
                    break
                  
                  case 'thinking':
                  case 'executing':
                    updated.status = data.payload
                    break
                  
                  case 'complete':
                    // Move current response to messages
                    setMessages(prev => [...prev, updated])
                    setCurrentResponse({})
                    setIsStreaming(false)
                    return updated
                  
                  case 'error':
                    updated.error = data.payload
                    setIsStreaming(false)
                    return updated
                }
                
                return updated
              })
            } catch (error) {
              console.error('Failed to parse SSE data:', error)
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error)
      setIsStreaming(false)
    }
  }

  const renderMessage = (message: any) => {
    if (message.type === 'user') {
      return (
        <div key={message.id} className="flex justify-end mb-4">
          <div className="bg-gradient-to-r from-cyan-500 to-purple-500 text-white rounded-2xl px-4 py-2 max-w-xs lg:max-w-md shadow-lg">
            <p className="text-sm">{message.content}</p>
          </div>
        </div>
      )
    }

    return (
      <div key={message.id} className="flex justify-start mb-6">
        <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-4 max-w-full shadow-2xl">
          {/* Text Response */}
          {message.content && (
            <div className="text-white mb-3">
              <div className="prose prose-invert max-w-none">
                {message.content.split('\n').map((line, i) => (
                  <p key={i} className="mb-2">{line}</p>
                ))}
              </div>
              
              {/* Smart Code Detection */}
              {!message.code && extractCodeFromText(message.content) && (
                <div className="mt-3 p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Code className="w-4 h-4 text-cyan-400" />
                      <span className="text-sm text-cyan-400 font-medium">Code detected in response</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => onCodeGenerated?.(extractCodeFromText(message.content)!, false)}
                        className="px-2 py-1 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-300 rounded text-xs font-medium transition-all duration-200 flex items-center gap-1"
                        title="Extract and insert code"
                      >
                        <Code className="w-3 h-3" />
                        Extract
                      </button>
                      <button
                        onClick={() => onCodeGenerated?.(extractCodeFromText(message.content)!, true)}
                        className="px-2 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 rounded text-xs font-medium transition-all duration-200 flex items-center gap-1"
                        title="Extract and run code"
                      >
                        <Play className="w-3 h-3" />
                        Run
                      </button>
                    </div>
                  </div>
                  <pre className="text-xs text-cyan-300 bg-black/20 rounded p-2 overflow-x-auto">
                    <code>{extractCodeFromText(message.content)}</code>
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Code Block */}
          {message.code && (
            <div className="mb-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Code className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm text-cyan-400 font-semibold">Generated Code</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => onCodeGenerated?.(message.code, false)}
                    className="px-3 py-1 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-300 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1"
                    title="Insert code into editor"
                  >
                    <Code className="w-3 h-3" />
                    Insert
                  </button>
                  <button
                    onClick={() => onCodeGenerated?.(message.code, true)}
                    className="px-3 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1"
                    title="Insert and execute code"
                  >
                    <Play className="w-3 h-3" />
                    Run
                  </button>
                </div>
              </div>
              <pre className="bg-black/40 border border-white/20 rounded-xl p-3 text-green-300 text-sm overflow-x-auto">
                <code>{message.code}</code>
              </pre>
            </div>
          )}

          {/* Execution Result */}
          {message.result && (
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-2">
                <Play className="w-4 h-4 text-yellow-400" />
                <span className="text-sm text-yellow-400 font-semibold">Execution Result</span>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  message.result.status === 'ok' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {message.result.status}
                </span>
              </div>
              
              {message.result.stdout && (
                <pre className="bg-black/40 border border-white/20 rounded-xl p-3 text-green-300 text-sm mb-2 overflow-x-auto">
                  {message.result.stdout}
                </pre>
              )}
              
              {message.result.stderr && (
                <pre className="bg-red-900/20 border border-red-500/30 rounded-xl p-3 text-red-300 text-sm overflow-x-auto">
                  {message.result.stderr}
                </pre>
              )}
            </div>
          )}

          {/* Artifacts */}
          {message.artifacts && message.artifacts.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-2">
                <Image className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-purple-400 font-semibold">Generated Artifacts</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {message.artifacts.map((artifact, i) => (
                  <div key={i} className="bg-black/20 border border-white/20 rounded-lg p-2">
                    <a 
                      href={artifact.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 text-sm flex items-center gap-1"
                    >
                      <FileText className="w-3 h-3" />
                      {artifact.path.split('/').pop()}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Git Info */}
          {message.commit && (
            <div className="flex items-center gap-2 text-xs text-gray-400 bg-black/20 rounded-lg p-2">
              <GitBranch className="w-3 h-3" />
              <span>Branch: {message.branch}</span>
              <span>•</span>
              <span>Commit: {message.commit.slice(0, 8)}</span>
            </div>
          )}

          {/* Error */}
          {message.error && (
            <div className="flex items-center gap-2 text-red-400 bg-red-900/20 border border-red-500/30 rounded-lg p-2">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{message.error}</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(renderMessage)}
        
        {/* Current streaming response */}
        {isStreaming && Object.keys(currentResponse).length > 0 && (
          <div className="flex justify-start mb-6">
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-4 max-w-full shadow-2xl">
              {/* Status indicator */}
              {currentResponse.status && (
                <div className="flex items-center gap-2 mb-2 text-cyan-400">
                  <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
                  <span className="text-sm">{currentResponse.status}</span>
                </div>
              )}

              {/* Streaming content */}
              {currentResponse.content && (
                <div className="text-white mb-3">
                  <div className="prose prose-invert max-w-none">
                    {currentResponse.content}
                    <span className="inline-block w-2 h-4 bg-cyan-400 animate-pulse ml-1"></span>
                  </div>
                </div>
              )}

              {/* Code being generated */}
              {currentResponse.code && (
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Code className="w-4 h-4 text-cyan-400" />
                      <span className="text-sm text-cyan-400 font-semibold">Generated Code</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => onCodeGenerated?.(currentResponse.code, false)}
                        className="px-3 py-1 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-300 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1"
                        title="Insert code into editor"
                      >
                        <Code className="w-3 h-3" />
                        Insert
                      </button>
                      <button
                        onClick={() => onCodeGenerated?.(currentResponse.code, true)}
                        className="px-3 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1"
                        title="Insert and execute code"
                      >
                        <Play className="w-3 h-3" />
                        Run
                      </button>
                    </div>
                  </div>
                  <pre className="bg-black/40 border border-white/20 rounded-xl p-3 text-green-300 text-sm overflow-x-auto">
                    <code>{currentResponse.code}</code>
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-white/20 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Ask me to analyze data, create plots, or write code..."
            className="flex-1 bg-black/30 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-gray-400 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
            disabled={isStreaming}
          />
          <button
            onClick={handleSendMessage}
            disabled={isStreaming || !input.trim()}
            className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-purple-500 text-white rounded-xl hover:from-cyan-600 hover:to-purple-600 disabled:opacity-50 font-semibold shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            {isStreaming ? 'Streaming...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
