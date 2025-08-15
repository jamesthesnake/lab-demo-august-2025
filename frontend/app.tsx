"""
Update your main App component to include the chat interface
"""

import React, { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import CodeEditor from './components/CodeEditor';  // Your existing editor

function App() {
  const [sessionId] = useState(() => {
    // Generate or retrieve session ID
    return localStorage.getItem('sessionId') || 
           `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  });
  
  const [editorCode, setEditorCode] = useState('');
  const [activeTab, setActiveTab] = useState<'chat' | 'editor'>('chat');

  const handleCodeInsert = (code: string) => {
    setEditorCode(code);
    setActiveTab('editor');
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
              AIDO Lab
            </h1>
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab('chat')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'chat' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                AI Chat
              </button>
              <button
                onClick={() => setActiveTab('editor')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'editor' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                Code Editor
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 h-[calc(100vh-64px)]">
        <div className="grid grid-cols-12 gap-6 h-full">
          {/* Left Panel - Session History */}
          <div className="col-span-2 bg-gray-800 rounded-lg p-4 overflow-y-auto">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Sessions</h3>
            <div className="space-y-2">
              <div className="bg-gray-700 rounded p-2 text-sm text-gray-300 cursor-pointer hover:bg-gray-600">
                Current Session
              </div>
            </div>
          </div>

          {/* Center Panel - Chat or Editor */}
          <div className="col-span-7 bg-gray-800 rounded-lg overflow-hidden">
            {activeTab === 'chat' ? (
              <ChatInterface 
                sessionId={sessionId} 
                onCodeInsert={handleCodeInsert}
              />
            ) : (
              <CodeEditor 
                code={editorCode}
                onChange={setEditorCode}
                sessionId={sessionId}
              />
            )}
          </div>

          {/* Right Panel - Results/Artifacts */}
          <div className="col-span-3 bg-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Results</h3>
            <div className="bg-gray-900 rounded p-3 h-[calc(100%-32px)] overflow-auto">
              <p className="text-gray-500 text-sm">
                Outputs and visualizations will appear here
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
