import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '@/lib/api';
import { AssistantQueryResponse, AssistantBriefingResponse } from '@/types/assistant';

export type VoiceState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'generating'
  | 'playing'
  | 'paused'
  | 'error';

export interface AssistantMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  intent?: string;
  suggested_actions?: Array<{ label: string; route: string }>;
  timestamp: Date;
}

interface AssistantContextType {
  isOpen: boolean;
  activeTab: 'chat' | 'briefing';
  setActiveTab: (tab: 'chat' | 'briefing') => void;
  openAssistant: (initialQuery?: string, tab?: 'chat' | 'briefing', autoSpeak?: boolean) => void;
  closeAssistant: () => void;
  toggleAssistant: () => void;
  messages: AssistantMessage[];
  isLoading: boolean;
  loadingStage: string;
  voiceState: VoiceState;
  voiceErrorMessage: string | null;
  currentSpeakingId: string | null;
  isSpeechRecognitionSupported: boolean;
  sendMessage: (query: string) => Promise<void>;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
  playAudio: (id: string, text: string) => Promise<void>;
  pauseAudio: () => void;
  resumeAudio: () => void;
  stopAudio: () => void;
  replayAudio: (id: string, text: string) => Promise<void>;
  briefingData: AssistantBriefingResponse | null;
  briefingLoading: boolean;
  loadBriefing: () => Promise<void>;
  newConversation: () => void;
}

const AssistantContext = createContext<AssistantContextType | undefined>(undefined);

// Web Speech Recognition typing
interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      [subIndex: number]: {
        transcript: string;
      };
    };
  };
}

interface IWindowSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

interface WindowWithSpeech extends Window {
  SpeechRecognition?: { new (): IWindowSpeechRecognition };
  webkitSpeechRecognition?: { new (): IWindowSpeechRecognition };
}

