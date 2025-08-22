'use client'

import React, { useState, useEffect } from 'react'
import { Image, FileText, BarChart3, Download } from 'lucide-react'

interface Artifact {
  filename: string
  type: 'plot' | 'table' | 'file'
  size: number
}

interface ArtifactViewerProps {
  sessionId: string
  artifacts: Artifact[]
  currentBranch: string
}

interface TableData {
  columns: string[]
  data: any[][]
  shape: [number, number]
}

export default function ArtifactViewer({ sessionId, artifacts, currentBranch }: ArtifactViewerProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null)
  const [tableData, setTableData] = useState<TableData | null>(null)
  const [loading, setLoading] = useState(false)
  const [branchArtifacts, setBranchArtifacts] = useState<Artifact[]>([])

  // Use passed artifacts first, then fetch from API if needed
  useEffect(() => {
    // If we have artifacts passed as props, use them first
    if (artifacts && artifacts.length > 0) {
      setBranchArtifacts(artifacts)
      return
    }

    // Otherwise, try to fetch from API
    const fetchBranchArtifacts = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/git/sessions/${sessionId}/artifacts?branch=${currentBranch}`)
        if (response.ok) {
          const data = await response.json()
          if (data.artifacts && data.artifacts.length > 0) {
            setBranchArtifacts(data.artifacts)
            return
          }
        }
      } catch (error) {
        console.error('Failed to fetch branch artifacts:', error)
      }
      
      // Fallback: fetch artifacts directly from workspace API
      try {
        const response = await fetch(`http://localhost:8000/api/workspaces/${sessionId}/files`)
        if (response.ok) {
          const data = await response.json()
          setBranchArtifacts(data.artifacts || [])
        }
      } catch (error) {
        console.error('Failed to fetch workspace artifacts:', error)
      }
    }

    if (sessionId && currentBranch) {
      fetchBranchArtifacts()
    }
  }, [sessionId, currentBranch, artifacts])

  const plotArtifacts = branchArtifacts.filter(a => a.type === 'plot')
  const tableArtifacts = branchArtifacts.filter(a => a.type === 'table' && a.filename.endsWith('.json'))

  const loadTableData = async (filename: string) => {
    setLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/workspaces/${sessionId}/${filename}`)
      if (response.ok) {
        const data = await response.json()
        setTableData(data)
      }
    } catch (error) {
      console.error('Failed to load table data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (branchArtifacts.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-400">
        <div className="text-center">
          <FileText className="w-8 h-8 mx-auto mb-2 text-gray-500" />
          <p className="text-sm">No artifacts generated</p>
          <p className="text-xs mt-1">Run code with plots or tables to see them here</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Plots Section */}
      {plotArtifacts.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            Plots ({plotArtifacts.length})
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {plotArtifacts.map((artifact, index) => (
              <div key={index} className="relative group">
                <img
                  src={`http://localhost:8000/workspaces/${sessionId}/${artifact.filename}`}
                  alt={artifact.filename}
                  className="w-full h-32 object-contain bg-white/5 rounded border border-white/10 hover:border-cyan-400/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedArtifact(artifact.filename)}
                />
                <div className="absolute bottom-1 left-1 bg-black/70 text-white text-xs px-1 py-0.5 rounded">
                  {artifact.filename}
                </div>
                <div className="absolute top-1 right-1 bg-black/70 text-white text-xs px-1 py-0.5 rounded">
                  {formatFileSize(artifact.size)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tables Section */}
      {tableArtifacts.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            Tables ({tableArtifacts.length})
          </h4>
          <div className="space-y-2">
            {tableArtifacts.map((artifact, index) => (
              <div
                key={index}
                className="p-3 bg-white/5 rounded border border-white/10 hover:border-cyan-400/50 transition-colors cursor-pointer"
                onClick={() => loadTableData(artifact.filename)}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm text-white">{artifact.filename.replace('.json', '')}</span>
                  <span className="text-xs text-gray-400">{formatFileSize(artifact.size)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plot Modal */}
      {selectedArtifact && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setSelectedArtifact(null)}>
          <div className="max-w-4xl max-h-[90vh] p-4">
            <img
              src={`http://localhost:8000/workspaces/${sessionId}/${selectedArtifact}`}
              alt={selectedArtifact}
              className="max-w-full max-h-full object-contain bg-white rounded"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="text-center mt-2">
              <span className="text-white text-sm">{selectedArtifact}</span>
            </div>
          </div>
        </div>
      )}

      {/* Table Modal */}
      {tableData && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setTableData(null)}>
          <div className="bg-slate-800 rounded-lg p-6 max-w-6xl max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">
                Table Data ({tableData?.shape?.[0] || 0} rows × {tableData?.shape?.[1] || 0} columns)
              </h3>
              <button
                onClick={() => setTableData(null)}
                className="text-gray-400 hover:text-white"
              >
                ×
              </button>
            </div>
            
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
              </div>
            ) : (
              <div className="overflow-auto max-h-96">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-600">
                      {tableData?.columns?.map((col, i) => (
                        <th key={i} className="text-left p-2 text-cyan-400 font-medium">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData?.data?.slice(0, 100).map((row, i) => (
                      <tr key={i} className="border-b border-gray-700/50">
                        {row?.map((cell, j) => (
                          <td key={j} className="p-2 text-gray-300">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {tableData?.data?.length > 100 && (
                  <div className="text-center text-gray-400 text-xs mt-2">
                    Showing first 100 rows of {tableData?.data?.length}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
