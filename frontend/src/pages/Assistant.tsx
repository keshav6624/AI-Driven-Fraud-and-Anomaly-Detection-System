import { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  data?: any[];
  vizHint?: string;
  timestamp: Date;
}

const SUGGESTIONS = [
  "How many MPs are there?",
  "Show me high risk MPs",
  "Which MPs have anomalies?",
  "Find MP from Delhi",
  "Show top allocations",
  "Compare risk by state",
  "Show duplicate records",
  "Summary of MPLADS data",
];

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hello! I'm the MPLAD-Sentinel AI Assistant. I can help you query MPLADS data using natural language. Try asking me questions like:\n\n- How many MPs are there?\n- Show high risk MPs\n- Find MP from Maharashtra\n- What are the anomalies?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSql, setShowSql] = useState<number | null>(null);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (question?: string) => {
    const q = question || input.trim();
    if (!q || loading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q, timestamp: new Date() }]);
    setLoading(true);

    try {
      const res = await api.askAssistant(q);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        sql: res.sql,
        data: res.data ?? undefined,
        vizHint: res.visualization_hint ?? undefined,
        timestamp: new Date(),
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message || 'Failed to process your question'}`,
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold">AI Assistant</h1>
        <p className="text-sm text-gray-500">Natural language queries powered by AI/ML</p>
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} onClick={() => handleSend(s)}
              className="bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 hover:bg-primary-50 hover:border-primary-300 transition-colors">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-3xl rounded-xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-primary-600 text-white'
                : 'bg-white border border-gray-200 shadow-sm'
            }`}>
              <div className="whitespace-pre-wrap text-sm">{msg.content}</div>

              {/* Data table */}
              {msg.data && msg.data.length > 0 && (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-gray-200">
                        {Object.keys(msg.data[0]).map(k => (
                          <th key={k} className="text-left px-2 py-1 font-medium text-gray-500">{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {msg.data.slice(0, 10).map((row, ri) => (
                        <tr key={ri} className="border-b border-gray-100">
                          {Object.values(row).map((v, vi) => (
                            <td key={vi} className="px-2 py-1 text-gray-700">
                              {v == null ? '—' : typeof v === 'number' ? Number(v).toLocaleString() : String(v)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {msg.data.length > 10 && (
                    <p className="text-xs text-gray-400 mt-1">Showing 10 of {msg.data.length} rows</p>
                  )}
                </div>
              )}

              {/* SQL toggle */}
              {msg.sql && (
                <div className="mt-2">
                  <button onClick={() => setShowSql(showSql === i ? null : i)}
                    className="text-xs text-primary-500 hover:text-primary-700">
                    {showSql === i ? 'Hide SQL' : 'Show SQL'}
                  </button>
                  {showSql === i && (
                    <pre className="mt-1 bg-gray-50 rounded p-2 text-xs text-gray-600 overflow-x-auto">{msg.sql}</pre>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 shadow-sm rounded-xl px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <div className="animate-spin w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full" />
                Thinking...
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input type="text" value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask a question about MPLADS data..."
          className="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none shadow-sm"
          disabled={loading} />
        <button onClick={() => handleSend()} disabled={loading || !input.trim()}
          className="bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors shadow-sm">
          Ask
        </button>
      </div>
    </div>
  );
}
