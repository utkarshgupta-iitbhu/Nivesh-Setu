import React from 'react';
import { getDayFocus, t } from '../i18n/translations';
import { useVoice } from '../api/voice';

export default function ExploreTab({
  lang,
  name,
  market,
  coachNote,
  onDismissCoach,
  watchlist,
  onlyWatchlist,
  triggeredAlerts,
  showTip,
  onDismissTip,
  onSelectStock,
  onToggleWatch,
}) {
  const { speakingId, toggleSpeak } = useVoice();

  if (!market) return <div className="page"><div className="card">{t(lang, 'loadingMarket')}</div></div>;

  const stocks = onlyWatchlist
    ? market.stocks.filter((s) => Boolean(watchlist[s.code]))
    : market.stocks;

  const latestNews = [...(market.news || [])].reverse().slice(0, 3);

  return (
    <div className="page">
      {!onlyWatchlist && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ margin: 0, fontSize: '1.15rem' }}>
              {t(lang, 'welcome')}{name ? `, ${name}` : ''} 👋
            </h2>
            <span className="muted" style={{ fontSize: '0.78rem' }}>{t(lang, 'fictionalNotice')}</span>
          </div>

          {/* Daily Learning Objective */}
          <div className="card" style={{ padding: '10px 12px', background: 'var(--brand-soft)', borderColor: 'transparent' }}>
            <strong style={{ fontSize: '0.82rem', color: 'var(--brand)' }}>
              🎯 {t(lang, 'todayFocus')} ({t(lang, 'dayLabel')} {market.day}/21):
            </strong>
            <div style={{ fontSize: '0.86rem', marginTop: 3 }}>{getDayFocus(market.day, lang, market.regime)}</div>
          </div>

          {showTip && (
            <div className="banner-ok" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <span>💡 {t(lang, 'tipExplore')}</span>
              <button className="btn btn-sm" onClick={onDismissTip}>{t(lang, 'gotIt')}</button>
            </div>
          )}

          {/* Market Indices */}
          <div className="grid-2">
            {market.indices.map((ix) => (
              <div key={ix.id} className="card" style={{ padding: 11 }}>
                <div className="muted" style={{ fontSize: '0.78rem' }}>{ix.name}</div>
                <div style={{ fontWeight: 700, fontSize: '1.05rem', marginTop: 2 }}>
                  {ix.value.toLocaleString('en-IN')}
                </div>
                <div className={ix.change_pct >= 0 ? 'up' : 'down'} style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                  {ix.change_pct >= 0 ? '+' : ''}{ix.change_pct}%
                </div>
              </div>
            ))}
          </div>

          {/* Triggered Notification Alerts */}
          {triggeredAlerts.length > 0 && (
            <div className="banner-warn">
              <strong>🔔 {lang === 'hi' ? 'आज के सूचना अलर्ट' : 'Notification Alerts Today'}</strong>
              {triggeredAlerts.map((a) => (
                <div key={a.id} style={{ marginTop: 4 }}>{a.summary[lang]}</div>
              ))}
            </div>
          )}

          {/* Contextual Coach Card */}
          {coachNote && (
            <div className="card" style={{ borderColor: 'var(--brand)' }}>
              <div className="card-header">
                <strong>🧭 {coachNote.title}</strong>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    className="btn btn-sm"
                    onClick={() =>
                      toggleSpeak('coach_note', `${coachNote.title}. ${coachNote.note} ${coachNote.question}`, lang)
                    }
                  >
                    {speakingId === 'coach_note' ? t(lang, 'stop') : t(lang, 'listen')}
                  </button>
                  <button className="btn btn-sm" onClick={onDismissCoach} aria-label="Dismiss coach note">✕</button>
                </div>
              </div>
              <p style={{ margin: '0 0 6px', fontSize: '0.9rem' }}>{coachNote.note}</p>
              <p className="muted" style={{ margin: 0, fontStyle: 'italic' }}>{coachNote.question}</p>
            </div>
          )}

          {/* Latest Market News */}
          <div className="card">
            <div className="card-header">
              <strong>📰 {t(lang, 'newsFeed')}</strong>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {latestNews.map((item, idx) => (
                <div
                  key={`${item.day}-${idx}`}
                  className={
                    item.severity === 'crash'
                      ? 'banner-danger'
                      : item.severity === 'rumour' || item.severity === 'warning'
                      ? 'banner-warn'
                      : 'muted'
                  }
                  style={{ fontSize: '0.84rem' }}
                >
                  <strong>{t(lang, 'dayLabel')} {item.day}:</strong> {item.text[lang]}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Stock List */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>{onlyWatchlist ? t(lang, 'watchlist') : t(lang, 'stocksTitle')}</strong>
        <span className="muted">{stocks.length}</span>
      </div>

      {stocks.length === 0 ? (
        <div className="card muted">{t(lang, 'noWatchlist')}</div>
      ) : (
        stocks.map((st) => {
          const q = st.quote;
          const watched = Boolean(watchlist[st.code]);
          return (
            <div key={st.code} className="stock-row" onClick={() => onSelectStock(st.code)}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className="stock-dot" style={{ background: st.color }} />
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{st.name}</div>
                  <div className="muted" style={{ fontSize: '0.78rem' }}>
                    {st.sector[lang]}
                    {q.circuit === 'LC' && <span className="pill pill-down" style={{ marginLeft: 6 }}>LC</span>}
                    {q.circuit === 'UC' && <span className="pill pill-up" style={{ marginLeft: 6 }}>UC</span>}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700 }}>₹{q.price.toFixed(2)}</div>
                  <div className={q.change_pct >= 0 ? 'up' : 'down'} style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                    {q.change_pct >= 0 ? '+' : ''}{q.change_pct}%
                  </div>
                </div>
                <button
                  className="btn btn-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleWatch(st.code);
                  }}
                  aria-label="Toggle watchlist"
                >
                  {watched ? '★' : '☆'}
                </button>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
