import { useState, useRef, useEffect, FormEvent } from 'react';
import { Send, Sparkles, Menu, Plus, Trash2, Bot, User, AlertCircle, LayoutDashboard, Shield, ChevronRight, ChevronLeft } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import api from '../lib/api';
import axios from 'axios';
import IncidentDashboard from '../components/IncidentDashboard';
import ObserverWidget from '../components/ObserverWidget';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isError?: boolean;
  reasoning_trace?: ReasoningStep[];
}

interface ReasoningStep {
  step: string;
  thought: string;
  timestamp: string;
  details?: Record<string, any>;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  lastUpdated: string;
}

const DEFAULT_ASSISTANT_MESSAGE: Message = {
  role: 'assistant',
  content: `👋 Hi! I'm **ElasticSeer**, your autonomous incident response agent.

I can help you with:
- 🔍 Investigating incidents and anomalies
- 📊 Analyzing metrics and logs
- 🔧 Generating fixes for code issues
- 🚀 Creating GitHub PRs automatically
- 📝 Searching code repositories

Ask me anything about your infrastructure, incidents, or code!`,
  timestamp: new Date().toISOString(),
};

export default function AgentChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([DEFAULT_ASSISTANT_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  const [rightSidebarTab, setRightSidebarTab] = useState<'incidents' | 'observer'>('incidents');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load conversations from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('elasticseer_conversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        const uniqueConvs = parsed.filter(
          (conv: Conversation, index: number, self: Conversation[]) =>
            index === self.findIndex((c) => c.id === conv.id)
        );
        setConversations(uniqueConvs);
        if (uniqueConvs.length > 0) {
          const latest = uniqueConvs[0];
          setCurrentConversationId(latest.id);
          setMessages(latest.messages);
        }
      } catch (e) {
        console.error('Failed to load conversations', e);
      }
    }
  }, []);

  // Save conversations to localStorage
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem('elasticseer_conversations', JSON.stringify(conversations));
    }
  }, [conversations]);

  // Update current conversation when messages change
  useEffect(() => {
    if (currentConversationId && messages.length > 1) {
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === currentConversationId
            ? {
              ...conv,
              messages,
              lastUpdated: new Date().toISOString(),
              title:
                conv.title === 'New Chat'
                  ? messages.find((m) => m.role === 'user')?.content.slice(0, 50) || 'New Chat'
                  : conv.title,
            }
            : conv
        )
      );
    }
  }, [messages, currentConversationId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [input]);

  // Initialize first conversation if none exist
  useEffect(() => {
    if (conversations.length === 0) {
      startNewChat();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startNewChat = () => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      title: 'New Chat',
      messages: [DEFAULT_ASSISTANT_MESSAGE],
      lastUpdated: new Date().toISOString(),
    };
    setConversations((prev) => [newConv, ...prev]);
    setCurrentConversationId(newConv.id);
    setMessages([DEFAULT_ASSISTANT_MESSAGE]);
  };

  const switchConversation = (convId: string) => {
    const conv = conversations.find((c) => c.id === convId);
    if (conv) {
      setCurrentConversationId(conv.id);
      setMessages(conv.messages);
    }
  };

  const deleteConversation = (convId: string) => {
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== convId);
      if (currentConversationId === convId) {
        if (filtered.length > 0) {
          const next = filtered[0];
          setCurrentConversationId(next.id);
          setMessages(next.messages);
        } else {
          startNewChat();
        }
      }
      return filtered;
    });
  };

  const clearConversation = () => {
    if (currentConversationId) {
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === currentConversationId
            ? { ...conv, messages: [DEFAULT_ASSISTANT_MESSAGE] }
            : conv
        )
      );
    }
    setMessages([DEFAULT_ASSISTANT_MESSAGE]);
  };

  const handleIncidentClick = (incidentId: string) => {
    setInput(`Show incident ${incidentId}`);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await api.post('/api/agent/chat_enhanced', {
        message: input.trim(),
        conversation_history: messages.filter((m) => m.role !== 'system'),
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response || 'I received your message but had trouble generating a response.',
        timestamp: new Date().toISOString(),
        reasoning_trace: response.data.reasoning_trace,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: `❌ **Error**: ${axios.isAxiosError(error) ? error.message : 'Failed to communicate with the agent. Please check your connection and try again.'}`,
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const quickPrompts = [
    'Analyze metrics for api-gateway',
    'Compare service health',
    'Show active anomalies',
    'Show incident statistics',
  ];

  return (
    <div className="min-h-screen bg-elastic-lightGray flex">
      {/* Sidebar */}
      <aside
        className={`${sidebarOpen ? 'w-64' : 'w-0'
          } transition-all duration-300 border-r border-elastic-border bg-white flex flex-col overflow-hidden`}
      >
        <div className="p-3 border-b border-elastic-border">
          <button
            onClick={startNewChat}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-elastic-blue text-white hover:bg-elastic-darkBlue transition-colors text-sm font-medium"
          >
            <Plus className="h-4 w-4" />
            New conversation
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`w-full group flex items-center justify-between gap-2 px-3 py-2 rounded-md mb-1 transition-colors cursor-pointer ${currentConversationId === conv.id
                ? 'bg-elastic-lightBlue text-elastic-darkBlue'
                : 'text-elastic-gray hover:bg-elastic-lightGray'
                }`}
              onClick={() => switchConversation(conv.id)}
            >
              <span className="text-sm truncate flex-1">{conv.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conv.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-elastic-border rounded transition-opacity"
                aria-label="Delete conversation"
              >
                <Trash2 className="h-3 w-3 text-elastic-gray" />
              </button>
            </div>
          ))}
        </div>

        <div className="p-3 border-t border-elastic-border">
          <div className="flex items-center gap-2 text-xs text-elastic-gray">
            <Bot className="h-4 w-4" />
            <span className="font-semibold">ElasticSeer Agent</span>
          </div>
          <div className="text-xs text-elastic-gray mt-1">Powered by Kibana Agent Builder</div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-elastic-border px-6 py-3 shadow-sm flex-shrink-0">
          <div className="flex items-center justify-between gap-4 max-w-[1600px] mx-auto w-full">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="text-elastic-gray hover:text-elastic-darkGray p-1.5 rounded-md hover:bg-elastic-lightGray"
              >
                <Menu className="h-5 w-5" />
              </button>
              <div className="flex items-center gap-2">
                <Bot className="h-6 w-6 text-elastic-blue" />
                <h1 className="text-lg font-semibold text-elastic-darkGray">ElasticSeer</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {messages.length > 1 && (
                <button
                  onClick={clearConversation}
                  className="text-sm text-elastic-gray hover:text-elastic-darkGray px-3 py-1.5 rounded-md hover:bg-elastic-lightGray transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Split View: Chat + Dashboard/Observer */}
        <div className="flex-1 flex gap-4 p-4 overflow-hidden max-w-[1600px] mx-auto w-full">
          {/* Chat Section */}
          <main className="flex-[2] flex flex-col overflow-hidden bg-white border border-elastic-border rounded-lg shadow-sm">
            {/* Messages */}
            <section className="flex-1 overflow-y-auto space-y-4 p-4 pr-2">
              {messages.map((message, index) => (
                <article
                  key={`${message.timestamp}-${index}`}
                  className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  {/* Avatar */}
                  <div
                    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.role === 'user'
                      ? 'bg-elastic-blue text-white'
                      : message.isError
                        ? 'bg-red-100 text-red-600'
                        : 'bg-elastic-lightBlue text-elastic-blue'
                      }`}
                  >
                    {message.role === 'user' ? (
                      <User className="h-4 w-4" />
                    ) : message.isError ? (
                      <AlertCircle className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div
                    className={`flex-1 rounded-lg px-4 py-3 ${message.role === 'user'
                      ? 'bg-elastic-blue text-white'
                      : message.isError
                        ? 'bg-red-50 border border-red-200 shadow-sm'
                        : 'bg-white border border-elastic-border shadow-sm'
                      }`}
                  >
                    <div
                      className={`markdown-content ${message.role === 'user' ? 'text-white' : 'text-elastic-darkGray'
                        }`}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    </div>

                    {/* Reasoning Trace */}
                    {message.reasoning_trace && message.reasoning_trace.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-elastic-border/50">
                        <details className="group">
                          <summary className="flex items-center gap-2 text-[10px] font-bold text-elastic-gray uppercase tracking-widest cursor-pointer hover:text-elastic-blue transition-colors list-none">
                            <Sparkles className="h-3 w-3 animate-pulse-subtle" />
                            <span>Reasoning Trace</span>
                            <ChevronRight className="h-3 w-3 group-open:rotate-90 transition-transform" />
                          </summary>
                          <div className="mt-2 space-y-2 pl-2 border-l-2 border-elastic-border/30">
                            {message.reasoning_trace.map((step, sIdx) => (
                              <div key={sIdx} className="text-xs">
                                <span className="font-semibold text-elastic-darkGray block">{step.step}</span>
                                <span className="text-elastic-gray italic">{step.thought}</span>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}
                    <div
                      className={`text-xs mt-2 ${message.role === 'user' ? 'text-blue-100' : 'text-elastic-gray'
                        }`}
                    >
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </article>
              ))}

              {/* Loading Indicator */}
              {isLoading && (
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-elastic-lightBlue text-elastic-blue flex items-center justify-center">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="flex-1 rounded-lg px-4 py-3 bg-white border border-elastic-border shadow-sm">
                    <div className="flex items-center gap-2 text-sm text-elastic-gray">
                      <Sparkles className="h-4 w-4 animate-pulse-subtle text-elastic-blue" />
                      <span>ElasticSeer is thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </section>

            {/* Input Wrapper */}
            <div className="p-4 border-t border-elastic-border bg-slate-50/50">
              {/* Quick Prompts */}
              {messages.length === 1 && (
                <section className="grid gap-2 sm:grid-cols-2 mb-4">
                  {quickPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => setInput(prompt)}
                      className="text-left rounded-md border border-elastic-border bg-white px-4 py-2 text-xs text-elastic-darkGray hover:bg-elastic-lightGray hover:border-elastic-blue transition-colors shadow-sm"
                    >
                      {prompt}
                    </button>
                  ))}
                </section>
              )}

              {/* Input Form */}
              <form onSubmit={handleSubmit} className="relative bg-white rounded-lg border border-elastic-border shadow-md">
                <textarea
                  ref={textareaRef}
                  rows={1}
                  className="w-full bg-transparent border-none rounded-lg px-4 py-3 pr-12 resize-none focus:outline-none focus:ring-2 focus:ring-elastic-blue text-elastic-darkGray placeholder:text-elastic-gray text-sm"
                  placeholder="Ask ElasticSeer anything..."
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      handleSubmit(event as unknown as FormEvent<HTMLFormElement>);
                    }
                  }}
                  disabled={isLoading}
                  required
                />
                <button
                  type="submit"
                  disabled={isLoading || !input.trim()}
                  className="absolute right-2 bottom-2 h-8 w-8 rounded-md bg-elastic-blue hover:bg-elastic-darkBlue text-white disabled:bg-elastic-gray disabled:cursor-not-allowed transition-all flex items-center justify-center shadow-sm"
                >
                  {isLoading ? (
                    <Sparkles className="h-4 w-4 animate-pulse-subtle" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </form>
            </div>
          </main>

          {/* Right Sidebar: Fixed Overlay Panel */}
          {rightSidebarOpen && (
            <aside className="fixed right-0 top-0 z-30 w-[400px] h-screen flex flex-col bg-elastic-lightGray border-l border-elastic-border shadow-xl transition-all duration-300 ease-in-out">
              {/* Tab Switcher & Collapse */}
              <div className="flex items-center gap-2 p-3 flex-shrink-0">
                <div className="flex-1 flex p-1 bg-white border border-elastic-border rounded-lg shadow-sm">
                  <button
                    onClick={() => setRightSidebarTab('incidents')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold rounded-md transition-all ${rightSidebarTab === 'incidents'
                      ? 'bg-elastic-blue text-white shadow-sm'
                      : 'text-elastic-gray hover:bg-elastic-lightGray'
                      }`}
                  >
                    <LayoutDashboard className="h-4 w-4" />
                    INCIDENTS
                  </button>
                  <button
                    onClick={() => setRightSidebarTab('observer')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold rounded-md transition-all ${rightSidebarTab === 'observer'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-elastic-gray hover:bg-elastic-lightGray'
                      }`}
                  >
                    <Shield className="h-4 w-4" />
                    OBSERVER
                  </button>
                </div>
                <button
                  onClick={() => setRightSidebarOpen(false)}
                  className="p-2 bg-white border border-elastic-border rounded-lg shadow-sm text-elastic-gray hover:text-elastic-blue hover:bg-elastic-lightGray transition-all"
                  title="Collapse Sidebar"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-3 pt-0">
                {rightSidebarTab === 'incidents' ? (
                  <div className="bg-white border border-elastic-border rounded-lg shadow-sm">
                    <IncidentDashboard onIncidentClick={handleIncidentClick} />
                  </div>
                ) : (
                  <ObserverWidget />
                )}
              </div>
            </aside>
          )}
          {/* Mini Toggle when collapsed */}
          {!rightSidebarOpen && (
            <div className="fixed right-4 top-24 z-10 flex flex-col gap-2">
              <button
                onClick={() => setRightSidebarOpen(true)}
                className="p-3 bg-white border border-elastic-border rounded-full shadow-lg text-elastic-blue hover:bg-elastic-blue hover:text-white transition-all group scale-90 hover:scale-100"
                title="Expand Monitoring"
              >
                <ChevronLeft className="h-5 w-5" />
                <div className="absolute right-full mr-2 px-2 py-1 bg-slate-900 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 whitespace-nowrap pointer-events-none transition-opacity">
                  Expand Monitoring
                </div>
              </button>
              <button
                onClick={() => {
                  setRightSidebarTab('incidents');
                  setRightSidebarOpen(true);
                }}
                className={`p-3 bg-white border border-elastic-border rounded-full shadow-lg transition-all ${rightSidebarTab === 'incidents' ? 'text-elastic-blue ring-2 ring-elastic-blue' : 'text-slate-400'}`}
              >
                <LayoutDashboard className="h-5 w-5" />
              </button>
              <button
                onClick={() => {
                  setRightSidebarTab('observer');
                  setRightSidebarOpen(true);
                }}
                className={`p-3 bg-white border border-elastic-border rounded-full shadow-lg transition-all ${rightSidebarTab === 'observer' ? 'text-indigo-600 ring-2 ring-indigo-600' : 'text-slate-400'}`}
              >
                <Shield className="h-5 w-5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
