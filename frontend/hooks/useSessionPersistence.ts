import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { getApiUrl } from '../lib/api'
const SESSION_STORAGE_KEY = 'aido_session_id'

interface SessionData {
  session_id: string
  created_at: string
  last_activity: string
  workspace_path: string
  user_id: string
  conversation_history: Array<{
    role: string
    content: string
    timestamp: string
  }>
  current_branch: string
  branch_code_cache: Record<string, string>
  uploaded_files: Array<any>
  sandbox_state: {
    variables: Record<string, any>
    imports: string[]
    working_directory: string
  }
  version_tree: Record<string, any>
  active: boolean
}

export function useSessionPersistence() {
  const [session, setSession] = useState<SessionData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Try to restore session from localStorage and backend
  const restoreSession = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Check if we have a session ID in localStorage
      const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
      
      if (storedSessionId) {
        // Try to restore the session from backend
        const response = await axios.get(getApiUrl(`/api/sessions/${storedSessionId}`))
        
        if (response.data) {
          setSession(response.data)
          console.log('Session restored from backend:', storedSessionId)
          return response.data
        }
      }
      
      // If no stored session or restoration failed, create new session
      return await createNewSession()
      
    } catch (error: any) {
      console.warn('Failed to restore session, creating new one:', error.message)
      return await createNewSession()
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Create a new session
  const createNewSession = useCallback(async () => {
    try {
      const response = await axios.post(getApiUrl('/api/sessions/create'))
      const newSession = response.data
      
      setSession(newSession)
      localStorage.setItem(SESSION_STORAGE_KEY, newSession.session_id)
      console.log('New session created:', newSession.session_id)
      
      return newSession
    } catch (error: any) {
      setError(`Failed to create session: ${error.message}`)
      console.error('Failed to create session:', error)
      return null
    }
  }, [])

  // Save conversation message to session
  const saveConversationMessage = useCallback(async (message: {
    role: string
    content: string
  }) => {
    if (!session) return false

    try {
      await axios.post(getApiUrl(`/api/sessions/${session.session_id}/conversation`), message)
      
      // Update local session state
      setSession(prev => prev ? {
        ...prev,
        conversation_history: [...prev.conversation_history, {
          ...message,
          timestamp: new Date().toISOString()
        }]
      } : null)
      
      return true
    } catch (error) {
      console.error('Failed to save conversation message:', error)
      return false
    }
  }, [session])

  // Update branch state
  const updateBranchState = useCallback(async (branch: string, code: string) => {
    if (!session) return false

    try {
      await axios.put(getApiUrl(`/api/sessions/${session.session_id}/branch`), {
        branch,
        code
      })
      
      // Update local session state
      setSession(prev => prev ? {
        ...prev,
        current_branch: branch,
        branch_code_cache: {
          ...prev.branch_code_cache,
          [branch]: code
        }
      } : null)
      
      return true
    } catch (error) {
      console.error('Failed to update branch state:', error)
      return false
    }
  }, [session])

  // Track uploaded file
  const trackUploadedFile = useCallback(async (fileInfo: {
    name: string
    path: string
    size: number
    type: string
  }) => {
    if (!session) return false

    try {
      await axios.post(getApiUrl(`/api/sessions/${session.session_id}/files`), fileInfo)
      
      // Update local session state
      setSession(prev => prev ? {
        ...prev,
        uploaded_files: [...prev.uploaded_files, {
          ...fileInfo,
          uploaded_at: new Date().toISOString()
        }]
      } : null)
      
      return true
    } catch (error) {
      console.error('Failed to track uploaded file:', error)
      return false
    }
  }, [session])

  // Update sandbox state
  const updateSandboxState = useCallback(async (variables: Record<string, any>, imports: string[]) => {
    if (!session) return false

    try {
      await axios.put(getApiUrl(`/api/sessions/${session.session_id}/sandbox`), {
        variables,
        imports
      })
      
      // Update local session state
      setSession(prev => prev ? {
        ...prev,
        sandbox_state: {
          ...prev.sandbox_state,
          variables,
          imports
        }
      } : null)
      
      return true
    } catch (error) {
      console.error('Failed to update sandbox state:', error)
      return false
    }
  }, [session])

  // Clear session (logout)
  const clearSession = useCallback(async () => {
    if (session) {
      try {
        await axios.delete(getApiUrl(`/api/sessions/${session.session_id}`))
      } catch (error) {
        console.error('Failed to delete session on backend:', error)
      }
    }
    
    localStorage.removeItem(SESSION_STORAGE_KEY)
    setSession(null)
    setError(null)
  }, [session])

  // Initialize session on mount
  useEffect(() => {
    restoreSession()
  }, [restoreSession])

  // Periodically update last activity
  useEffect(() => {
    if (!session) return

    const interval = setInterval(async () => {
      try {
        await axios.put(getApiUrl(`/api/sessions/${session.session_id}/activity`))
      } catch (error) {
        console.error('Failed to update session activity:', error)
      }
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [session])

  return {
    session,
    isLoading,
    error,
    restoreSession,
    createNewSession,
    saveConversationMessage,
    updateBranchState,
    trackUploadedFile,
    updateSandboxState,
    clearSession
  }
}