export const AssistantProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();

  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'briefing'>('chat');
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('Aptly is checking your workspace...');
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [voiceErrorMessage, setVoiceErrorMessage] = useState<string | null>(null);
  const [currentSpeakingId, setCurrentSpeakingId] = useState<string | null>(null);
  const [briefingData, setBriefingData] = useState<AssistantBriefingResponse | null>(null);
  const [isSpeechRecognitionSupported, setIsSpeechRecognitionSupported] = useState(false);

  const recognitionRef = useRef<IWindowSpeechRecognition | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioBlobCacheRef = useRef<Map<string, string>>(new Map());

  // Initialize Speech Recognition detection
  useEffect(() => {
    const win = window as unknown as WindowWithSpeech;
    const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (SpeechRecognition) {
      setIsSpeechRecognitionSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        if (transcript.trim()) {
          setVoiceState('idle');
          sendMessage(transcript.trim());
        }
      };

      recognition.onerror = () => {
        setVoiceState('error');
        setTimeout(() => setVoiceState('idle'), 1500);
      };

      recognition.onend = () => {
        setVoiceState((prev) => (prev === 'listening' ? 'idle' : prev));
      };

      recognitionRef.current = recognition;
    } else {
      setIsSpeechRecognitionSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      stopAudio();
    };
  }, []);

  // Global Keyboard Shortcut: Cmd+K / Ctrl+K & Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCmdK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
      if (isCmdK) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
        return;
      }

      if (e.key === 'Escape' && isOpen) {
        closeAssistant();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const stopAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setVoiceState('idle');
    setCurrentSpeakingId(null);
  }, []);

  const pauseAudio = useCallback(() => {
    if (currentAudioRef.current && !currentAudioRef.current.paused) {
      currentAudioRef.current.pause();
      setVoiceState('paused');
    } else if (window.speechSynthesis && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      setVoiceState('paused');
    }
  }, []);

  const resumeAudio = useCallback(() => {
    if (currentAudioRef.current && currentAudioRef.current.paused) {
      currentAudioRef.current.play().then(() => {
        setVoiceState('playing');
      }).catch(() => {
        setVoiceState('idle');
      });
    } else if (window.speechSynthesis && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setVoiceState('playing');
    }
  }, []);

  const playAudio = useCallback(
    async (id: string, text: string) => {
      stopAudio();
      setVoiceErrorMessage(null);
      setCurrentSpeakingId(id);
      setVoiceState('generating');

      const cleanedText = text
        .replace(/[*_#`~]/g, '')
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
        .replace(/https?:\/\/\S+/g, '')
        .trim();

      if (!cleanedText) {
        setVoiceState('idle');
        setCurrentSpeakingId(null);
        return;
      }

      try {
        let audioUrl = audioBlobCacheRef.current.get(cleanedText);
        if (!audioUrl) {
          const audioBlob = await api.postBlob('/api/v1/assistant/speech', {
            text: cleanedText.slice(0, 1000),
          });
          audioUrl = URL.createObjectURL(audioBlob);
          audioBlobCacheRef.current.set(cleanedText, audioUrl);
        }

        const audio = new Audio(audioUrl);
        currentAudioRef.current = audio;

        audio.onended = () => {
          setVoiceState('idle');
          setCurrentSpeakingId(null);
          currentAudioRef.current = null;
        };

        audio.onerror = () => {
          setVoiceErrorMessage('Voice is unavailable right now.');
          setVoiceState('error');
          setTimeout(() => setVoiceState('idle'), 3000);
        };

        await audio.play();
        setVoiceState('playing');
      } catch (err: unknown) {
        const errorDetail = err instanceof Error ? err.message : '';
        if (errorDetail.includes('429')) {
          setVoiceErrorMessage('Voice limit reached. Please wait a moment.');
        } else {
          setVoiceErrorMessage('Voice is unavailable right now.');
        }
        setVoiceState('error');
        setTimeout(() => setVoiceState('idle'), 3000);
      }
    },
    [stopAudio]
  );

  const replayAudio = useCallback(
    async (id: string, text: string) => {
      await playAudio(id, text);
    },
    [playAudio]
  );

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    stopAudio();
    try {
      recognitionRef.current.start();
      setVoiceState('listening');
    } catch {
      setVoiceState('idle');
    }
  }, [stopAudio]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setVoiceState('idle');
  }, []);

  const toggleListening = useCallback(() => {
    if (voiceState === 'listening') {
      stopListening();
    } else {
      startListening();
    }
  }, [voiceState, startListening, stopListening]);

  // Context-aware page label helper
  const getPageContextLabel = useCallback(() => {
    const path = location.pathname;
    if (path.startsWith('/track-jobs')) return 'Track Jobs board';
    if (path.startsWith('/find-positions')) return 'Find Positions page';
    if (path.startsWith('/jd-analyzer')) return 'JD Analyzer page';
    if (path.startsWith('/dashboard')) return 'Dashboard';
    return undefined;
  }, [location.pathname]);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isLoading) return;

      const userMsg: AssistantMessage = {
        id: `user-${Date.now()}`,
        sender: 'user',
        text: query.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setVoiceState('thinking');
      setLoadingStage('Aptly is checking your workspace...');

      try {
        const pageContext = getPageContextLabel();
        const response = await api.post<AssistantQueryResponse>('/api/v1/assistant/query', {
          message: query.trim(),
          page_context: pageContext,
        });

        const assistantMsg: AssistantMessage = {
          id: `asst-${Date.now()}`,
          sender: 'assistant',
          text: response.answer,
          intent: response.intent,
          suggested_actions: response.suggested_actions,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
        setVoiceState('idle');
      } catch (err) {
        const errorMsg: AssistantMessage = {
          id: `err-${Date.now()}`,
          sender: 'assistant',
          text:
            err instanceof Error
              ? err.message
              : 'I encountered an issue retrieving your career insights. Please try again.',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
        setVoiceState('error');
        setTimeout(() => setVoiceState('idle'), 2000);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, getPageContextLabel]
  );

  const loadBriefing = useCallback(async () => {
    setBriefingLoading(true);
    setVoiceState('thinking');

    // Staged status updates
    setLoadingStage('Reviewing your matches...');
    const t1 = setTimeout(() => setLoadingStage('Checking your pipeline...'), 600);
    const t2 = setTimeout(() => setLoadingStage('Looking at upcoming deadlines...'), 1200);

    try {
      const data = await api.get<AssistantBriefingResponse>('/api/v1/assistant/briefing');
      setBriefingData(data);
      setActiveTab('briefing');
      setVoiceState('idle');
    } catch (err) {
      console.error('Failed to load briefing:', err);
      setVoiceState('error');
      setTimeout(() => setVoiceState('idle'), 2000);
    } finally {
      clearTimeout(t1);
      clearTimeout(t2);
      setBriefingLoading(false);
    }
  }, []);

  const openAssistant = useCallback(
    (initialQuery?: string, tab: 'chat' | 'briefing' = 'chat', _autoSpeak = false) => {
      setIsOpen(true);
      setActiveTab(tab);

      if (tab === 'briefing') {
        loadBriefing();
      } else if (initialQuery) {
        sendMessage(initialQuery);
      }
    },
    [loadBriefing, sendMessage]
  );

  const closeAssistant = useCallback(() => {
    setIsOpen(false);
    stopAudio();
    stopListening();
  }, [stopAudio, stopListening]);

  const toggleAssistant = useCallback(() => {
    if (isOpen) {
      closeAssistant();
    } else {
      openAssistant();
    }
  }, [isOpen, closeAssistant, openAssistant]);

  const newConversation = useCallback(() => {
    setMessages([]);
    setActiveTab('chat');
    stopAudio();
    stopListening();
  }, [stopAudio, stopListening]);

  return (
    <AssistantContext.Provider
      value={{
        isOpen,
        activeTab,
        setActiveTab,
        openAssistant,
        closeAssistant,
        toggleAssistant,
        messages,
        isLoading,
        loadingStage,
        voiceState,
        voiceErrorMessage,
        currentSpeakingId,
        isSpeechRecognitionSupported,
        sendMessage,
        startListening,
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
      }}
    >
      {children}
    </AssistantContext.Provider>
  );
};

export const useAssistant = () => {
  const context = useContext(AssistantContext);
  if (!context) {
    throw new Error('useAssistant must be used within an AssistantProvider');
  }
  return context;
};
