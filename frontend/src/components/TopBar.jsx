import React from 'react';
import { t } from '../i18n/translations';

export default function TopBar({
  lang,
  theme,
  day,
  seasonDays,
  aiEnabled,
  onNextDay,
  onToggleLang,
  onToggleTheme,
  onOpenAsk,
}) {
  return (
    <header className="topbar">
      <div className="brand-row">
        <img src="/icons/icon-192.png" alt="NiveshSetu" style={{ borderRadius: 7 }} />
        <div>
          <div style={{ lineHeight: 1.1 }}>{t(lang, 'brand')}</div>
          <span className="pill pill-brand" style={{ fontSize: '0.68rem', padding: '1px 7px' }}>
            {t(lang, 'dayLabel')} {day}/{seasonDays}
          </span>
        </div>
      </div>

      <div className="topbar-controls">
        <span className={`pill ${aiEnabled ? 'pill-up' : 'pill-warn'}`}>
          {aiEnabled ? t(lang, 'aiOn') : t(lang, 'aiOff')}
        </span>
        <button className="btn btn-sm" onClick={onOpenAsk} title={t(lang, 'askGuide')}>
          💬 {t(lang, 'askBtn')}
        </button>
        <button className="btn btn-sm" onClick={onToggleLang}>
          {lang === 'en' ? 'हिंदी' : 'EN'}
        </button>
        <button className="btn btn-sm" onClick={onToggleTheme} aria-label="Toggle theme">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        {day < seasonDays && (
          <button className="btn btn-primary btn-sm" onClick={onNextDay}>
            {t(lang, 'nextDay')}
          </button>
        )}
      </div>
    </header>
  );
}
