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

  const handleCodeInsert = (generatedCode: string) => {
    setCode(generatedCode)
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
        
        <div className="grid grid-cols-5 gap-6 h-[calc(100vh-280px)]">
          {/* Code Editor */}
          <div className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl shadow-2xl p-6 hover:bg-white/15 transition-all duration-300">
            <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              Code Editor
            </h2>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-72 p-4 bg-black/30 border border-white/20 rounded-xl font-mono text-sm resize-none text-green-300 placeholder-gray-400 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
              placeholder="# Enter Python code here..."
            />
            <button
              onClick={executeCode}
              disabled={isExecuting}
              className="mt-4 px-6 py-3 bg-gradient-to-r from-cyan-500 to-purple-500 text-white rounded-xl hover:from-cyan-600 hover:to-purple-600 disabled:opacity-50 font-semibold shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105"
            >
              {isExecuting ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Executing...
                </span>
              ) : (
                'Execute Code'
              )}
            </button>
            
            {session && (
              <div className="mt-4 text-sm text-gray-300 bg-black/20 rounded-lg p-2 border border-white/10">
                <span className="text-cyan-400">Session:</span> {session.session_id.slice(0, 8)}...
              </div>
            )}
          </div>
          
          {/* Output */}
          <div className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl shadow-2xl p-6 hover:bg-white/15 transition-all duration-300">
            <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
              Output Console
            </h2>
            <pre className="w-full h-72 p-4 bg-black/40 border border-white/20 rounded-xl text-green-300 overflow-auto text-sm font-mono shadow-inner">
              {output || '# Output will appear here...\n# Ready for execution'}
            </pre>
          </div>

          {/* AI Chat */}
          <div className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl shadow-2xl overflow-hidden hover:bg-white/15 transition-all duration-300">
            <h2 className="text-xl font-semibold p-6 pb-4 bg-gradient-to-r from-purple-500/20 to-pink-500/20 border-b border-white/20 text-white flex items-center gap-2">
              <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
              AI Assistant
            </h2>
            <div className="h-full">
              {session && (
                <StreamingChat 
                  sessionId={session.session_id}
                />
              )}
            </div>
          </div>

          {/* Analysis History */}
          <div className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl shadow-2xl overflow-hidden hover:bg-white/15 transition-all duration-300">
            <div className="h-full">
              {session && (
                <VersionTree 
                  sessionId={session.session_id}
                  onCommitSelect={(commitHash) => console.log('Selected commit:', commitHash)}
                  onBranchFork={(fromCommit, branchName) => console.log('Created branch:', branchName)}
                />
              )}
            </div>
          </div>

          {/* Security Panel */}
          <div className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl shadow-2xl overflow-hidden hover:bg-white/15 transition-all duration-300">
            <div className="h-full">
              <SecurityPanel />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
