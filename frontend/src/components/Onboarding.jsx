import React, { useState } from 'react';
import { t } from '../i18n/translations';

export default function Onboarding({ initialState, onComplete }) {
  const [lang, setLang] = useState(initialState.lang || 'en');
  const [name, setName] = useState(initialState.name || '');
  const [experienced, setExperienced] = useState(initialState.experienced);
  const [statedCrashReaction, setStatedCrashReaction] = useState(initialState.statedCrashReaction);
  const [startingCash, setStartingCash] = useState(initialState.startingCash);
  const [mode, setMode] = useState(initialState.mode);

  const handleSubmit = (e) => {
    e.preventDefault();
    const seed = mode === 'practice' ? Math.floor(100 + Math.random() * 9000) : 42;
    onComplete({
      onboarded: true,
      lang,
      name: name.trim(),
      experienced,
      statedCrashReaction,
      startingCash,
      mode,
      seed,
      day: 1,
      orders: [],
      watchlist: {},
      alerts: [],
      research: {},
    });
  };

  return (
    <div className="app-shell">
      <form className="page" onSubmit={handleSubmit} style={{ paddingTop: 26 }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <img src="/icons/icon-192.png" alt="NiveshSetu" style={{ width: 60, height: 60, borderRadius: 14, marginBottom: 8 }} />
          <h1 style={{ margin: '0 0 4px', fontSize: '1.45rem' }}>
            {t(lang, 'brand')} · {lang === 'hi' ? 'NiveshSetu' : 'निवेश सेतु'}
          </h1>
          <p className="muted" style={{ margin: '0 0 8px' }}>{t(lang, 'onboardingTitle')}</p>
          <span className="pill pill-brand">{t(lang, 'fictionalNotice')}</span>
        </div>

        {/* Step 1: Language */}
        <div className="card">
          <strong>1. {lang === 'hi' ? 'भाषा चुनें' : 'Choose Language'}</strong>
          <div className="chip-row" style={{ marginTop: 10 }}>
            <button type="button" className={`chip ${lang === 'en' ? 'selected' : ''}`} onClick={() => setLang('en')}>
              English
            </button>
            <button type="button" className={`chip ${lang === 'hi' ? 'selected' : ''}`} onClick={() => setLang('hi')}>
              हिंदी (Hindi)
            </button>
          </div>
        </div>

        {/* Step 2: Name (local only) */}
        <div className="card">
          <strong>2. {lang === 'hi' ? 'आपका नाम (केवल आपके फ़ोन पर रहेगा)' : 'Your Name (stays on your device only)'}</strong>
          <input
            className="input"
            style={{ marginTop: 10 }}
            placeholder={lang === 'hi' ? 'जैसे: उत्कर्ष' : 'e.g. Utkarsh'}
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={32}
          />
        </div>

        {/* Step 3: Experience (controls default MTF toggle) */}
        <div className="card">
          <strong>3. {lang === 'hi' ? 'क्या आपने पहले शेयर बाज़ार में निवेश किया है?' : 'Have you invested in stocks before?'}</strong>
          <div className="chip-row" style={{ marginTop: 10 }}>
            <button type="button" className={`chip ${!experienced ? 'selected' : ''}`} onClick={() => setExperienced(false)}>
              {lang === 'hi' ? 'पहली बार (नया निवेशक)' : 'First-time investor'}
            </button>
            <button type="button" className={`chip ${experienced ? 'selected' : ''}`} onClick={() => setExperienced(true)}>
              {lang === 'hi' ? 'हाँ, थोड़ा अनुभव है (MTF अनलॉक)' : 'Yes, some experience (unlocks MTF)'}
            </button>
          </div>
        </div>

        {/* Step 4: Stated crash reaction */}
        <div className="card">
          <strong>
            4. {lang === 'hi' ? 'अगर आपका पोर्टफ़ोलियो 10% गिर जाए, तो आप क्या करेंगे?' : 'If your portfolio drops 10% suddenly, what would you do?'}
          </strong>
          <p className="muted" style={{ margin: '4px 0 10px' }}>
            {lang === 'hi' ? 'दिन 21 पर हम इसकी तुलना आपके असली व्यवहार से करेंगे।' : 'On Day 21, we compare this with what you actually did.'}
          </p>
          <div className="chip-row">
            {[
              { id: 'hold', en: 'Stay calm & hold', hi: 'शांत रहकर रुकूँगा' },
              { id: 'buy_more', en: 'Review & buy carefully', hi: 'जाँचकर थोड़ा और ख़रीदूँगा' },
              { id: 'sell', en: 'Sell quickly to stop loss', hi: 'डरकर तुरंत बेच दूँगा' },
            ].map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={`chip ${statedCrashReaction === opt.id ? 'selected' : ''}`}
                onClick={() => setStatedCrashReaction(opt.id)}
              >
                {opt[lang]}
              </button>
            ))}
          </div>
        </div>

        {/* Step 5: Virtual Cash & Mode */}
        <div className="card">
          <strong>5. {lang === 'hi' ? 'नकली पैसे और सीज़न मोड' : 'Pretend Capital & Season Mode'}</strong>
          <div className="chip-row" style={{ marginTop: 10 }}>
            {[25000, 50000, 100000].map((amt) => (
              <button
                key={amt}
                type="button"
                className={`chip ${startingCash === amt ? 'selected' : ''}`}
                onClick={() => setStartingCash(amt)}
              >
                ₹{amt.toLocaleString('en-IN')}
              </button>
            ))}
          </div>
          <div className="chip-row" style={{ marginTop: 10 }}>
            <button type="button" className={`chip ${mode === 'guided' ? 'selected' : ''}`} onClick={() => setMode('guided')}>
              {lang === 'hi' ? 'गाइडेड 21-दिन कहानी (अनुशंसित)' : 'Guided 21-Day Story (Recommended)'}
            </button>
            <button type="button" className={`chip ${mode === 'practice' ? 'selected' : ''}`} onClick={() => setMode('practice')}>
              {lang === 'hi' ? 'प्रैक्टिस सीज़न (रैंडम सीड)' : 'Practice Season (Random Seed)'}
            </button>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" style={{ padding: 13, fontSize: '1rem' }}>
          {t(lang, 'startSim')}
        </button>
      </form>
    </div>
  );
}
