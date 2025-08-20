'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import StreamingChat from '../components/StreamingChat'
import BranchManager from '../components/BranchManager'
import EnhancedCodeEditor from '../components/EnhancedCodeEditor'
import EnhancedOutputConsole from '../components/EnhancedOutputConsole'
import SimpleVersionTree from '../components/SimpleVersionTree'
import ArtifactViewer from '../components/ArtifactViewer'
import SecurityPanel from '../components/SecurityPanel'
import PackageManager from '../components/PackageManager'
import ClientOnly from '../components/ClientOnly'

// Use localhost since the browser runs on the host machine
const API_URL = 'http://localhost:8000'

export default function Home() {
  const [session, setSession] = useState<any>(null)
  const [code, setCode] = useState(`print("Hello, whats up AIDO Lab!")

# Example: Create a simple data visualization
import pandas as pd
import matplotlib.pyplot as plt

# Sample data
data = {'x': [1, 2, 3, 4, 5], 'y': [2, 5, 3, 8, 7]}
df = pd.DataFrame(data)

# Create plot
plt.figure(figsize=(8, 6))
plt.plot(df['x'], df['y'], marker='o')
plt.title('Sample Data Visualization')
plt.xlabel('X values')
plt.ylabel('Y values')
plt.grid(True)
plt.show()
`)
  const [output, setOutput] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)
  const [isCommitting, setIsCommitting] = useState(false)
  const [artifacts, setArtifacts] = useState<any[]>([])
  const [currentBranch, setCurrentBranch] = useState('main')
  const [branchCodeCache, setBranchCodeCache] = useState<Record<string, string>>({})

  useEffect(() => {
    createSession()
  }, [])

  const createSession = async () => {
    // Only run on client side
    if (typeof window === 'undefined') return
    
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
      
      const result = response.data
      const stdout = result.results?.stdout || result.stdout || ''
      const stderr = result.results?.stderr || result.stderr || ''
      
      setOutput(stdout + (stderr ? '\nErrors: ' + stderr : ''))
      
      // Update artifacts if any were generated
      const artifacts = result.results?.artifacts || result.artifacts || []
      if (artifacts.length > 0) {
        setArtifacts(artifacts)
      }
    } catch (error: any) {
      console.error('Execution failed:', error)
      setOutput(prev => prev + '\n\nExecution failed: ' + error.message)
    } finally {
      setIsExecuting(false)
    }
  }

  const handleCodeInsert = (generatedCode: string) => {
    setCode(generatedCode)
  }

  const handleCodeRevert = async (commitSha: string) => {
    if (!session) return
    
    try {
      const response = await axios.get(`${API_URL}/api/git/sessions/${session.session_id}/commits/${commitSha}/code`)
      if (response.data && response.data.code) {
        setCode(response.data.code)
        setOutput(`# Code reverted to commit ${commitSha.slice(0, 8)}
# Previous code has been restored to the editor
# You can now execute or modify this code`)
      }
    } catch (error) {
      console.error('Failed to revert code:', error)
      setOutput(`# Error: Failed to revert code from commit ${commitSha.slice(0, 8)}
# Please try again or check the commit history`)
    }
  }

  const handleCommitCode = async () => {
    if (!session || !code.trim()) return
    
    setIsCommitting(true)
    try {
      const response = await axios.post(`${API_URL}/api/git/commit/${session.session_id}`, {
        message: `Manual commit: ${new Date().toISOString()}`,
        code: code,
        branch: currentBranch
      })
      setOutput(prev => prev + '\n\n✅ Code committed to git: ' + response.data.sha + ` (${currentBranch})`)
      
      // Trigger git history refresh by dispatching a custom event
      window.dispatchEvent(new CustomEvent('gitHistoryUpdate', { 
        detail: { sessionId: session.session_id, commitSha: response.data.sha, branch: currentBranch } 
      }))
    } catch (error: any) {
      console.error('Commit failed:', error)
      setOutput(prev => prev + '\n\n❌ Commit failed: ' + error.message)
    } finally {
      setIsCommitting(false)
    }
  }

  const handleBranchSwitch = async (branchName: string) => {
    // Save current code to cache before switching
    setBranchCodeCache(prev => ({
      ...prev,
      [currentBranch]: code
    }))
    
    // Load code for the new branch
    const cachedCode = branchCodeCache[branchName]
    if (cachedCode) {
      setCode(cachedCode)
    } else {
      // Load code from git for this branch
      try {
        const response = await fetch(`${API_URL}/api/git/sessions/${session?.session_id}/branches/${branchName}/code`)
        if (response.ok) {
          const data = await response.json()
          setCode(data.code || '')
        } else {
          // Default code for new branch
          setCode('# New branch - start coding here!\nprint("Hello from ' + branchName + '")')
        }
      } catch (error) {
        console.error('Failed to load branch code:', error)
        setCode('# New branch - start coding here!\nprint("Hello from ' + branchName + '")')
      }
    }
    
    setCurrentBranch(branchName)
    setOutput(prev => prev + '\n\n🌿 Switched to branch: ' + branchName)
  }

  const handleBranchCreate = (branchName: string, fromBranch: string) => {
    // Cache current code when creating a new branch
    setBranchCodeCache(prev => ({
      ...prev,
      [fromBranch]: code,
      [branchName]: code // New branch starts with current code
    }))
    
    setCurrentBranch(branchName)
    setOutput(prev => prev + '\n\n🌿 Created and switched to branch: ' + branchName)
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
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                    <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></div>
                    Code Editor
                  </h2>
                  <div className="flex items-center gap-3">
                    {session && (
                      <BranchManager 
                        sessionId={session.session_id}
                        onBranchSwitch={handleBranchSwitch}
                        onBranchCreate={handleBranchCreate}
                      />
                    )}
                    {session && (
                      <span className="text-xs bg-black/30 px-3 py-1 rounded-full text-cyan-300">
                        Session: {session.session_id.slice(0, 8)}...
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="h-96">
                <EnhancedCodeEditor
                  code={code}
                  onChange={setCode}
                  onExecute={executeCode}
                  isExecuting={isExecuting}
                  onSave={handleCommitCode}
                  isSaving={isCommitting}
                />
              </div>
            </div>
            
            {/* Output Console */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="h-96">
                <EnhancedOutputConsole
                  output={output}
                  isExecuting={isExecuting}
                />
              </div>
            </div>
          </div>

          {/* Second Row - AI Chat, Version Tree, Packages */}
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
                <ClientOnly fallback={
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin mx-auto mb-4"></div>
                      <p>Loading AI Assistant...</p>
                    </div>
                  </div>
                }>
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
                </ClientOnly>
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
                <ClientOnly fallback={
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <svg className="w-12 h-12 mx-auto mb-4 text-cyan-500/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <p>Loading History...</p>
                    </div>
                  </div>
                }>
                  {session ? (
                    <SimpleVersionTree 
                      sessionId={session.session_id}
                      currentBranch={currentBranch}
                      onCodeRevert={handleCodeRevert}
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
                </ClientOnly>
              </div>
            </div>

            {/* Package Manager */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border-b border-white/10 p-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                  <div className="w-3 h-3 bg-yellow-400 rounded-full animate-pulse"></div>
                  Packages
                  <span className="ml-auto text-xs bg-yellow-500/20 px-2 py-1 rounded-full text-yellow-300">
                    pip
                  </span>
                </h2>
              </div>
              <div className="h-96">
                <ClientOnly fallback={
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <div className="w-12 h-12 border-2 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin mx-auto mb-4"></div>
                      <p>Loading Package Manager...</p>
                    </div>
                  </div>
                }>
                  {session ? (
                    <PackageManager sessionId={session.session_id} />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-400">
                      <div className="text-center">
                        <div className="w-12 h-12 border-2 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin mx-auto mb-4"></div>
                        <p>Initializing session...</p>
                      </div>
                    </div>
                  )}
                </ClientOnly>
              </div>
            </div>

          </div>

          {/* Third Row - Security and Artifacts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
                <ClientOnly fallback={
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <div className="w-12 h-12 border-2 border-red-500/30 border-t-red-500 rounded-full animate-spin mx-auto mb-4"></div>
                      <p>Loading Security Panel...</p>
                    </div>
                  </div>
                }>
                  <SecurityPanel />
                </ClientOnly>
              </div>
            </div>

            {/* Artifacts Panel */}
            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-green-500/10 to-blue-500/10 border-b border-white/10 p-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                  Plots & Tables
                  <span className="ml-2 text-xs bg-blue-500/20 px-2 py-1 rounded-full text-blue-300">
                    {currentBranch}
                  </span>
                  <span className="ml-auto text-xs bg-green-500/20 px-2 py-1 rounded-full text-green-300">
                    {artifacts.length}
                  </span>
                </h2>
              </div>
              <div className="h-96 overflow-y-auto">
                <ClientOnly fallback={
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <div className="w-12 h-12 border-2 border-green-500/30 border-t-green-500 rounded-full animate-spin mx-auto mb-4"></div>
                      <p>Loading Artifacts...</p>
                    </div>
                  </div>
                }>
                  {session ? (
                    <div className="p-4">
                      <ArtifactViewer 
                        sessionId={session.session_id}
                        artifacts={artifacts}
                        currentBranch={currentBranch}
                      />
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-400">
                      <div className="text-center">
                        <svg className="w-12 h-12 mx-auto mb-4 text-green-500/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        <p>No artifacts yet</p>
                        <p className="text-sm mt-1">Run code with plots or tables</p>
                      </div>
                    </div>
                  )}
                </ClientOnly>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
