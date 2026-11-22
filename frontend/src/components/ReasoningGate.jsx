import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { recordAndTranscribe, stopSpeaking, useVoice } from '../api/voice';
import { t } from '../i18n/translations';

const TAGS = [
  { id: 'fundamentals', en: 'Checked fundamentals', hi: 'फ़ंडामेंटल्स देखे' },
  { id: 'tip', en: 'Friend / Telegram tip', hi: 'दोस्त / टेलीग्राम टिप' },
  { id: 'rising', en: 'Price is rising fast', hi: 'क़ीमत तेज़ी से बढ़ रही है' },
  { id: 'other', en: 'Long-term diversification', hi: 'लंबे समय का लक्ष्य' },
];

export default function ReasoningGate({
  lang,
  pendingBuy,
  stock,
  state,
  onCancel,
  onConfirmBuy,
}) {
  const [reasonTag, setReasonTag] = useState('fundamentals');
  const [reasonText, setReasonText] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const stopRecRef = useRef(null);
  const { speakingId, toggleSpeak } = useVoice();

  useEffect(() => () => {
    stopSpeaking();
    stopRecRef.current?.();
  }, []);

  const resMeta = state.research[stock.code] || {};

  const handleMic = () => {
    if (recording) {
      stopRecRef.current?.();
      setRecording(false);
      return;
    }
    setError('');
    stopRecRef.current = recordAndTranscribe(lang, {
      onStart: () => setRecording(true),
      onResult: (txt) => setReasonText((prev) => (prev ? `${prev} ${txt}` : txt)),
      onError: (msg) => setError(msg),
      onEnd: () => setRecording(false),
    });
  };

  const handleEvaluate = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.checkReason({
        mode: state.mode,
        seed: state.seed,
        day: state.day,
        lang,
        starting_cash: state.startingCash,
        orders: state.orders,
        code: pendingBuy.code,
        qty: pendingBuy.qty,
        mtf: pendingBuy.mtf,
        reason_tag: reasonTag,
        reason_text: reasonText,
        opened_fundamentals: Boolean(resMeta.info),
        read_news: Boolean(resMeta.news),
      });
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFinalConfirm = () => {
    stopSpeaking();
    onConfirmBuy({
      ...pendingBuy,
      reason_tag: reasonTag,
      reason_text: reasonText,
      gate_score: result?.score ?? 50,
      gate_verdict: result?.verdict ?? 'mixed',
      gate_flags: result?.flags ?? [],
    });
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-sheet">
        <div className="card-header" style={{ marginBottom: 0 }}>
          <strong>🧠 {lang === 'hi' ? 'ख़रीदने से पहले रुकें और सोचें' : 'Pause & Check Your Reasoning'}</strong>
          <button className="btn btn-sm" onClick={() => { stopSpeaking(); onCancel(); }}>✕</button>
        </div>

        <div className="muted">
          {stock.name} · {pendingBuy.qty} {lang === 'hi' ? 'शेयर' : 'shares'} {pendingBuy.mtf ? '· 2× MTF' : ''}
        </div>

        {!result ? (
          <>
            <div className="chip-row">
              {TAGS.map((tag) => (
                <button
                  key={tag.id}
                  type="button"
                  className={`chip ${reasonTag === tag.id ? 'selected' : ''}`}
                  onClick={() => setReasonTag(tag.id)}
                >
                  {tag[lang]}
                </button>
              ))}
            </div>

            <textarea
              className="textarea"
              placeholder={
                lang === 'hi'
                  ? 'अपने शब्दों में लिखें या 🎤 दबाकर बोलें — आप यह शेयर क्यों ख़रीद रहे हैं?'
                  : 'Type or tap 🎤 Speak — why are you buying this stock?'
              }
              value={reasonText}
              onChange={(e) => setReasonText(e.target.value)}
            />

            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className={`btn ${recording ? 'btn-danger' : ''}`} onClick={handleMic}>
                {recording ? t(lang, 'listening') : t(lang, 'speak')}
              </button>
              <button className="btn btn-primary" style={{ flex: 1 }} disabled={loading} onClick={handleEvaluate}>
                {loading
                  ? (lang === 'hi' ? 'जाँच हो रही है...' : 'Checking reasoning...')
                  : (lang === 'hi' ? 'मेरा कारण जाँचें' : 'Evaluate My Reasoning')}
              </button>
            </div>

            {error && <div className="banner-danger">{error}</div>}
          </>
        ) : result.blocked_as_advice ? (
          <>
            <div className="banner-warn">{result.text}</div>
            <button className="btn" onClick={() => setResult(null)}>
              {lang === 'hi' ? 'अपना कारण फिर से लिखें' : 'Rewrite My Reason'}
            </button>
          </>
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className={`pill ${result.verdict === 'sound' ? 'pill-up' : result.verdict === 'weak' ? 'pill-down' : 'pill-warn'}`}>
                {result.verdict.toUpperCase()} · {result.score}/100
              </span>
              <button
                className="btn btn-sm"
                onClick={() =>
                  toggleSpeak('gate_verdict', `${result.consequence_text} ${result.question || result.next_time_tip}`, lang)
                }
              >
                {speakingId === 'gate_verdict' ? t(lang, 'stop') : t(lang, 'listen')}
              </button>
            </div>

            {result.question && (
              <div className="banner-warn">
                <strong>{lang === 'hi' ? 'सोचने का सवाल:' : 'One question before you buy:'}</strong>
                <div>{result.question}</div>
              </div>
            )}

            <div className="banner-danger">
              <strong>{lang === 'hi' ? 'इस ऑर्डर का जोखिम:' : 'What this order means for you:'}</strong>
              <div>{result.consequence_text}</div>
            </div>

            <div style={{ fontSize: '0.86rem', display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div>✅ <strong>{lang === 'hi' ? 'अच्छी बात:' : 'What is right:'}</strong> {result.what_is_right}</div>
              <div>⚠️ <strong>{lang === 'hi' ? 'क्या छूट गया:' : 'What is missing:'}</strong> {result.what_is_missing}</div>
              <div>💡 <strong>{lang === 'hi' ? 'अगली बार:' : 'Next time:'}</strong> {result.next_time_tip}</div>
            </div>

            <div className="grid-2" style={{ marginTop: 4 }}>
              <button className="btn" onClick={() => { stopSpeaking(); onCancel(); }}>
                {lang === 'hi' ? 'रुकें (रद्द करें)' : 'Pause & Cancel'}
              </button>
              <button className="btn btn-primary" onClick={handleFinalConfirm}>
                {lang === 'hi' ? 'फिर भी ख़रीदें' : 'Confirm Buy'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
