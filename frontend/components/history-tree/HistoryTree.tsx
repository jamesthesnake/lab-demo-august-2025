import React, { useState, useEffect } from 'react';
import { GitBranch, GitCommit, Eye, Plus, ArrowRight, RotateCcw, GitCompare, GitMerge, Bookmark } from 'lucide-react';
import DiffViewer from '../diff-viewer/DiffViewer';

interface Commit {
  hash: string;
  message: string;
  timestamp: string;
  branch: string;
  parent?: string;
}

interface Branch {
  name: string;
  commits: Commit[];
  current: boolean;
}

interface HistoryTreeProps {
  sessionId: string;
  onCommitSelect?: (commitHash: string) => void;
  onBranchCreate?: (fromCommit: string, branchName: string) => void;
  onCommitRestore?: (commitHash: string) => void;
}

export const HistoryTree: React.FC<HistoryTreeProps> = ({
  sessionId,
  onCommitSelect,
  onBranchCreate,
  onCommitRestore
}) => {
  const [history, setHistory] = useState<{ branches: Branch[]; commits: Commit[] } | null>(null);
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null);
  const [compareCommit, setCompareCommit] = useState<string | null>(null);
  const [showBranchModal, setShowBranchModal] = useState<string | null>(null);
  const [showDiffViewer, setShowDiffViewer] = useState<boolean>(false);
  const [showRestoreModal, setShowRestoreModal] = useState<string | null>(null);
  const [newBranchName, setNewBranchName] = useState('');
  const [restoreCreateBranch, setRestoreCreateBranch] = useState(false);

  useEffect(() => {
    loadHistory();
  }, [sessionId]);

  const loadHistory = async () => {
    try {
      const response = await fetch(`/api/chat/history/${sessionId}`);
      const data = await response.json();
      setHistory(data);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleCommitSelect = (commitHash: string) => {
    setSelectedCommit(commitHash);
    onCommitSelect?.(commitHash);
  };

  const handleBranchCreate = async () => {
    if (!showBranchModal || !newBranchName.trim()) return;

    try {
      await fetch('/api/chat/branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          from_commit: showBranchModal,
          branch_name: newBranchName
        })
      });
      
      onBranchCreate?.(showBranchModal, newBranchName);
      setShowBranchModal(null);
      setNewBranchName('');
      loadHistory();
    } catch (error) {
      console.error('Failed to create branch:', error);
    }
  };

  const handleCommitRestore = async () => {
    if (!showRestoreModal) return;

    try {
      const response = await fetch(`/api/git/sessions/${sessionId}/restore/${showRestoreModal}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          create_branch: restoreCreateBranch,
          branch_name: restoreCreateBranch ? newBranchName : undefined
        })
      });

      if (response.ok) {
        onCommitRestore?.(showRestoreModal);
        setShowRestoreModal(null);
        setNewBranchName('');
        setRestoreCreateBranch(false);
        loadHistory();
      }
    } catch (error) {
      console.error('Failed to restore commit:', error);
    }
  };

  const handleCompareSelect = (commitHash: string) => {
    if (!compareCommit) {
      setCompareCommit(commitHash);
    } else if (compareCommit === commitHash) {
      setCompareCommit(null);
    } else {
      setSelectedCommit(commitHash);
      setShowDiffViewer(true);
    }
  };

  const createCheckpoint = async () => {
    try {
      await fetch(`/api/git/sessions/${sessionId}/checkpoint`, {
        method: 'POST'
      });
      loadHistory();
    } catch (error) {
      console.error('Failed to create checkpoint:', error);
    }
  };

  if (!history) {
    return (
      <div className="p-4 text-center text-gray-500">
        Loading history...
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-50 overflow-auto">
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <GitBranch className="w-5 h-5" />
            Analysis History
          </h3>
          <button
            onClick={createCheckpoint}
            className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            title="Create checkpoint"
          >
            <Bookmark className="w-3 h-3" />
            Checkpoint
          </button>
        </div>

        {compareCommit && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm text-yellow-800">
                Comparing with {compareCommit.substring(0, 8)}. Select another commit to compare.
              </span>
              <button
                onClick={() => setCompareCommit(null)}
                className="text-yellow-600 hover:text-yellow-800"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Current Branch Info */}
        <div className="mb-4 p-3 bg-blue-50 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-700">
            <GitBranch className="w-4 h-4" />
            <span className="font-medium">
              Current: {history.branches.find(b => b.current)?.name || 'main'}
            </span>
          </div>
        </div>

        {/* Commit Tree */}
        <div className="space-y-2">
          {history.commits.map((commit, index) => (
            <div key={commit.hash} className="relative">
              {/* Connection Line */}
              {index < history.commits.length - 1 && (
                <div className="absolute left-4 top-8 w-px h-6 bg-gray-300"></div>
              )}
              
              {/* Commit Node */}
              <div
                className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedCommit === commit.hash
                    ? 'bg-blue-100 border-2 border-blue-300'
                    : 'bg-white border border-gray-200 hover:bg-gray-50'
                }`}
                onClick={() => handleCommitSelect(commit.hash)}
              >
                <div className="flex-shrink-0 mt-1">
                  <GitCommit className="w-4 h-4 text-gray-600" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {commit.message}
                    </span>
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      {commit.branch}
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      {new Date(commit.timestamp).toLocaleString()}
                    </span>
                    
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCommitSelect(commit.hash);
                        }}
                        className="p-1 text-gray-400 hover:text-blue-600 rounded"
                        title="View this analysis"
                      >
                        <Eye className="w-3 h-3" />
                      </button>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowRestoreModal(commit.hash);
                        }}
                        className="p-1 text-gray-400 hover:text-orange-600 rounded"
                        title="Restore to this state"
                      >
                        <RotateCcw className="w-3 h-3" />
                      </button>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCompareSelect(commit.hash);
                        }}
                        className={`p-1 rounded ${
                          compareCommit === commit.hash
                            ? 'text-yellow-600 bg-yellow-100'
                            : 'text-gray-400 hover:text-purple-600'
                        }`}
                        title="Compare commits"
                      >
                        <GitCompare className="w-3 h-3" />
                      </button>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowBranchModal(commit.hash);
                        }}
                        className="p-1 text-gray-400 hover:text-green-600 rounded"
                        title="Create branch from here"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  
                  <div className="text-xs text-gray-400 mt-1 font-mono">
                    {commit.hash.substring(0, 8)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Branch List */}
        {history.branches.length > 1 && (
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Branches</h4>
            <div className="space-y-1">
              {history.branches.map((branch) => (
                <div
                  key={branch.name}
                  className={`flex items-center gap-2 p-2 rounded text-sm ${
                    branch.current
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  <GitBranch className="w-3 h-3" />
                  <span className="font-medium">{branch.name}</span>
                  <span className="text-xs">({branch.commits.length} commits)</span>
                  {branch.current && (
                    <span className="ml-auto text-xs bg-blue-200 px-2 py-1 rounded">
                      current
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Branch Creation Modal */}
      {showBranchModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Create New Branch</h3>
            <p className="text-sm text-gray-600 mb-4">
              Create a new analysis branch from commit {showBranchModal.substring(0, 8)}
            </p>
            
            <input
              type="text"
              value={newBranchName}
              onChange={(e) => setNewBranchName(e.target.value)}
              placeholder="Enter branch name..."
              className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && handleBranchCreate()}
            />
            
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowBranchModal(null);
                  setNewBranchName('');
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleBranchCreate}
                disabled={!newBranchName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Create Branch
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Branch List */}
      {history.branches.length > 1 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Branches</h4>
          <div className="space-y-1">
            {history.branches.map((branch) => (
              <div
                key={branch.name}
                className={`flex items-center gap-2 p-2 rounded text-sm ${
                  branch.current
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                <GitBranch className="w-3 h-3" />
                <span className="font-medium">{branch.name}</span>
                <span className="text-xs">({branch.commits.length} commits)</span>
                {branch.current && (
                  <span className="ml-auto text-xs bg-blue-200 px-2 py-1 rounded">
                    current
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Restore Modal */}
      {showRestoreModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <RotateCcw className="w-5 h-5 text-orange-600" />
              Restore Analysis State
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Restore your analysis to commit {showRestoreModal.substring(0, 8)}. This will restore both the code and execution environment.
            </p>
            
            <div className="mb-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={restoreCreateBranch}
                  onChange={(e) => setRestoreCreateBranch(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Create new branch for exploration</span>
              </label>
            </div>

            {restoreCreateBranch && (
              <input
                type="text"
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                placeholder="Enter branch name..."
                className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            )}
            
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowRestoreModal(null);
                  setNewBranchName('');
                  setRestoreCreateBranch(false);
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCommitRestore}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
              >
                Restore
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Diff Viewer */}
      {showDiffViewer && selectedCommit && compareCommit && (
        <DiffViewer
          sessionId={sessionId}
          commitSha1={compareCommit}
          commitSha2={selectedCommit}
          onClose={() => {
            setShowDiffViewer(false);
            setCompareCommit(null);
            setSelectedCommit(null);
          }}
        />
      )}
    </div>
  );
};

export default HistoryTree;
