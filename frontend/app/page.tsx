'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

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

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">AIDO Lab</h1>
        
        <div className="grid grid-cols-2 gap-8">
          <div>
            <h2 className="text-xl font-semibold mb-4">Code Editor</h2>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-96 p-4 border rounded-lg font-mono text-sm"
              placeholder="Enter Python code here..."
            />
            <button
              onClick={executeCode}
              disabled={isExecuting}
              className="mt-4 px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
            >
              {isExecuting ? 'Executing...' : 'Execute'}
            </button>
          </div>
          
          <div>
            <h2 className="text-xl font-semibold mb-4">Output</h2>
            <pre className="w-full h-96 p-4 border rounded-lg bg-gray-900 text-green-400 overflow-auto">
              {output || 'Output will appear here...'}
            </pre>
          </div>
        </div>
        
        {session && (
          <div className="mt-8 text-sm text-gray-600">
            Session ID: {session.session_id}
          </div>
        )}
      </div>
    </div>
  )
}
