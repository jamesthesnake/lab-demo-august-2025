import React, { useState, useEffect } from 'react';
import { GitBranch, Plus, ChevronDown, Check, X } from 'lucide-react';

interface Branch {
  name: string;
  current: boolean;
  lastCommit?: string;
}

interface BranchManagerProps {
  sessionId: string;
  onBranchSwitch?: (branchName: string) => void;
  onBranchCreate?: (branchName: string, fromBranch?: string) => void;
}

export const BranchManager: React.FC<BranchManagerProps> = ({
  sessionId,
  onBranchSwitch,
  onBranchCreate
}) => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [currentBranch, setCurrentBranch] = useState<string>('main');
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newBranchName, setNewBranchName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadBranches();
  }, [sessionId]);

  const loadBranches = async () => {
    if (typeof window === 'undefined') return;
    
    try {
      const response = await fetch(`http://localhost:8000/api/git/sessions/${sessionId}/branches`);
      if (response.ok) {
        const data = await response.json();
        setBranches(data.branches || []);
        setCurrentBranch(data.current_branch || 'main');
      }
    } catch (error) {
      console.error('Failed to load branches:', error);
      // Default to main branch if API fails
      setBranches([{ name: 'main', current: true }]);
      setCurrentBranch('main');
    }
  };

  const handleBranchSwitch = async (branchName: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/git/sessions/${sessionId}/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch: branchName })
      });
      
      if (response.ok) {
        setCurrentBranch(branchName);
        setIsOpen(false);
        onBranchSwitch?.(branchName);
        loadBranches();
      }
    } catch (error) {
      console.error('Failed to switch branch:', error);
    }
  };

  const handleCreateBranch = async () => {
    if (!newBranchName.trim()) return;
    
    setIsCreating(true);
    try {
      const response = await fetch(`http://localhost:8000/api/git/sessions/${sessionId}/branches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name: newBranchName,
          from_branch: currentBranch 
        })
      });
      
      if (response.ok) {
        setNewBranchName('');
        setShowCreateModal(false);
        onBranchCreate?.(newBranchName, currentBranch);
        loadBranches();
      }
    } catch (error) {
      console.error('Failed to create branch:', error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="relative">
      {/* Branch Dropdown Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg border border-slate-600/50 transition-colors"
      >
        <GitBranch className="w-4 h-4 text-cyan-400" />
        <span className="text-sm font-medium text-white">{currentBranch}</span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-slate-800 rounded-lg border border-slate-600/50 shadow-xl z-50">
          <div className="p-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">Branches</span>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-cyan-600 hover:bg-cyan-500 rounded transition-colors"
              >
                <Plus className="w-3 h-3" />
                New
              </button>
            </div>
            
            {/* Branch List */}
            <div className="space-y-1">
              {branches.map((branch) => (
                <button
                  key={branch.name}
                  onClick={() => handleBranchSwitch(branch.name)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                    branch.name === currentBranch
                      ? 'bg-cyan-600/20 text-cyan-400'
                      : 'hover:bg-slate-700/50 text-slate-300'
                  }`}
                >
                  <GitBranch className="w-3 h-3" />
                  <span className="flex-1 text-left">{branch.name}</span>
                  {branch.name === currentBranch && <Check className="w-3 h-3" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Create Branch Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-600/50 p-6 w-96">
            <h3 className="text-lg font-semibold text-white mb-4">Create New Branch</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Branch Name
                </label>
                <input
                  type="text"
                  value={newBranchName}
                  onChange={(e) => setNewBranchName(e.target.value)}
                  placeholder="feature/new-feature"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  autoFocus
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Create from
                </label>
                <div className="flex items-center gap-2 px-3 py-2 bg-slate-700/50 rounded-md">
                  <GitBranch className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm text-white">{currentBranch}</span>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleCreateBranch}
                disabled={!newBranchName.trim() || isCreating}
                className="flex-1 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-md text-white font-medium transition-colors"
              >
                {isCreating ? 'Creating...' : 'Create Branch'}
              </button>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setNewBranchName('');
                }}
                className="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-md text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default BranchManager;
