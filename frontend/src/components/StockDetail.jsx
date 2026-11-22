import React, { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { TRANSLATIONS, t } from '../i18n/translations';

const SELL_REASONS = [
  { id: 'target', en: 'Booking profit / target met', hi: 'मुनाफ़ा / लक्ष्य पूरा' },
  { id: 'fear', en: 'Worried about price falling', hi: 'गिरावट का डर' },
  { id: 'other', en: 'Rebalancing / need cash', hi: 'पुनर्संतुलन / नक़द ज़रूरत' },
];

export default function StockDetail({
  lang,
  stock,
  day,
  holding,
  freeCash = 0,
  experienced,
  marketNews,
  onBack,
  onTrackResearch,
  onStartBuy,
  onDirectSell,
  onAddAlert,
}) {
  const [qty, setQty] = useState(0);
  const [side, setSide] = useState('buy');
  const [sellReason, setSellReason] = useState('target');
  const [mtf, setMtf] = useState(false);
  const [showFundamentals, setShowFundamentals] = useState(false);
  const [showAlertBox, setShowAlertBox] = useState(false);
  const [alertRule, setAlertRule] = useState('price_below');
  const [alertThreshold, setAlertThreshold] = useState(String(Math.round(stock.quote.price * 0.9)));
  const [openedAt] = useState(() => Date.now());

  const q = stock.quote;
  const stockNews = (marketNews || []).filter((n) => n.stock_code === stock.code).reverse();
  const alertLabels = TRANSLATIONS[lang]?.alertRules || TRANSLATIONS.en.alertRules;
  const flagLabels = TRANSLATIONS[lang]?.redFlagLabels || TRANSLATIONS.en.redFlagLabels;

  useEffect(() => {
    onTrackResearch(stock.code, 'chart');
    if (stockNews.length > 0) onTrackResearch(stock.code, 'news');
  }, [stock.code]);

  const handleToggleFundamentals = () => {
    setShowFundamentals((v) => !v);
    onTrackResearch(stock.code, 'info');
  };

  const handleSubmitOrder = () => {
    if (qty <= 0) return;
    const thinkMs = Date.now() - openedAt;
    if (side === 'buy') {
      onStartBuy({ code: stock.code, qty, mtf, thinkMs });
    } else {
      onDirectSell({ code: stock.code, qty, thinkMs, reason_tag: sellReason });
    }
  };

  const handleSaveAlert = () => {
    onAddAlert({
      id: `al_${Date.now()}`,
      code: stock.code,
      rule: alertRule,
      threshold: Number(alertThreshold) || 0,
    });
    setShowAlertBox(false);
  };

  const chartData = stock.history.map((pt) => ({
    label: pt.day <= 0 ? `D${pt.day}` : `${t(lang, 'dayLabel')} ${pt.day}`,
    price: pt.close,
  }));

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button className="btn btn-sm" onClick={onBack}>← {lang === 'hi' ? 'वापस' : 'Back'}</button>
        <button className="btn btn-sm" onClick={() => setShowAlertBox((v) => !v)}>{t(lang, 'setAlert')}</button>
      </div>

      {/* Header + Circuit Banner */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 style={{ margin: 0, fontSize: '1.18rem' }}>{stock.name}</h2>
            <span className="muted">{stock.sector[lang]} · {stock.code}</span>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 800, fontSize: '1.25rem' }}>₹{q.price.toFixed(2)}</div>
            <div className={q.change_pct >= 0 ? 'up' : 'down'} style={{ fontWeight: 600, fontSize: '0.85rem' }}>
              {q.change_pct >= 0 ? '+' : ''}{q.change_pct}% ({lang === 'hi' ? '5 दिन' : '5D'}: {q.change_5d_pct >= 0 ? '+' : ''}{q.change_5d_pct}%)
            </div>
          </div>
        </div>

        {q.circuit === 'LC' && (
          <div className="banner-danger" style={{ marginBottom: 10 }}>
            🔒 {t(lang, 'lowerCircuit')}
          </div>
        )}
        {q.circuit === 'UC' && (
          <div className="banner-warn" style={{ marginBottom: 10 }}>
            ⚡ {t(lang, 'upperCircuit')}
          </div>
        )}

        {/* Recharts Interactive Price Chart */}
        <div style={{ width: '100%', height: 190 }}>
          <ResponsiveContainer>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={stock.color} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={stock.color} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <XAxis dataKey="label" hide />
              <YAxis domain={['auto', 'auto']} width={46} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => [`₹${Number(v).toFixed(2)}`, 'Close']} />
              <Area type="monotone" dataKey="price" stroke={stock.color} strokeWidth={2.2} fill="url(#priceFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="grid-2" style={{ marginTop: 8, fontSize: '0.8rem' }}>
          <div className="muted">20D SMA: <strong>₹{q.sma_20d}</strong></div>
          <div className="muted">Vol: <strong>{q.volume.toLocaleString('en-IN')}</strong></div>
        </div>
      </div>

      {/* Alert Creator */}
      {showAlertBox && (
        <div className="card">
          <strong>🔔 {t(lang, 'setAlert')}</strong>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            <select className="select" value={alertRule} onChange={(e) => setAlertRule(e.target.value)}>
              {Object.entries(alertLabels).map(([k, label]) => (
                <option key={k} value={k}>{label}</option>
              ))}
            </select>
            {(alertRule === 'price_below' || alertRule === 'price_above') && (
              <input
                className="input"
                type="number"
                value={alertThreshold}
                onChange={(e) => setAlertThreshold(e.target.value)}
              />
            )}
            <button className="btn btn-primary btn-sm" onClick={handleSaveAlert}>
              {lang === 'hi' ? 'अलर्ट सेव करें' : 'Save Alert'}
            </button>
          </div>
        </div>
      )}

      {/* Fundamentals ⓘ Drawer */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: showFundamentals ? 8 : 0 }}>
          <strong>{t(lang, 'fundamentals')}</strong>
          <button className="btn btn-sm" onClick={handleToggleFundamentals}>
            {showFundamentals ? (lang === 'hi' ? 'छिपाएँ' : 'Hide') : (lang === 'hi' ? 'खोलें' : 'Inspect')}
          </button>
        </div>
        {showFundamentals && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.88rem' }}>
            <p style={{ margin: 0 }}>{stock.about[lang]}</p>
            <div className="grid-2">
              <div>M-Cap: <strong>₹{stock.fundamentals.mcap_cr.toLocaleString('en-IN')} Cr</strong></div>
              <div>P/E: <strong>{stock.fundamentals.pe ?? (lang === 'hi' ? 'घाटे में' : 'Loss-making')}</strong></div>
              <div>{lang === 'hi' ? 'कर्ज़' : 'Debt'}: <strong>{stock.fundamentals.debt_level.toUpperCase()}</strong></div>
              <div>{lang === 'hi' ? '3 साल बिक्री (Cr)' : '3Y Sales (Cr)'}: <strong>{stock.fundamentals.sales_3y_cr.join(' → ')}</strong></div>
            </div>
            {stock.fundamentals.red_flags.length > 0 && (
              <div className="banner-warn">
                ⚠️ {lang === 'hi' ? 'ध्यान देने योग्य संकेत' : 'Things to know'}: {stock.fundamentals.red_flags.map((f) => flagLabels[f] || f).join(' · ')}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Buy / Sell Order Panel */}
      <div className="card">
        <div className="chip-row" style={{ marginBottom: 10 }}>
          <button className={`chip ${side === 'buy' ? 'selected' : ''}`} onClick={() => { setSide('buy'); setQty(0); }}>
            {t(lang, 'buy')}
          </button>
          <button className={`chip ${side === 'sell' ? 'selected' : ''}`} onClick={() => { setSide('sell'); setQty(0); }}>
            {t(lang, 'sell')} {holding ? `(${holding.qty})` : '(0)'}
          </button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label className="muted">{t(lang, 'qty')}</label>
          {side === 'buy' && (
            <span className="muted" style={{ fontSize: '0.78rem' }}>
              {t(lang, 'freeCash')}: <strong>₹{freeCash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</strong>
            </span>
          )}
        </div>
        <input
          className="input"
          type="number"
          min={0}
          max={side === 'sell' ? (holding?.qty || 0) : 10000}
          value={qty}
          onChange={(e) => setQty(Math.max(0, parseInt(e.target.value || '0', 10)))}
          style={{ marginTop: 4 }}
        />

        {side === 'buy' && freeCash > q.price && (
          <div className="chip-row" style={{ marginTop: 8 }}>
            {[0.1, 0.25, 0.5].map((frac) => {
              const budget = freeCash * frac * (mtf ? 2 : 1);
              const calcQty = Math.max(1, Math.floor(budget / q.price));
              return (
                <button key={frac} type="button" className="btn btn-sm" onClick={() => setQty(calcQty)}>
                  {Math.round(frac * 100)}% {lang === 'hi' ? 'नक़द' : 'cash'}
                </button>
              );
            })}
          </div>
        )}

        {side === 'sell' && holding?.qty > 0 && (
          <>
            <div className="chip-row" style={{ marginTop: 8 }}>
              {[0.25, 0.5, 1].map((frac) => (
                <button
                  key={frac}
                  type="button"
                  className="btn btn-sm"
                  onClick={() => setQty(Math.max(1, Math.floor(holding.qty * frac)))}
                >
                  {frac === 1 ? t(lang, 'all') : `${frac * 100}%`}
                </button>
              ))}
            </div>
            <div style={{ marginTop: 10 }}>
              <div className="muted" style={{ marginBottom: 6 }}>
                {lang === 'hi' ? 'बेचने का कारण:' : 'Why are you selling?'}
              </div>
              <div className="chip-row">
                {SELL_REASONS.map((sr) => (
                  <button
                    key={sr.id}
                    type="button"
                    className={`chip ${sellReason === sr.id ? 'selected' : ''}`}
                    onClick={() => setSellReason(sr.id)}
                  >
                    {sr[lang]}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {side === 'buy' && experienced && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, fontSize: '0.86rem' }}>
            <input type="checkbox" checked={mtf} onChange={(e) => setMtf(e.target.checked)} />
            {t(lang, 'useMtf')}
          </label>
        )}

        <div className="muted" style={{ marginTop: 8 }}>
          {lang === 'hi' ? 'अनुमानित मूल्य' : 'Estimated Value'}:{' '}
          <strong>₹{(qty * q.price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</strong>
          {side === 'buy' && mtf && qty > 0 && (
            <span> ({lang === 'hi' ? 'अपना नक़द' : 'Own cash'}: ₹{((qty * q.price) / 2).toLocaleString('en-IN', { maximumFractionDigits: 0 })})</span>
          )}
        </div>

        <button
          className={`btn ${side === 'buy' ? 'btn-primary' : 'btn-danger'}`}
          style={{ width: '100%', marginTop: 12 }}
          disabled={qty <= 0 || day > 21}
          onClick={handleSubmitOrder}
        >
          {side === 'buy'
            ? (lang === 'hi' ? 'कारण जाँचें और आगे बढ़ें →' : 'Check Reasoning & Continue →')
            : `${t(lang, 'sell')} ${qty} ${stock.code}`}
        </button>
      </div>

      {/* Company-specific news */}
      {stockNews.length > 0 && (
        <div className="card">
          <strong>📰 {stock.name} {t(lang, 'newsFeed')}</strong>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
            {stockNews.map((n, i) => (
              <div key={i} className="muted" style={{ fontSize: '0.84rem' }}>
                <strong>{t(lang, 'dayLabel')} {n.day}:</strong> {n.text[lang]}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
