'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import StreamingChat from '../components/StreamingChat'
import CodeEditor from '../components/CodeEditor'
import OutputConsole from '../components/OutputConsole'
import VersionTree from '../components/VersionTree'
import SecurityPanel from '../components/SecurityPanel'

// Use localhost since the browser runs on the host machine
const API_URL = 'http://localhost:8000'

export default function Home() {
  const [session, setSession] = useState<any>(null)
  const [code, setCode] = useState('print("Hello, whats up AIDO Lab!")')
  const [output, setOutput] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)

  useEffect(() => {
    createSession()
  }, [])

  const createSession = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/sessions/create`)
      setSession(response.data)
      console.log('Session created:', response.data)
      setOutput('Session created! Ready to execute code.')
    } catch (error) {
      console.error('Failed to create session:', error)
      setOutput('Failed to create session. Check if backend is running.')
    }
  }

  const executeCode = async () => {
    if (!session) {
      setOutput('No session. Creating one...')
      await createSession()
      return
    }
    
    setIsExecuting(true)
    setOutput('Executing...')
    
    try {
      const response = await axios.post(`${API_URL}/api/execute`, {
        session_id: session.session_id,
        query: code,
        is_natural_language: false,
      })
      
      const result = response.data.results
      setOutput(result.stdout || result.stderr || 'No output')
    } catch (error: any) {
      console.error('Execution failed:', error)
      setOutput(`Execution failed: ${error.message}`)
    } finally {
      setIsExecuting(false)
    }
  }

  const handleCodeInsert = (generatedCode: string, autoExecute = false) => {
    setCode(generatedCode)
    if (autoExecute) {
      // Execute after a short delay to allow state to update
      setTimeout(() => {
        executeCode()
      }, 100)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse animation-delay-2000"></div>
        <div className="absolute top-40 left-40 w-60 h-60 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse animation-delay-4000"></div>
      </div>
      
      <div className="relative z-10 max-w-7xl mx-auto p-8">
        <div className="text-center mb-12">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mb-4">
            AIDO Lab
          </h1>
          <p className="text-xl text-gray-300 font-light">
            AI-Driven Data Science Platform with Secure Code Execution
          </p>
        </div>
        
        {/* Main Content Area */}
        <div className="space-y-6">
          {/* Top Row - Code Editor and Output */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Code Editor */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border-b border-white/10 p-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                  <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></div>
                  Code Editor
                  {session && (
                    <span className="ml-auto text-xs bg-black/30 px-3 py-1 rounded-full text-cyan-300">
                      Session: {session.session_id.slice(0, 8)}...
                    </span>
                  )}
                </h2>
              </div>
              <div className="p-6">
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full h-80 p-4 bg-black/20 border border-white/10 rounded-xl font-mono text-sm resize-none text-emerald-300 placeholder-gray-500 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/20 transition-all"
                  placeholder="# Enter your Python code here...
# Example:
import pandas as pd
import matplotlib.pyplot as plt

# Your analysis code"
                />
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={executeCode}
                    disabled={isExecuting}
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-xl hover:from-emerald-600 hover:to-cyan-600 disabled:opacity-50 font-semibold shadow-lg hover:shadow-emerald-500/25 transition-all duration-300 transform hover:scale-[1.02] disabled:hover:scale-100"
                  >
                    {isExecuting ? (
                      <span className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        Executing...
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m6-6V7a2 2 0 00-2-2H5a2 2 0 00-2 2v3m0 0v8a2 2 0 002 2h14a2 2 0 002-2v-8m0 0V7" />
                        </svg>
                        Execute Code
                      </span>
                    )}
                  </button>
                  <button className="px-4 py-3 bg-white/10 border border-white/20 text-white rounded-xl hover:bg-white/20 transition-all duration-300">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Output Console */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border-b border-white/10 p-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                  <div className="w-3 h-3 bg-amber-400 rounded-full animate-pulse"></div>
                  Output Console
                  <div className="ml-auto flex gap-2">
                    <button className="p-1 hover:bg-white/10 rounded transition-colors">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                    <button className="p-1 hover:bg-white/10 rounded transition-colors">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </h2>
              </div>
              <div className="p-6">
                <pre className="w-full h-80 p-4 bg-black/20 border border-white/10 rounded-xl text-amber-300 overflow-auto text-sm font-mono shadow-inner leading-relaxed">
                  {output || `# Console Output
# Ready for code execution...
# 
# Tips:
# - Use print() to see output
# - Variables persist between executions
# - Import libraries as needed`}
                </pre>
              </div>
            </div>
          </div>

          {/* Bottom Row - AI Chat, Version Tree, and Security */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* AI Assistant */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-b border-white/10 p-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                  <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse"></div>
                  AI Assistant
                  <span className="ml-auto text-xs bg-purple-500/20 px-2 py-1 rounded-full text-purple-300">
                    Claude
                  </span>
                </h2>
              </div>
              <div className="h-96">
                {session ? (
                  <StreamingChat 
                    sessionId={session.session_id}
                    onCodeGenerated={handleCodeInsert}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin mx-auto mb-4"></div>
                      <p>Initializing session...</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Version Tree */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border-b border-white/10 p-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                  <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse"></div>
                  Analysis History
                  <span className="ml-auto text-xs bg-cyan-500/20 px-2 py-1 rounded-full text-cyan-300">
                    Git
                  </span>
                </h2>
              </div>
              <div className="h-96">
                {session ? (
                  <VersionTree 
                    sessionId={session.session_id}
                    onCommitSelect={(commitHash) => console.log('Selected commit:', commitHash)}
                    onBranchFork={(fromCommit, branchName) => console.log('Created branch:', branchName)}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <svg className="w-12 h-12 mx-auto mb-4 text-cyan-500/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <p>No commits yet</p>
                      <p className="text-sm mt-1">Run code to create history</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Security Panel */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border-b border-white/10 p-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                  <div className="w-3 h-3 bg-red-400 rounded-full animate-pulse"></div>
                  Security Status
                  <span className="ml-auto text-xs bg-red-500/20 px-2 py-1 rounded-full text-red-300">
                    Active
                  </span>
                </h2>
              </div>
              <div className="h-96">
                <SecurityPanel />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
