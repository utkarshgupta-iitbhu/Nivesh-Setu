import React, { useRef } from 'react';
import { TRANSLATIONS, t } from '../i18n/translations';

export default function PortfolioTab({
  lang,
  mode,
  state,
  portfolio,
  orders,
  alerts,
  market,
  showTip,
  onDismissTip,
  onSelectStock,
  onDeleteAlert,
  onImportState,
  onReset,
}) {
  const fileInputRef = useRef(null);
  const holdingsEntries = Object.entries(portfolio?.holdings || {});
  const priceMap = Object.fromEntries((market?.stocks || []).map((s) => [s.code, s.quote.price]));
  const alertLabels = TRANSLATIONS[lang]?.alertRules || TRANSLATIONS.en.alertRules;
  const reasonLabels = TRANSLATIONS[lang]?.reasonLabels || TRANSLATIONS.en.reasonLabels;

  const startingCash = portfolio?.starting_cash ?? state.startingCash;
  const equity = portfolio?.equity ?? startingCash;
  const netPnl = equity - startingCash;
  const netPnlPct = startingCash > 0 ? (netPnl / startingCash) * 100 : 0;
  const interestPaid = portfolio?.total_interest_paid ?? 0;

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `niveshsetu-day${state.day}-backup.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || '{}'));
        if (typeof parsed.day === 'number' && Array.isArray(parsed.orders)) {
          onImportState(parsed);
        }
      } catch {
        // ignore malformed file
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleResetClick = () => {
    if (window.confirm(t(lang, 'confirmReset'))) {
      onReset();
    }
  };

  return (
    <div className="page">
      {mode === 'portfolio' ? (
        <>
          {showTip && (
            <div className="banner-ok" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <span>💡 {t(lang, 'tipPortfolio')}</span>
              <button className="btn btn-sm" onClick={onDismissTip}>{t(lang, 'gotIt')}</button>
            </div>
          )}

          {/* Full Transparent P&L Summary Card */}
          <div className="card">
            <div className="muted">{t(lang, 'netWorth')}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, margin: '4px 0 12px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '1.6rem', fontWeight: 800 }}>
                ₹{equity.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </span>
              <span className={netPnl >= 0 ? 'up' : 'down'} style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                {netPnl >= 0 ? '+' : ''}₹{netPnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })} ({netPnlPct >= 0 ? '+' : ''}{netPnlPct.toFixed(1)}%)
              </span>
            </div>

            <div className="grid-2" style={{ fontSize: '0.86rem' }}>
              <div>
                <div className="muted">{t(lang, 'startingCapital')}</div>
                <strong>₹{startingCash.toLocaleString('en-IN')}</strong>
              </div>
              <div>
                <div className="muted">{t(lang, 'freeCash')}</div>
                <strong>₹{(portfolio?.cash ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</strong>
              </div>
              <div>
                <div className="muted">{t(lang, 'borrowedMtf')}</div>
                <strong className={portfolio?.total_borrowed > 0 ? 'down' : ''}>
                  ₹{(portfolio?.total_borrowed ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </strong>
              </div>
              <div>
                <div className="muted">{t(lang, 'interestPaid')}</div>
                <strong className={interestPaid > 0 ? 'down' : ''}>
                  ₹{interestPaid.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </strong>
              </div>
            </div>
          </div>

          <strong>{t(lang, 'holdings')} ({holdingsEntries.length})</strong>
          {holdingsEntries.length === 0 ? (
            <div className="card muted">{t(lang, 'noHoldings')}</div>
          ) : (
            holdingsEntries.map(([code, h]) => {
              const curPrice = priceMap[code] || h.avg_cost;
              const mktVal = curPrice * h.qty;
              const unrealizedPnl = (curPrice - h.avg_cost) * h.qty;
              return (
                <div key={code} className="stock-row" onClick={() => onSelectStock(code)}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{code}</div>
                    <div className="muted" style={{ fontSize: '0.8rem' }}>
                      {h.qty} {lang === 'hi' ? 'शेयर' : 'sh'} · Avg ₹{h.avg_cost.toFixed(2)}
                      {h.borrowed > 0 && ` · MTF Loan ₹${h.borrowed.toFixed(0)}`}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700 }}>₹{mktVal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                    <div className={unrealizedPnl >= 0 ? 'up' : 'down'} style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                      {unrealizedPnl >= 0 ? '+' : ''}₹{unrealizedPnl.toFixed(0)}
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {alerts.length > 0 && (
            <div className="card">
              <strong>🔔 {t(lang, 'activeAlerts')} ({alerts.length})</strong>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                {alerts.map((a) => (
                  <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                    <span>{a.code} — {alertLabels[a.rule] || a.rule} {a.threshold ? `(${a.threshold})` : ''}</span>
                    <button className="btn btn-sm" onClick={() => onDeleteAlert(a.id)}>✕</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Local Backup Export / Import */}
          <div className="card">
            <div className="muted" style={{ fontSize: '0.8rem', marginBottom: 8 }}>{t(lang, 'backupNote')}</div>
            <div className="grid-2">
              <button className="btn btn-sm" onClick={handleExport}>⬇ {t(lang, 'exportBackup')}</button>
              <button className="btn btn-sm" onClick={() => fileInputRef.current?.click()}>⬆ {t(lang, 'importBackup')}</button>
              <input ref={fileInputRef} type="file" accept="application/json" style={{ display: 'none' }} onChange={handleImportFile} />
            </div>
          </div>

          <button className="btn" onClick={handleResetClick}>{t(lang, 'resetSeason')}</button>
        </>
      ) : (
        <>
          <strong>{t(lang, 'orders')} ({orders.length})</strong>
          {orders.length === 0 ? (
            <div className="card muted">{t(lang, 'noOrders')}</div>
          ) : (
            [...orders].reverse().map((o, idx) => (
              <div key={idx} className="card" style={{ padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>
                    <span className={o.side === 'buy' ? 'up' : 'down'}>
                      {o.side === 'buy' ? t(lang, 'buy') : t(lang, 'sell')}
                    </span>{' '}
                    {o.code}
                  </strong>
                  <span className="muted">{t(lang, 'dayLabel')} {o.day}</span>
                </div>
                <div className="muted" style={{ fontSize: '0.83rem', marginTop: 4 }}>
                  {t(lang, 'qty')}: {o.qty} {o.mtf ? '· 2× MTF' : ''} · {t(lang, 'reason')}: {reasonLabels[o.reason_tag] || o.reason_tag}
                </div>
              </div>
            ))
          )}
        </>
      )}
    </div>
  );
}
