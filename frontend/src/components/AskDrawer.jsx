import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { recordAndTranscribe, stopSpeaking, useVoice } from '../api/voice';
import { t } from '../i18n/translations';

export default function AskDrawer({ lang, onClose }) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const stopRecRef = useRef(null);
  const { speakingId, toggleSpeak } = useVoice();

  useEffect(() => () => {
    stopSpeaking();
    stopRecRef.current?.();
  }, []);

  const handleMic = () => {
    if (recording) {
      stopRecRef.current?.();
      setRecording(false);
      return;
    }
    stopRecRef.current = recordAndTranscribe(lang, {
      onStart: () => setRecording(true),
      onResult: (txt) => setQuestion(txt),
      onEnd: () => setRecording(false),
    });
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    stopSpeaking();
    setLoading(true);
    try {
      const res = await api.askGuide({ lang, question });
      setAnswer(res);
    } catch (err) {
      setAnswer({ text: err.message, source: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-sheet">
        <div className="card-header" style={{ marginBottom: 0 }}>
          <strong>💬 {t(lang, 'askGuide')}</strong>
          <button className="btn btn-sm" onClick={() => { stopSpeaking(); onClose(); }}>✕</button>
        </div>
        <p className="muted" style={{ margin: 0 }}>
          {lang === 'hi'
            ? 'कोई भी निवेश शब्द या संदेह पूछें (जैसे "लोअर सर्किट क्या है?")। स्टॉक टिप पूछने पर हमारा गार्डरेल तुरंत रोक देगा।'
            : 'Ask any investing doubt or term (e.g. "What is a lower circuit?"). Stock tip requests are blocked by our guardrail.'}
        </p>

        <form onSubmit={handleAsk} style={{ display: 'flex', gap: 6 }}>
          <input
            className="input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={lang === 'hi' ? 'अपना सवाल लिखें या 🎤 बोलें...' : 'Type or tap 🎤 to ask...'}
          />
          <button type="button" className={`btn ${recording ? 'btn-danger' : ''}`} onClick={handleMic}>
            🎤
          </button>
          <button className="btn btn-primary" disabled={loading}>
            {loading ? '...' : t(lang, 'askBtn')}
          </button>
        </form>

        <div className="muted" style={{ fontSize: '0.76rem' }}>{t(lang, 'voicePrivacyNote')}</div>

        {answer && (
          <div className={answer.source === 'guardrail_refusal' ? 'banner-warn' : 'card'}>
            <p style={{ margin: '0 0 8px', fontSize: '0.9rem' }}>{answer.text}</p>
            <button
              className="btn btn-sm"
              onClick={() => toggleSpeak('ask_answer', answer.text, lang)}
            >
              {speakingId === 'ask_answer' ? t(lang, 'stop') : t(lang, 'listen')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
