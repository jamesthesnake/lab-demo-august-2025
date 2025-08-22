// API configuration utility
export const getApiBaseUrl = (): string => {
  // NEXT_PUBLIC_ environment variables are available in the browser
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }
  
  // Check if we're in browser
  if (typeof window !== 'undefined') {
    // Client-side: always use localhost for development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }
    // For production deployments, use same host but port 8000
    return `http://${window.location.hostname}:8000`
  }
  
  // Server-side: use internal Docker network name
  return 'http://backend:8000'
}

export const getApiUrl = (path: string): string => {
  const baseUrl = getApiBaseUrl()
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const fullUrl = `${baseUrl}${cleanPath}`
  console.log('API URL:', fullUrl, 'Browser:', typeof window !== 'undefined', 'Hostname:', typeof window !== 'undefined' ? window.location.hostname : 'server')
  return fullUrl
}
