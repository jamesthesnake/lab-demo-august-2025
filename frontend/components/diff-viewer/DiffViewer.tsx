import React, { useState, useEffect } from 'react';
import { GitCompare, FileText, Plus, Minus, Eye, ArrowRight } from 'lucide-react';

interface DiffFile {
  path: string;
  status: 'added' | 'modified' | 'deleted';
  additions?: number;
  deletions?: number;
}

interface DiffData {
  files_added: string[];
  files_modified: string[];
  files_deleted: string[];
  stats: Record<string, any>;
}

interface DiffViewerProps {
  sessionId: string;
  commitSha1: string;
  commitSha2: string;
  onClose?: () => void;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  sessionId,
  commitSha1,
  commitSha2,
  onClose
}) => {
  const [diffData, setDiffData] = useState<DiffData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<{ before: string; after: string } | null>(null);

  useEffect(() => {
    loadDiff();
  }, [sessionId, commitSha1, commitSha2]);

  const loadDiff = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/git/sessions/${sessionId}/diff/${commitSha1}/${commitSha2}`);
      const data = await response.json();
      setDiffData(data.diff);
    } catch (error) {
      console.error('Failed to load diff:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filePath: string) => {
    try {
      // Load file content from both commits
      const [beforeResponse, afterResponse] = await Promise.all([
        fetch(`/api/git/sessions/${sessionId}/file/${commitSha1}/${filePath}`),
        fetch(`/api/git/sessions/${sessionId}/file/${commitSha2}/${filePath}`)
      ]);

      const before = beforeResponse.ok ? await beforeResponse.text() : '';
      const after = afterResponse.ok ? await afterResponse.text() : '';

      setFileContent({ before, after });
      setSelectedFile(filePath);
    } catch (error) {
      console.error('Failed to load file content:', error);
    }
  };

  const getFileIcon = (status: string) => {
    switch (status) {
      case 'added':
        return <Plus className="w-4 h-4 text-green-600" />;
      case 'deleted':
        return <Minus className="w-4 h-4 text-red-600" />;
      case 'modified':
        return <FileText className="w-4 h-4 text-blue-600" />;
      default:
        return <FileText className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'added':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'deleted':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'modified':
        return 'bg-blue-50 border-blue-200 text-blue-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const renderLineDiff = (before: string, after: string) => {
    const beforeLines = before.split('\n');
    const afterLines = after.split('\n');
    const maxLines = Math.max(beforeLines.length, afterLines.length);

    return (
      <div className="grid grid-cols-2 gap-4 font-mono text-sm">
        <div className="border-r border-gray-200 pr-4">
          <div className="bg-red-50 text-red-800 px-2 py-1 text-xs font-medium mb-2">
            Before ({commitSha1.substring(0, 8)})
          </div>
          <div className="space-y-1">
            {beforeLines.map((line, index) => (
              <div key={index} className="flex">
                <span className="text-gray-400 w-8 text-right mr-2">{index + 1}</span>
                <span className="flex-1">{line || ' '}</span>
              </div>
            ))}
          </div>
        </div>
        
        <div className="pl-4">
          <div className="bg-green-50 text-green-800 px-2 py-1 text-xs font-medium mb-2">
            After ({commitSha2.substring(0, 8)})
          </div>
          <div className="space-y-1">
            {afterLines.map((line, index) => (
              <div key={index} className="flex">
                <span className="text-gray-400 w-8 text-right mr-2">{index + 1}</span>
                <span className="flex-1">{line || ' '}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6">
          <div className="text-center">Loading diff...</div>
        </div>
      </div>
    );
  }

  if (!diffData) {
    return null;
  }

  const allFiles: Array<{ path: string; status: string }> = [
    ...diffData.files_added.map(path => ({ path, status: 'added' })),
    ...diffData.files_modified.map(path => ({ path, status: 'modified' })),
    ...diffData.files_deleted.map(path => ({ path, status: 'deleted' }))
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-6xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <GitCompare className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold">Compare Commits</h2>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                {commitSha1.substring(0, 8)}
              </span>
              <ArrowRight className="w-4 h-4" />
              <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                {commitSha2.substring(0, 8)}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl font-bold"
          >
            ×
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* File List */}
          <div className="w-1/3 border-r border-gray-200 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Changed Files ({allFiles.length})
              </h3>
              
              <div className="space-y-1">
                {allFiles.map((file) => (
                  <div
                    key={file.path}
                    className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                      selectedFile === file.path
                        ? 'bg-blue-100 border border-blue-300'
                        : 'hover:bg-gray-50'
                    }`}
                    onClick={() => loadFileContent(file.path)}
                  >
                    {getFileIcon(file.status)}
                    <span className="flex-1 text-sm truncate">{file.path}</span>
                    <span className={`text-xs px-2 py-1 rounded border ${getStatusColor(file.status)}`}>
                      {file.status}
                    </span>
                  </div>
                ))}
              </div>

              {allFiles.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No changes between commits
                </div>
              )}
            </div>
          </div>

          {/* File Content */}
          <div className="flex-1 overflow-y-auto">
            {selectedFile && fileContent ? (
              <div className="p-4">
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    {selectedFile}
                  </h4>
                </div>
                {renderLineDiff(fileContent.before, fileContent.after)}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <Eye className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                  <p>Select a file to view changes</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Plus className="w-3 h-3 text-green-600" />
                {diffData.files_added.length} added
              </span>
              <span className="flex items-center gap-1">
                <FileText className="w-3 h-3 text-blue-600" />
                {diffData.files_modified.length} modified
              </span>
              <span className="flex items-center gap-1">
                <Minus className="w-3 h-3 text-red-600" />
                {diffData.files_deleted.length} deleted
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DiffViewer;
