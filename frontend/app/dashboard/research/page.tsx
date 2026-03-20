'use client';

import { useState, useRef, useEffect } from 'react';
import TopBar from '@/components/TopBar';
import ChatMessage from '@/components/ChatMessage';
import SidePanel from '@/components/SidePanel';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  sources?: any;
  warnings?: string[];
  trigger_uncertainty?: boolean;
}

const FILTER_OPTIONS = [
  'All Laws',
  'IPC/BNS',
  'CrPC/BNSS',
  'Contract Act',
  'Companies Act',
  'Evidence Act',
  'Supreme Court',
  'High Courts',
];

const STARTER_QUESTIONS = [
  'What is the punishment for cheque bounce under NI Act?',
  'Explain Section 138 Negotiable Instruments Act',
  'What are the grounds for anticipatory bail?',
  'Key differences between IPC and BNS 2023',
];

export default function ResearchPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedFilters, setSelectedFilters] = useState<string[]>(['All Laws']);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [sidePanelContent, setSidePanelContent] = useState<{
    title: string;
    content: string;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const toggleFilter = (filter: string) => {
    if (filter === 'All Laws') {
      setSelectedFilters(['All Laws']);
    } else {
      const newFilters = selectedFilters.includes(filter)
        ? selectedFilters.filter((f) => f !== filter)
        : [...selectedFilters.filter((f) => f !== 'All Laws'), filter];

      if (newFilters.length === 0) {
        setSelectedFilters(['All Laws']);
      } else {
        setSelectedFilters(newFilters);
      }
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // Adjust textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      // Call backend API
      const response = await fetch('http://localhost:8000/api/legal/question', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: input,
          include_reasoning: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.answer,
        timestamp: new Date().toLocaleTimeString(),
        confidence: data.confidence,
        sources: data.sources,
        warnings: data.warnings,
        trigger_uncertainty: data.trigger_uncertainty,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content:
          'I apologize, but I encountered an error processing your request. Please ensure the backend server is running and try again.',
        timestamp: new Date().toLocaleTimeString(),
        confidence: 'LOW',
        trigger_uncertainty: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStarterQuestion = (question: string) => {
    setInput(question);
    textareaRef.current?.focus();
  };

  const handleSectionClick = (section: string) => {
    setSidePanelContent({
      title: 'Section Details',
      content: section,
    });
    setSidePanelOpen(true);
  };

  const handleCaseClick = (caseText: string) => {
    setSidePanelContent({
      title: 'Case Summary',
      content: caseText,
    });
    setSidePanelOpen(true);
  };

  const handleFeedback = async (messageIdx: number, helpful: boolean) => {
    console.log(`Feedback for message ${messageIdx}: ${helpful ? 'helpful' : 'not helpful'}`);
    // TODO: Send feedback to backend
    try {
      await fetch('http://localhost:8000/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query_id: messageIdx,
          response_id: messageIdx,
          rating: helpful ? 5 : 1,
          helpful: helpful,
          accurate: helpful,
          comment: '',
        }),
      });
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  return (
    <>
      <TopBar title="Legal Research" />

      <div className="flex flex-col h-[calc(100vh-4rem-3rem)]">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            <div className="max-w-4xl mx-auto mt-20">
              <div className="text-center mb-12">
                <h1 className="text-4xl font-bold text-[#1F3864] mb-4">
                  Legal Research Assistant
                </h1>
                <p className="text-lg text-gray-600">
                  Ask questions about Indian law, get citation-backed answers
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {STARTER_QUESTIONS.map((question, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleStarterQuestion(question)}
                    className="p-4 text-left bg-white border border-gray-200 rounded-lg hover:border-[#2E5499] hover:shadow-md transition-all"
                  >
                    <p className="text-sm text-gray-700">{question}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-6xl mx-auto">
              {messages.map((message, idx) => (
                <ChatMessage
                  key={idx}
                  {...message}
                  onSectionClick={handleSectionClick}
                  onCaseClick={handleCaseClick}
                  onFeedback={
                    message.role === 'assistant'
                      ? (helpful) => handleFeedback(idx, helpful)
                      : undefined
                  }
                />
              ))}
              {loading && (
                <div className="flex justify-start mb-6">
                  <div className="bg-white rounded-lg border border-gray-200 px-6 py-4 shadow-sm">
                    <div className="flex items-center gap-3 text-gray-500">
                      <div className="flex gap-1">
                        <span className="animate-bounce" style={{ animationDelay: '0ms' }}>
                          .
                        </span>
                        <span className="animate-bounce" style={{ animationDelay: '150ms' }}>
                          .
                        </span>
                        <span className="animate-bounce" style={{ animationDelay: '300ms' }}>
                          .
                        </span>
                      </div>
                      <span className="text-sm font-medium">Researching</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white px-6 py-4">
          <div className="max-w-4xl mx-auto">
            {/* Filters */}
            <div className="mb-3 flex flex-wrap gap-2">
              {FILTER_OPTIONS.map((filter) => (
                <button
                  key={filter}
                  onClick={() => toggleFilter(filter)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    selectedFilters.includes(filter)
                      ? 'bg-[#2E5499] text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>

            {/* Input */}
            <div className="flex gap-3">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ask a legal question... (Press Enter to send, Shift+Enter for new line)"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-[#2E5499] focus:border-transparent"
                rows={1}
                style={{ maxHeight: '200px' }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="px-6 py-3 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Side Panel */}
      <SidePanel
        isOpen={sidePanelOpen}
        onClose={() => setSidePanelOpen(false)}
        title={sidePanelContent?.title || ''}
      >
        <div className="prose max-w-none" style={{ fontFamily: 'Georgia, serif' }}>
          <p className="text-gray-800 whitespace-pre-wrap">{sidePanelContent?.content}</p>
        </div>
      </SidePanel>
    </>
  );
}
