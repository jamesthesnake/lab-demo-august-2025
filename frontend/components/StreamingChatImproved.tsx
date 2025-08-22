'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, Square, Code, Play, FileText, GitBranch, AlertCircle, Image, User, Bot } from 'lucide-react'
import { getApiUrl } from '../lib/api'

interface StreamEvent {
  type: string
  payload: any
}

interface Message {
  id: string
  userMessage: string
  aiResponse?: {
    content?: string
    code?: string
    result?: any
    artifacts?: any[]
    commit?: any
  }
  timestamp: Date
  isComplete: boolean
}

interface StreamingChatProps {
  sessionId: string
  onCodeGenerated?: (code: string, Execute?: boolean) => void
  currentCode?: string
  currentOutput?: string
}

export default function StreamingChatImproved({ sessionId, onCodeGenerated, currentCode, currentOutput }: StreamingChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentMessage, setCurrentMessage] = useState<Message | null>(null)
  const [responseFormat, setResponseFormat] = useState<'code' | 'conversational'>('code')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentMessage])

  const extractCodeFromText = (text: string): string | null => {
    const pythonCodeMatch = text.match(/```(?:python|py)?\n([\s\S]*?)\n```/i)
    if (pythonCodeMatch) {
      return pythonCodeMatch[1].trim()
    }
    
    const codeMatch = text.match(/```\n?([\s\S]*?)\n?```/)
    if (codeMatch) {
      return codeMatch[1].trim()
    }
    
    const inlineMatch = text.match(/`([^`]*(?:import|def|print|pandas|numpy|plt)[^`]*)`/)
    if (inlineMatch) {
      return inlineMatch[1].trim()
    }
    
    return null
  }

  const sendMessage = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage = input.trim()
    setInput('')
    setIsStreaming(true)

    // Create new message with unique ID
    const newMessage: Message = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      userMessage,
      aiResponse: {},
      timestamp: new Date(),
      isComplete: false
    }

    setCurrentMessage(newMessage)
    
    console.log('Sending message:', userMessage)
    console.log('API URL:', getApiUrl(`/api/stream/chat/${sessionId}`))

    try {
      // Send the request to start streaming
      const response = await fetch(getApiUrl(`/api/stream/chat/${sessionId}`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          response_format: responseFormat,
          context: {
            current_code: currentCode,
            current_output: currentOutput
          }
        })
      })

      console.log('Response status:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Stream response error:', errorText)
        throw new Error(`Failed to start stream: ${response.status} ${errorText}`)
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
          if (line.startsWith('data: ') && line.trim() !== 'data: ') {
            try {
              let jsonStr = line.slice(6).trim()
              
              // Handle double "data: " prefix from backend
              if (jsonStr.startsWith('data: ')) {
                jsonStr = jsonStr.slice(6).trim()
              }
              
              if (jsonStr && jsonStr !== '[DONE]') {
                console.log('Parsing JSON:', jsonStr)
                const data: StreamEvent = JSON.parse(jsonStr)
                
                setCurrentMessage(prev => {
                  if (!prev) return prev
                  
                  const updatedResponse = { ...prev.aiResponse }
                  
                  switch (data.type) {
                    case 'text':
                      updatedResponse.content = (updatedResponse.content || '') + data.payload
                      break
                    case 'code':
                      updatedResponse.code = data.payload
                      break
                    case 'result':
                      updatedResponse.result = data.payload
                      break
                    case 'artifact':
                      updatedResponse.artifacts = [...(updatedResponse.artifacts || []), data.payload]
                      break
                    case 'commit':
                      updatedResponse.commit = data.payload
                      break
                    case 'complete':
                      const completedMessage = { ...prev, aiResponse: updatedResponse, isComplete: true }
                      setMessages(prevMessages => {
                        // Check if this message already exists to prevent duplicates
                        const exists = prevMessages.some(msg => msg.id === completedMessage.id)
                        if (exists) return prevMessages
                        return [...prevMessages, completedMessage]
                      })
                      setCurrentMessage(null)
                      setIsStreaming(false)
                      return null
                    case 'error':
                      updatedResponse.content = (updatedResponse.content || '') + `\n\nError: ${data.payload}`
                      const errorMessage = { ...prev, aiResponse: updatedResponse, isComplete: true }
                      setMessages(prevMessages => {
                        // Check if this message already exists to prevent duplicates
                        const exists = prevMessages.some(msg => msg.id === errorMessage.id)
                        if (exists) return prevMessages
                        return [...prevMessages, errorMessage]
                      })
                      setCurrentMessage(null)
                      setIsStreaming(false)
                      return null
                  }
                  
                  return { ...prev, aiResponse: updatedResponse }
                })
              }
            } catch (error) {
              console.error('Error parsing stream data:', error, 'Raw line:', line)
              // Skip malformed JSON and continue processing
              continue
            }
          }
        }
      }


    } catch (error) {
      console.error('Stream error:', error)
      setIsStreaming(false)
      
      if (currentMessage && !currentMessage.isComplete) {
        const errorMessage = { 
          ...currentMessage, 
          aiResponse: { 
            ...currentMessage.aiResponse, 
            content: (currentMessage.aiResponse?.content || '') + `\n\nConnection error: ${error.message}` 
          },
          isComplete: true 
        }
        setMessages(prev => {
          // Check if this message already exists to prevent duplicates
          const exists = prev.some(msg => msg.id === errorMessage.id)
          if (exists) return prev
          return [...prev, errorMessage]
        })
      }
      setCurrentMessage(null)
    }
  }

  const stopStreaming = () => {
    setIsStreaming(false)
    
    if (currentMessage && !currentMessage.isComplete) {
      const completedMessage = { ...currentMessage, isComplete: true }
      setMessages(prev => {
        // Check if this message already exists to prevent duplicates
        const exists = prev.some(msg => msg.id === completedMessage.id)
        if (exists) return prev
        return [...prev, completedMessage]
      })
      setCurrentMessage(null)
    }
  }

  const renderMessage = (message: Message) => {
    return (
      <div key={message.id} className="space-y-4">
        {/* User Message */}
        <div className="flex justify-end">
          <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 backdrop-blur-xl border border-blue-400/30 rounded-2xl p-4 max-w-[80%] shadow-lg">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-blue-300 font-medium">You</span>
              <span className="text-xs text-gray-400">{message.timestamp.toLocaleTimeString()}</span>
            </div>
            <div className="text-white">
              {message.userMessage}
            </div>
          </div>
        </div>

        {/* AI Response */}
        <div className="flex justify-start">
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-4 max-w-[85%] shadow-2xl">
            <div className="flex items-center gap-2 mb-3">
              <Bot className="w-4 h-4 text-cyan-400" />
              <span className="text-sm text-cyan-300 font-medium">AI Assistant</span>
              {!message.isComplete && (
                <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
              )}
            </div>

            {/* Text Response */}
            {message.aiResponse?.content && (
              <div className="text-white mb-3">
                <div className="prose prose-invert max-w-none text-sm">
                  {message.aiResponse.content.split('\n').map((line, i) => (
                    <p key={i} className="mb-2">{line}</p>
                  ))}
                </div>
              </div>
            )}

            {/* Code Block */}
            {message.aiResponse?.code && (
              <div className="mb-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Code className="w-4 h-4 text-cyan-400" />
                    <span className="text-sm text-cyan-400 font-semibold">Generated Code</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => onCodeGenerated?.(message.aiResponse!.code!, false)}
                      className="px-3 py-1 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-300 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1"
                      title="Insert code into editor"
                    >
                      <Code className="w-3 h-3" />
                      Insert
                    </button>
                    <button
                      onClick={() => onCodeGenerated?.(message.aiResponse!.code!, true)}
                      className="px-3 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1"
                      title="Insert and execute code"
                    >
                      <Play className="w-3 h-3" />
                      Run
                    </button>
                  </div>
                </div>
                <pre className="bg-black/40 border border-white/20 rounded-xl p-3 text-green-300 text-sm overflow-x-auto">
                  <code>{message.aiResponse.code}</code>
                </pre>
              </div>
            )}

            {/* Execution Result */}
            {message.aiResponse?.result && (
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <Play className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm text-yellow-400 font-semibold">Execution Result</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    message.aiResponse.result.status === 'ok' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {message.aiResponse.result.status}
                  </span>
                </div>
                
                {message.aiResponse.result.stdout && (
                  <pre className="bg-black/40 border border-white/20 rounded-xl p-3 text-green-300 text-sm mb-2 overflow-x-auto">
                    {message.aiResponse.result.stdout}
                  </pre>
                )}
                
                {message.aiResponse.result.stderr && (
                  <pre className="bg-red-900/20 border border-red-500/30 rounded-xl p-3 text-red-300 text-sm overflow-x-auto">
                    {message.aiResponse.result.stderr}
                  </pre>
                )}
              </div>
            )}

            {/* Artifacts */}
            {message.aiResponse?.artifacts && message.aiResponse.artifacts.length > 0 && (
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <Image className="w-4 h-4 text-purple-400" />
                  <span className="text-sm text-purple-400 font-semibold">Generated Artifacts</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {message.aiResponse.artifacts.map((artifact, i) => (
                    <div key={i} className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-2">
                      <div className="text-xs text-purple-300 font-medium">{artifact.filename || artifact.path}</div>
                      <div className="text-xs text-gray-400">{artifact.type}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Git Commit */}
            {message.aiResponse?.commit && (
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <GitBranch className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-green-400 font-semibold">Saved to Git</span>
                </div>
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-2">
                  <div className="text-xs text-green-300 font-mono">{message.aiResponse.commit.sha}</div>
                  <div className="text-xs text-gray-400">Branch: {message.aiResponse.commit.branch}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-white/20 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">AI Assistant</h3>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Response:</span>
            <select
              value={responseFormat}
              onChange={(e) => setResponseFormat(e.target.value as 'code' | 'conversational')}
              className="bg-black/30 border border-white/20 text-white text-sm rounded-lg px-3 py-1 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
            >
              <option value="code">Code-focused</option>
              <option value="conversational">Conversational</option>
            </select>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map(renderMessage)}
        
        {/* Current streaming message */}
        {currentMessage && renderMessage(currentMessage)}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-white/20 p-4">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
              placeholder="Ask me to analyze data, create plots, or write code..."
              className="w-full bg-black/30 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-gray-400 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all resize-none"
              rows={3}
              disabled={isStreaming}
            />
          </div>
          
          <div className="flex flex-col gap-2">
            {isStreaming ? (
              <button
                onClick={stopStreaming}
                className="p-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-300 rounded-xl transition-all duration-200 flex items-center justify-center"
                title="Stop generation"
              >
                <Square className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={sendMessage}
                disabled={!input.trim()}
                className="p-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-200 flex items-center justify-center shadow-lg hover:shadow-cyan-500/25"
                title="Send message (Enter)"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
        
        <div className="mt-2 text-xs text-gray-400 text-center">
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
    </div>
  )
}
