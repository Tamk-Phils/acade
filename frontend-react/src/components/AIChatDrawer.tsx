import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, DocumentMetadata } from '../types';
import { sendChatMessage } from '../services/api';

interface AIChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  institution: 'uba' | 'catuc';
  docType: string;
  schoolType: string;
  metadata?: DocumentMetadata;
  onApplyChanges?: (changes: Record<string, any>) => void;
  prefilledPrompt?: string;
  onClearPrefilledPrompt?: () => void;
}

export const AIChatDrawer: React.FC<AIChatDrawerProps> = ({
  isOpen,
  onClose,
  institution,
  docType,
  schoolType,
  metadata,
  onApplyChanges,
  prefilledPrompt,
  onClearPrefilledPrompt
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      sender: 'assistant',
      text: `Hello! I am the **AcadFormat AI Academic Director** for **${
        institution === 'catuc' ? 'Catholic University of Cameroon (CATUC)' : 'The University of Bamenda (UBa)'
      }**.\n\nYou can **type or speak** using the 🎙️ microphone to give formatting instructions. Ask me to change your title, update supervisors, configure group assignment rosters, or explain binding rules.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      suggestions: [
        'Set supervisor to Prof. Mathias Onabid',
        'Make this a group assignment with 5 members',
        'Why is 4cm inside margin mandatory?',
        'Switch to CATUC FBMS'
      ]
    }
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [latency, setLatency] = useState<number | null>(12);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);

  // Sync prefilled prompt when supplied from LivePreview or selection
  useEffect(() => {
    if (prefilledPrompt) {
      setInput(prefilledPrompt);
      onClearPrefilledPrompt?.();
    }
  }, [prefilledPrompt]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize Speech Recognition
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
          setIsListening(true);
        };

        recognition.onresult = (event: any) => {
          let fullTranscript = '';
          for (let i = 0; i < event.results.length; ++i) {
            fullTranscript += event.results[i][0].transcript;
          }
          if (fullTranscript.trim()) {
            setInput(fullTranscript);
          }
        };

        recognition.onerror = (event: any) => {
          console.warn('Speech recognition error:', event.error);
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognition;
      } catch (err) {
        console.warn('Speech recognition initialization failed:', err);
        setSpeechSupported(false);
      }
    } else {
      setSpeechSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
    };
  }, []);

  const toggleListening = () => {
    if (!speechSupported) {
      alert(
        'Live speech transcription uses the Web Speech API supported in Google Chrome, Microsoft Edge, and Safari. Please type your prompt directly or enable microphone permissions.'
      );
      return;
    }

    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch (_) {}
      setIsListening(false);
    } else {
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch (err) {
        console.error('Failed to start speech recognition:', err);
        setIsListening(false);
      }
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  if (!isOpen) return null;

  const handleSendMessage = async (textToSend: string) => {
    const text = textToSend.trim();
    if (!text || loading) return;

    // If currently recording voice, stop
    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch (_) {}
      setIsListening(false);
    }

    const userMsg: ChatMessage = {
      id: 'usr_' + Date.now(),
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    const startTime = performance.now();
    try {
      const resp = await sendChatMessage(text, institution, docType, schoolType, metadata);
      const elapsed = Math.round(performance.now() - startTime);
      setLatency(elapsed);

      // If AI produced applied changes, invoke parent callback
      if (resp.applied_changes && onApplyChanges) {
        onApplyChanges(resp.applied_changes);
      }

      const aiMsg: ChatMessage = {
        id: 'ai_' + Date.now(),
        sender: 'assistant',
        text: resp.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestions: resp.suggestions,
        engine: resp.engine,
        applied_changes: resp.applied_changes,
        action_summary: resp.action_summary
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      const errMsg: ChatMessage = {
        id: 'err_' + Date.now(),
        sender: 'assistant',
        text: 'The assistant could not be reached. Local formatting fallback is active.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'init_reset',
        sender: 'assistant',
        text: `Conversation cleared. Ready for your voice dictations or text prompts.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestions: [
          'Set supervisor to Prof. Mathias Onabid',
          'What is the inside binding margin?',
          'COLTECH cover page layout'
        ]
      }
    ]);
  };

  return (
    <div className="ai-drawer-overlay" onClick={onClose}>
      <div className="ai-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="ai-drawer-header">
          <div className="ai-drawer-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            Academic Formatting AI
            {latency !== null && (
              <span className="speed-tag" title="Sub-15ms local engine latency">
                ⚡ {latency}ms
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <button
              type="button"
              onClick={clearChat}
              style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', fontSize: '0.75rem' }}
              title="Clear conversation"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: '#FFFFFF', cursor: 'pointer', fontSize: '1.1rem', marginLeft: '0.5rem' }}
              title="Close drawer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Live Voice Recording Status Banner */}
        {isListening && (
          <div
            style={{
              padding: '0.4rem 0.8rem',
              background: '#991B1B',
              color: '#FEE2E2',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.75rem',
              borderBottom: '1px solid #DC2626'
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ animation: 'pulse 1s infinite', fontSize: '0.9rem' }}>🔴</span>
              Listening... Speak your ideas or formatting instructions
            </span>
            <button
              type="button"
              onClick={toggleListening}
              style={{
                background: '#FFFFFF',
                color: '#991B1B',
                border: 'none',
                padding: '0.15rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.7rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Stop & Keep
            </button>
          </div>
        )}

        {/* Messages Body */}
        <div className="ai-drawer-messages">
          {messages.map((m) => (
            <div key={m.id} className={`chat-bubble ${m.sender}`}>
              <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>

              {/* Visual Card when Changes were Executed on Manuscript */}
              {m.action_summary && (
                <div
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    color: '#34D399'
                  }}
                >
                  <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.2rem' }}>
                    <span>⚡ Applied to Manuscript</span>
                  </div>
                  <div style={{ color: '#E2E8F0', fontSize: '0.75rem', lineHeight: 1.4 }}>
                    {m.action_summary}
                  </div>
                </div>
              )}

              {m.suggestions && m.suggestions.length > 0 && (
                <div className="suggestion-chips">
                  {m.suggestions.map((sug, sIdx) => (
                    <button
                      key={sIdx}
                      type="button"
                      className="suggestion-chip"
                      onClick={() => handleSendMessage(sug)}
                    >
                      {sug}
                    </button>
                  ))}
                </div>
              )}
              <div
                style={{
                  fontSize: '0.65rem',
                  opacity: 0.6,
                  textAlign: 'right',
                  marginTop: '0.35rem'
                }}
              >
                {m.timestamp}
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-bubble assistant" style={{ fontStyle: 'italic', opacity: 0.8 }}>
              Thinking and formatting your document...
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar with Speech Transcription Microphone */}
        <div className="ai-drawer-footer">
          <button
            type="button"
            className="btn-tool"
            onClick={toggleListening}
            title={isListening ? 'Stop voice recording' : 'Voice transcribe (Speech-to-Text)'}
            style={{
              background: isListening ? '#DC2626' : '#1E293B',
              color: isListening ? '#FFFFFF' : '#94A3B8',
              borderColor: isListening ? '#DC2626' : '#334155',
              padding: '0.45rem 0.65rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            {isListening ? '🛑' : '🎙️'}
          </button>

          <input
            type="text"
            className="form-control"
            placeholder={isListening ? 'Transcribing your voice in real time...' : 'Ask or prompt (e.g. "Change title to...")'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSendMessage(input);
            }}
          />

          <button
            type="button"
            className="btn-tool"
            disabled={!input.trim() || loading}
            onClick={() => handleSendMessage(input)}
            style={{
              background: 'var(--color-primary, #0284C7)',
              color: 'white',
              borderColor: 'transparent',
              padding: '0.45rem 0.9rem'
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};
