import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Mic,
  Send,
  Play,
  Pause,
  Square,
  RotateCcw,
  Sun,
  Clock,
  Briefcase,
  Search,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useAssistant } from '@/contexts/AssistantContext';
import { VoiceWaveform } from './VoiceWaveform';
import { AptlyLogo } from '@/components/common/AptlyLogo';

export const AptlyAssistantDrawer: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const {
    isOpen,
    closeAssistant,
    activeTab,
    setActiveTab,
    messages,
    isLoading,
    loadingStage,
    voiceState,
    voiceErrorMessage,
    currentSpeakingId,
    isSpeechRecognitionSupported,
    sendMessage,
    stopListening,
    toggleListening,
    playAudio,
    pauseAudio,
    resumeAudio,
    stopAudio,
    replayAudio,
    briefingData,
    briefingLoading,
    loadBriefing,
    newConversation,
  } = useAssistant();

  const [inputText, setInputText] = useState('');
  const [hasPlayedBriefing, setHasPlayedBriefing] = useState(false);
  const [playedMessageIds, setPlayedMessageIds] = useState<Set<string>>(new Set());

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Dynamic user first name
  const firstName = useMemo(() => {
    if (!user?.name) return 'there';
    const first = user.name.trim().split(' ')[0];
    return first.charAt(0).toUpperCase() + first.slice(1);
  }, [user?.name]);

  // Dynamic time of day greeting
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return `Good morning, ${firstName}.`;
    if (hour < 18) return `Good afternoon, ${firstName}.`;
    return `Good evening, ${firstName}.`;
  }, [firstName]);

  // Formatted date (e.g., "Tuesday, September 23")
  const formattedToday = useMemo(() => {
    return new Intl.DateTimeFormat('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    }).format(new Date());
  }, []);

  // Auto-scroll messages
  useEffect(() => {
    if (activeTab === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeTab, isLoading]);

  // Focus textarea when opened
  useEffect(() => {
    if (isOpen && activeTab === 'chat') {
      setTimeout(() => textareaRef.current?.focus(), 150);
    }
  }, [isOpen, activeTab]);

  // Close drawer on Escape key for keyboard accessibility
  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeAssistant();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, closeAssistant]);

  if (!isOpen) return null;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (!inputText.trim() || isLoading) return;
    const text = inputText;
    setInputText('');
    sendMessage(text);
  };

  const handleActionClick = (route: string) => {
    closeAssistant();
    navigate(route);
  };

  // Quick Command rows
  const quickCommands = [
    {
      icon: <Sun size={15} className="text-[#3D5580]" />,
      label: 'Daily briefing',
      action: () => {
        setActiveTab('briefing');
        if (!briefingData) loadBriefing();
      },
    },
    {
      icon: <Clock size={15} className="text-[#3D5580]" />,
      label: "What's coming up?",
      action: () => sendMessage("What's coming up this week in terms of deadlines, interviews, or assessments?"),
    },
    {
      icon: <Briefcase size={15} className="text-[#3D5580]" />,
      label: 'Application progress',
      action: () => sendMessage('What is the status and progress of my tracked applications?'),
    },
    {
      icon: <Search size={15} className="text-[#3D5580]" />,
      label: 'Best new matches',
      action: () => sendMessage('What are my best new job matches right now?'),
    },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-black/25 backdrop-blur-[2px] transition-opacity duration-200">
      {/* Backdrop */}
      <div className="absolute inset-0" onClick={closeAssistant} />

      {/* Drawer Panel */}
      <div className="relative w-full sm:w-[460px] bg-[#FFFFFF] shadow-2xl flex flex-col h-full z-10 border-l border-[#E2E2E2] transition-transform duration-250 ease-out font-sans">
        
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-[#E2E2E2] bg-[#FFFFFF] flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <AptlyLogo height={22} variant="full" />
              <span className="text-[#E2E2E2]">|</span>
              <span className="text-[12px] font-medium text-[#6B6B6B]">Career Intelligence</span>
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
              <span className="text-[11px] text-[#6B6B6B]">Ready</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* New Conversation Button */}
            {messages.length > 0 && activeTab === 'chat' && (
              <button
                type="button"
                onClick={newConversation}
                className="text-[11.5px] font-medium text-[#6B6B6B] hover:text-[#1A1A1A] px-2 py-1 rounded hover:bg-[#F3F4F6] transition-colors cursor-pointer"
              >
                New conversation
              </button>
            )}

            {/* Close Button */}
            <button
              type="button"
              onClick={closeAssistant}
              className="p-1.5 text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F3F4F6] rounded-md transition-colors cursor-pointer"
              title="Close (Esc)"
            >
              <X size={17} />
            </button>
          </div>
        </div>

        {/* Signature Horizontal Voice Waveform Bar */}
        <div className="border-b border-[#F0F0F0] bg-[#FAFAFA] py-1.5 px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <Mic size={13} className="text-[#1B2A4A]" />
            <span className="text-[11.5px] font-medium text-[#1B2A4A]">
              {voiceState === 'listening'
                ? 'Listening to speech...'
                : voiceState === 'thinking'
                ? loadingStage
                : voiceState === 'generating'
                ? 'Generating voice...'
                : voiceState === 'playing'
                ? 'Speaking...'
                : voiceState === 'paused'
                ? 'Voice paused'
                : voiceErrorMessage
                ? voiceErrorMessage
                : 'Aptly Voice Assistant'}
            </span>
          </div>
          <VoiceWaveform state={voiceState} />
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
          
          {/* TAB 1: Chat View */}
          {activeTab === 'chat' && (
            <>
              {/* Initial Greeting & Quick Commands */}
              {messages.length === 0 ? (
                <div className="space-y-6 pt-2 animate-fade-in">
                  <div>
                    <h2 className="font-serif text-[22px] font-bold text-[#1A1A1A] leading-snug">
                      {greeting}
                    </h2>
                    <p className="text-[13.5px] text-[#6B6B6B] mt-1">
                      What would you like to know?
                    </p>
                  </div>

                  {/* Compact Command Rows */}
                  <div className="space-y-1.5 pt-1">
                    {quickCommands.map((cmd, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={cmd.action}
                        className="w-full text-left px-3.5 py-3 rounded-lg border border-[#E2E2E2] hover:border-[#CBD5E1] bg-white hover:bg-[#F5F8FC] text-[13px] font-medium text-[#1A1A1A] transition-all duration-150 flex items-center justify-between group cursor-pointer"
                      >
                        <div className="flex items-center gap-3">
                          {cmd.icon}
                          <span>{cmd.label}</span>
                        </div>
                        <span className="text-[#6B6B6B] text-[12px] group-hover:translate-x-0.5 transition-transform duration-150">
                          →
                        </span>
                      </button>
                    ))}
                  </div>

                  <div className="pt-2 border-t border-[#F0F0F0]">
                    <p className="text-[11.5px] text-[#6B6B6B] leading-relaxed">
                      Ask about applications, upcoming deadlines, resume match against requirements, or get grounded advice based on your workspace.
                    </p>
                  </div>
                </div>
              ) : (
                /* Message Stream */
                <div className="space-y-6">
                  {messages.map((msg) => {
                    const isUser = msg.sender === 'user';
                    const isCurrentSpeaking = currentSpeakingId === msg.id;

                    if (isUser) {
                      return (
                        <div key={msg.id} className="flex justify-end">
                          <div className="max-w-[85%] bg-[#F3F4F6] text-[#1A1A1A] text-[13px] px-3.5 py-2 rounded-xl rounded-br-xs font-normal">
                            {msg.text}
                          </div>
                        </div>
                      );
                    }

                    // Aptly Response rendered directly on canvas
                    return (
                      <div key={msg.id} className="space-y-2.5 pt-1">
                        <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-[#6B6B6B]">
                          <span>APTLY</span>
                          <span>
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>

                        <div className="text-[13.5px] text-[#1A1A1A] leading-relaxed font-normal whitespace-pre-line">
                          {msg.text}
                        </div>

                        {/* Audio Controls for this response (mutually exclusive) */}
                        <div className="flex items-center gap-3 pt-1">
                          {isCurrentSpeaking && voiceState === 'generating' ? (
                            <span className="text-[12px] text-[#6B6B6B] italic">Generating voice...</span>
                          ) : isCurrentSpeaking && voiceState === 'playing' ? (
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={pauseAudio}
                                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#1B2A4A] hover:text-[#3D5580] cursor-pointer"
                              >
                                <Pause size={13} />
                                <span>Pause</span>
                              </button>
                              <span className="text-[#E2E2E2]">|</span>
                              <button
                                type="button"
                                onClick={stopAudio}
                                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#6B6B6B] hover:text-[#1A1A1A] cursor-pointer"
                              >
                                <Square size={12} />
                                <span>Stop</span>
                              </button>
                            </div>
                          ) : isCurrentSpeaking && voiceState === 'paused' ? (
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={resumeAudio}
                                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#1B2A4A] hover:text-[#3D5580] cursor-pointer"
                              >
                                <Play size={13} />
                                <span>Resume</span>
                              </button>
                              <span className="text-[#E2E2E2]">|</span>
                              <button
                                type="button"
                                onClick={stopAudio}
                                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#6B6B6B] hover:text-[#1A1A1A] cursor-pointer"
                              >
                                <Square size={12} />
                                <span>Stop</span>
                              </button>
                            </div>
                          ) : playedMessageIds.has(msg.id) ? (
                            <button
                              type="button"
                              onClick={() => {
                                setPlayedMessageIds((prev) => new Set(prev).add(msg.id));
                                replayAudio(msg.id, msg.text);
                              }}
                              className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#3D5580] hover:text-[#1B2A4A] cursor-pointer"
                            >
                              <RotateCcw size={12} />
                              <span>Replay</span>
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                setPlayedMessageIds((prev) => new Set(prev).add(msg.id));
                                playAudio(msg.id, msg.text);
                              }}
                              className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#3D5580] hover:text-[#1B2A4A] cursor-pointer"
                            >
                              <Play size={12} />
                              <span>Listen</span>
                            </button>
                          )}
                        </div>

                        {/* Contextual Action Pills */}
                        {msg.suggested_actions && msg.suggested_actions.length > 0 && (
                          <div className="pt-2 flex flex-wrap gap-2">
                            {msg.suggested_actions.map((act, i) => (
                              <button
                                key={i}
                                type="button"
                                onClick={() => handleActionClick(act.route)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white hover:bg-[#F9FAFB] text-[12px] font-medium text-[#1A1A1A] hover:border-[#CBD5E1] transition-colors cursor-pointer group"
                              >
                                <span>{act.label}</span>
                                <span className="text-[#6B6B6B] group-hover:translate-x-0.5 transition-transform">
                                  →
                                </span>
                              </button>
                            ))}
                          </div>
                        )}

                        <div className="h-2" />
                      </div>
                    );
                  })}

                  {/* Thinking status */}
                  {isLoading && (
                    <div className="space-y-1 pt-1 text-[13px] text-[#6B6B6B] flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#1B2A4A] animate-ping" />
                      <span>{loadingStage}</span>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </>
          )}

          {/* TAB 2: Daily Briefing View */}
          {activeTab === 'briefing' && (
            <div className="space-y-5 animate-fade-in">
              <button
                type="button"
                onClick={() => setActiveTab('chat')}
                className="text-[12px] font-medium text-[#6B6B6B] hover:text-[#1A1A1A] flex items-center gap-1 cursor-pointer"
              >
                ← Back to conversation
              </button>

              {/* Date Header */}
              <div>
                <span className="font-mono text-[11px] font-bold uppercase tracking-widest text-[#6B6B6B]">
                  TODAY
                </span>
                <h3 className="font-serif text-[22px] font-bold text-[#1A1A1A] leading-tight mt-0.5">
                  {formattedToday}
                </h3>
              </div>

              {briefingLoading ? (
                <div className="py-8 space-y-3">
                  <div className="flex items-center gap-2 text-[13px] text-[#6B6B6B]">
                    <span className="w-2 h-2 rounded-full bg-[#1B2A4A] animate-ping" />
                    <span>{loadingStage}</span>
                  </div>
                </div>
              ) : briefingData ? (
                <div className="space-y-5">
                  {/* Factual Metrics Rows */}
                  <div className="grid grid-cols-3 gap-2.5">
                    {briefingData.summary.active_matches_count !== undefined && (
                      <div className="p-3 border border-[#E2E2E2] rounded-lg bg-white">
                        <div className="font-serif text-xl font-bold text-[#1A1A1A]">
                          {briefingData.summary.active_matches_count}
                        </div>
                        <div className="text-[11px] text-[#6B6B6B] mt-0.5 font-medium">New Matches</div>
                      </div>
                    )}

                    {briefingData.summary.upcoming_oa_count !== undefined && (
                      <div className="p-3 border border-[#E2E2E2] rounded-lg bg-white">
                        <div className="font-serif text-xl font-bold text-[#1A1A1A]">
                          {briefingData.summary.upcoming_oa_count +
                            (briefingData.summary.upcoming_interviews_count || 0)}
                        </div>
                        <div className="text-[11px] text-[#6B6B6B] mt-0.5 font-medium">Upcoming</div>
                      </div>
                    )}

                    {briefingData.summary.pending_confirmations_count !== undefined && (
                      <div className="p-3 border border-[#E2E2E2] rounded-lg bg-white">
                        <div className="font-serif text-xl font-bold text-[#1A1A1A]">
                          {briefingData.summary.pending_confirmations_count}
                        </div>
                        <div className="text-[11px] text-[#6B6B6B] mt-0.5 font-medium">Awaiting Conf.</div>
                      </div>
                    )}
                  </div>

                  {/* Grounded Summary */}
                  <div className="space-y-2">
                    <span className="font-mono text-[11px] font-bold uppercase tracking-widest text-[#6B6B6B]">
                      TODAY&apos;S BRIEFING
                    </span>
                    <p className="text-[13.5px] text-[#1A1A1A] leading-relaxed whitespace-pre-line">
                      {briefingData.answer}
                    </p>
                  </div>

                  {/* Mutually Exclusive Audio Player Bar */}
                  <div className="pt-1">
                    {currentSpeakingId === 'briefing' && voiceState === 'generating' ? (
                      <span className="text-[12.5px] text-[#6B6B6B] italic">Generating voice...</span>
                    ) : currentSpeakingId === 'briefing' && voiceState === 'playing' ? (
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={pauseAudio}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white text-[12.5px] font-medium text-[#1A1A1A] hover:bg-[#F9FAFB] cursor-pointer"
                        >
                          <Pause size={13} />
                          <span>Pause</span>
                        </button>
                        <button
                          type="button"
                          onClick={stopAudio}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white text-[12.5px] font-medium text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F9FAFB] cursor-pointer"
                        >
                          <Square size={12} />
                          <span>Stop</span>
                        </button>
                      </div>
                    ) : currentSpeakingId === 'briefing' && voiceState === 'paused' ? (
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={resumeAudio}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white text-[12.5px] font-medium text-[#1B2A4A] hover:bg-[#F9FAFB] cursor-pointer"
                        >
                          <Play size={13} />
                          <span>Resume</span>
                        </button>
                        <button
                          type="button"
                          onClick={stopAudio}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white text-[12.5px] font-medium text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F9FAFB] cursor-pointer"
                        >
                          <Square size={12} />
                          <span>Stop</span>
                        </button>
                      </div>
                    ) : hasPlayedBriefing ? (
                      <button
                        type="button"
                        onClick={() => {
                          setHasPlayedBriefing(true);
                          replayAudio('briefing', briefingData.answer);
                        }}
                        className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-[#E2E2E2] bg-white hover:bg-[#F9FAFB] text-[13px] font-medium text-[#1A1A1A] transition-colors cursor-pointer"
                      >
                        <RotateCcw size={14} className="text-[#1B2A4A]" />
                        <span>Replay</span>
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setHasPlayedBriefing(true);
                          playAudio('briefing', briefingData.answer);
                        }}
                        className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-[#E2E2E2] bg-white hover:bg-[#F9FAFB] text-[13px] font-medium text-[#1A1A1A] transition-colors cursor-pointer"
                      >
                        <Play size={14} className="text-[#1B2A4A]" />
                        <span>Listen to briefing</span>
                      </button>
                    )}
                  </div>

                  {/* Top Matches preview if available */}
                  {briefingData.summary.top_matches && briefingData.summary.top_matches.length > 0 && (
                    <div className="pt-2 space-y-2">
                      <span className="font-mono text-[11px] font-bold uppercase tracking-widest text-[#6B6B6B]">
                        TOP MATCHES
                      </span>
                      <div className="space-y-1.5">
                        {briefingData.summary.top_matches.map((m, i) => (
                          <div
                            key={i}
                            className="p-2.5 rounded-lg border border-[#E2E2E2] bg-white flex items-center justify-between text-xs"
                          >
                            <div>
                              <div className="font-medium text-[#1A1A1A]">{m.role}</div>
                              <div className="text-[#6B6B6B] text-[11px]">{m.company}</div>
                            </div>
                            {m.score_pct !== undefined && (
                              <span className="font-mono text-[11px] font-semibold text-[#1B2A4A]">
                                {m.score_pct}%
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suggested Actions */}
                  {briefingData.suggested_actions && briefingData.suggested_actions.length > 0 && (
                    <div className="pt-2 flex flex-wrap gap-2">
                      {briefingData.suggested_actions.map((act, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => handleActionClick(act.route)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white hover:bg-[#F9FAFB] text-[12px] font-medium text-[#1A1A1A] hover:border-[#CBD5E1] transition-colors cursor-pointer group"
                        >
                          <span>{act.label}</span>
                          <span className="text-[#6B6B6B] group-hover:translate-x-0.5 transition-transform">
                            →
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Input Composer (Anchored at Bottom) */}
        {activeTab === 'chat' && (
          <div className="p-3.5 border-t border-[#E2E2E2] bg-[#FFFFFF] shrink-0">
            {voiceState === 'listening' && (
              <div className="mb-2 px-3 py-1.5 rounded-md bg-[#F3F4F6] text-[#1B2A4A] text-xs font-medium flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#1B2A4A] animate-ping" />
                  Listening...
                </span>
                <button
                  type="button"
                  onClick={stopListening}
                  className="text-[11px] text-[#6B6B6B] hover:text-[#1A1A1A] underline cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            )}

            <div className="flex items-end gap-2 border border-[#E2E2E2] focus-within:border-[#1B2A4A] rounded-xl p-2 bg-[#FAFAFA] focus-within:bg-white transition-colors">
              <textarea
                ref={textareaRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your career workspace..."
                rows={1}
                disabled={isLoading}
                className="flex-1 bg-transparent text-[13px] text-[#1A1A1A] placeholder-[#9CA3AF] resize-none outline-hidden min-h-[36px] max-h-[120px] py-1 px-1.5"
              />

              <div className="flex items-center gap-1 shrink-0 pb-0.5">
                {/* Microphone control */}
                {isSpeechRecognitionSupported && (
                  <button
                    type="button"
                    onClick={toggleListening}
                    disabled={isLoading}
                    className={`p-2 rounded-lg transition-colors cursor-pointer ${
                      voiceState === 'listening'
                        ? 'bg-[#1B2A4A] text-white'
                        : 'text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F3F4F6]'
                    }`}
                    title={voiceState === 'listening' ? 'Stop listening' : 'Speak your question'}
                  >
                    <Mic size={16} />
                  </button>
                )}

                {/* Send button */}
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!inputText.trim() || isLoading}
                  className="p-2 rounded-lg bg-[#1B2A4A] text-white hover:bg-[#3D5580] disabled:opacity-30 disabled:hover:bg-[#1B2A4A] transition-colors cursor-pointer"
                  title="Send (Enter)"
                >
                  <Send size={15} />
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-[10.5px] text-[#9CA3AF] mt-2 px-1">
              <span>Enter to send · Shift+Enter for newline</span>
              <span>Grounded in your workspace</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
