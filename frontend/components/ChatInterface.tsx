import React, { useState, useEffect, useRef } from 'react';
import { Send, Code, GitBranch, Image, Table, Loader } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  tool_results?: {
    stdout: string;
    stderr: string;
    artifacts: string[];
  };
  timestamp: string;
}

interface ChatInterfaceProps {
  sessionId: string;
  onCodeInsert?: (code: string) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId, onCodeInsert }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCode, setShowCode] = useState<string | null>(null);
  const [history, setHistory] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load history on mount
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

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: input
        })
      });

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.assistant_message || '(No response)',
        tool_results: data.tool_results ? {
          stdout: data.tool_results.stdout || '',
          stderr: data.tool_results.stderr || '',
          artifacts: data.artifacts || []
        } : undefined,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Refresh history to show new commit
      loadHistory();
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const extractCode = (content: string): string | null => {
    const codeMatch = content.match(/```python\n([\s\S]*?)```/);
    return codeMatch ? codeMatch[1] : null;
  };

  const createBranch = async (fromCommit: string) => {
    const branchName = prompt('Enter branch name:');
    if (!branchName) return;

    try {
      await fetch('/api/chat/branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          from_commit: fromCommit,
          branch_name: branchName
        })
      });
      loadHistory();
    } catch (error) {
      console.error('Failed to create branch:', error);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 px-6 py-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">AI Chat</h2>
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">
              {history?.current_branch || 'main'}
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-100'
              }`}
            >
              <div className="whitespace-pre-wrap">{message.content}</div>
              
              {/* Tool results */}
              {message.tool_results && (
                <div className="mt-4 space-y-2">
                  {message.tool_results.stdout && (
                    <div className="bg-black rounded p-3">
                      <div className="text-xs text-gray-400 mb-1">Output:</div>
                      <pre className="text-green-400 text-sm overflow-x-auto">
                        {message.tool_results.stdout}
                      </pre>
                    </div>
                  )}
                  
                  {message.tool_results.stderr && (
                    <div className="bg-black rounded p-3">
                      <div className="text-xs text-gray-400 mb-1">Errors:</div>
                      <pre className="text-red-400 text-sm overflow-x-auto">
                        {message.tool_results.stderr}
                      </pre>
                    </div>
                  )}
                  
                  {message.tool_results.artifacts.length > 0 && (
                    <div className="mt-4 space-y-3">
                      {message.tool_results.artifacts.map((artifact, i) => (
                        <div key={i} className="border border-gray-600 rounded-lg overflow-hidden">
                          {artifact.endsWith('.png') || artifact.endsWith('.jpg') || artifact.endsWith('.jpeg') || artifact.endsWith('.gif') ? (
                            <div className="bg-white p-2">
                              <img 
                                src={`http://localhost:8000${artifact}`}
                                alt={`Generated plot ${i + 1}`}
                                className="max-w-full h-auto rounded"
                                onError={(e) => {
                                  console.error('Failed to load image:', artifact);
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                              <div className="flex items-center justify-between mt-2 text-xs text-gray-600">
                                <span className="flex items-center gap-1">
                                  <Image className="w-3 h-3" />
                                  {artifact.split('/').pop()}
                                </span>
                                <a
                                  href={`http://localhost:8000${artifact}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800"
                                >
                                  Open full size
                                </a>
                              </div>
                            </div>
                          ) : (
                            <div className="p-3 bg-gray-700">
                              <a
                                href={`http://localhost:8000${artifact}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-gray-300 hover:text-white"
                              >
                                <Table className="w-4 h-4" />
                                <span>{artifact.split('/').pop()}</span>
                              </a>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              
              {/* Code extraction button */}
              {message.role === 'assistant' && extractCode(message.content) && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => setShowCode(extractCode(message.content))}
                    className="flex items-center gap-1 px-3 py-1 bg-gray-700 rounded text-xs text-gray-300 hover:bg-gray-600"
                  >
                    <Code className="w-3 h-3" />
                    View Code
                  </button>
                  {onCodeInsert && (
                    <button
                      onClick={() => {
                        const code = extractCode(message.content);
                        if (code) onCodeInsert(code);
                      }}
                      className="flex items-center gap-1 px-3 py-1 bg-green-700 rounded text-xs text-gray-300 hover:bg-green-600"
                    >
                      Insert to Editor
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg px-4 py-3 flex items-center gap-2">
              <Loader className="w-4 h-4 animate-spin text-gray-400" />
              <span className="text-gray-400">Thinking...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-700 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Ask me to analyze data, create visualizations, or write code..."
            className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Code modal */}
      {showCode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-4xl w-full max-h-[80vh] overflow-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-white">Generated Code</h3>
              <button
                onClick={() => setShowCode(null)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <pre className="bg-black rounded p-4 overflow-x-auto">
              <code className="text-green-400">{showCode}</code>
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
