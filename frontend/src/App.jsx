import React, { useEffect, useRef, useState } from 'react';
import { api } from './api/client';
import { stopSpeaking } from './api/voice';
import { t } from './i18n/translations';
import { loadState, resetSeasonState, saveState } from './state/storage';
import Onboarding from './components/Onboarding';
import TopBar from './components/TopBar';
import ExploreTab from './components/ExploreTab';
import StockDetail from './components/StockDetail';
import ReasoningGate from './components/ReasoningGate';
import PortfolioTab from './components/PortfolioTab';
import ReportTab from './components/ReportTab';
import AskDrawer from './components/AskDrawer';

export default function App() {
  const [state, setState] = useState(() => loadState());
  const [tab, setTab] = useState('explore');
  const [selectedCode, setSelectedCode] = useState(null);
  const [market, setMarket] = useState(null);
  const [portfolio, setPortfolio] = useState({
    starting_cash: state.startingCash,
    cash: state.startingCash,
    equity: state.startingCash,
    total_interest_paid: 0,
    holdings: {},
    total_borrowed: 0,
  });
  const [aiEnabled, setAiEnabled] = useState(false);
  const [coachNote, setCoachNote] = useState(null);
  const [pendingBuy, setPendingBuy] = useState(null);
  const [triggeredAlerts, setTriggeredAlerts] = useState([]);
  const [toast, setToast] = useState('');
  const [showAsk, setShowAsk] = useState(false);
  const prevMarginCallsRef = useRef(0);

  useEffect(() => {
    saveState(state);
    document.documentElement.setAttribute('data-theme', state.theme);
  }, [state]);

  useEffect(() => {
    stopSpeaking();
  }, [tab, selectedCode, state.day]);

  useEffect(() => {
    api.health().then((h) => setAiEnabled(Boolean(h.ai_enabled))).catch(() => setAiEnabled(false));
  }, []);

  useEffect(() => {
    if (!state.onboarded) return;
    let active = true;
    setCoachNote(null); // Never show an older day's coach note on a new day

    api
      .getMarket(state.mode, state.seed, state.day)
      .then((snap) => {
        if (!active) return;
        setMarket(snap);
        if (snap.coach_event) {
          api
            .getCoach({
              mode: state.mode,
              seed: state.seed,
              day: state.day,
              lang: state.lang,
              starting_cash: state.startingCash,
              orders: state.orders,
              event_type: snap.coach_event,
            })
            .then((note) => { if (active) setCoachNote(note); })
            .catch(() => {});
        }
      })
      .catch((e) => { if (active) setToast(e.message); });

    return () => { active = false; };
  }, [state.onboarded, state.mode, state.seed, state.day, state.lang]);

  // Sync portfolio via zero-LLM /api/report/score (instant, never burns Sarvam quota)
  useEffect(() => {
    if (!state.onboarded) return;
    let active = true;
    api
      .getScore({
        mode: state.mode,
        seed: state.seed,
        as_of_day: state.day,
        starting_cash: state.startingCash,
        orders: state.orders,
      })
      .then((scorecard) => {
        if (!active) return;
        const s = scorecard.portfolio_summary;
        setPortfolio({
          starting_cash: s.starting_cash,
          cash: s.cash,
          equity: s.final_equity,
          total_interest_paid: s.total_interest_paid || 0,
          total_borrowed: s.total_borrowed || 0,
          holdings: s.holdings || {},
        });
        if (s.margin_calls > prevMarginCallsRef.current) {
          prevMarginCallsRef.current = s.margin_calls;
          setToast(
            state.lang === 'hi'
              ? '⚠️ MTF मार्जिन कॉल लगा — आपका उधार वाला शेयर अपने आप बिक गया!'
              : '⚠️ Forced MTF Margin Call — your leveraged position was squared off!'
          );
          api
            .getCoach({
              mode: state.mode,
              seed: state.seed,
              day: state.day,
              lang: state.lang,
              starting_cash: state.startingCash,
              orders: state.orders,
              event_type: 'margin_call',
            })
            .then((note) => { if (active) setCoachNote(note); })
            .catch(() => {});
        }
      })
      .catch(() => {});
    return () => { active = false; };
  }, [state.onboarded, state.mode, state.seed, state.day, state.orders.length]);

  if (!state.onboarded) {
    return <Onboarding initialState={state} onComplete={(next) => setState(next)} />;
  }

  const handleReset = () => {
    stopSpeaking();
    prevMarginCallsRef.current = 0;
    setCoachNote(null);
    setTriggeredAlerts([]);
    setToast('');
    setSelectedCode(null);
    setState((p) => resetSeasonState(p));
    setPortfolio({
      starting_cash: state.startingCash,
      cash: state.startingCash,
      equity: state.startingCash,
      total_interest_paid: 0,
      holdings: {},
      total_borrowed: 0,
    });
    setTab('explore');
  };

  const handleImportState = (imported) => {
    stopSpeaking();
    setState((prev) => ({ ...prev, ...imported, onboarded: true }));
    setToast(state.lang === 'hi' ? 'बैकअप लोड हो गया ✓' : 'Backup restored ✓');
  };

  const handleDismissTip = (tipKey) => {
    setState((p) => ({ ...p, seenTips: { ...(p.seenTips || {}), [tipKey]: true } }));
  };

  const handleTrackResearch = (code, field) => {
    setState((prev) => ({
      ...prev,
      research: {
        ...prev.research,
        [code]: { ...(prev.research[code] || {}), [field]: true },
      },
    }));
  };

  const handleToggleWatch = (code) => {
    setState((prev) => {
      const nextWatch = { ...prev.watchlist };
      if (nextWatch[code]) delete nextWatch[code];
      else nextWatch[code] = prev.day;
      return { ...prev, watchlist: nextWatch };
    });
  };

  const handleNextDay = async () => {
    if (state.day >= 21) return;
    const nextDay = state.day + 1;
    setState((prev) => ({ ...prev, day: nextDay }));
    setSelectedCode(null);

    if (state.alerts.length > 0) {
      try {
        const res = await api.evaluateAlerts({
          mode: state.mode,
          seed: state.seed,
          day: nextDay,
          alerts: state.alerts,
        });
        setTriggeredAlerts(res.triggered || []);
        if (res.triggered?.length) {
          const firedIds = new Set(res.triggered.map((x) => x.id));
          setState((prev) => ({ ...prev, alerts: prev.alerts.filter((a) => !firedIds.has(a.id)) }));
        }
      } catch {
        setTriggeredAlerts([]);
      }
    } else {
      setTriggeredAlerts([]);
    }

    if (nextDay === 21) setTab('report');
  };

  const executeOrder = async (orderPayload) => {
    try {
      const res = await api.validateOrder({
        mode: state.mode,
        seed: state.seed,
        starting_cash: state.startingCash,
        existing_orders: state.orders,
        new_order: orderPayload,
      });
      setPortfolio(res.portfolio);
      setState((prev) => ({ ...prev, orders: [...prev.orders, orderPayload] }));
      setToast(`${orderPayload.side.toUpperCase()} ${orderPayload.qty} ${orderPayload.code} ✓`);
      setPendingBuy(null);
      setSelectedCode(null);
    } catch (err) {
      const msg = err.detail?.[state.lang] || err.message;
      setToast(msg);
      if (err.detail?.code === 'LOWER_CIRCUIT_LOCK') {
        api
          .getCoach({
            mode: state.mode,
            seed: state.seed,
            day: state.day,
            lang: state.lang,
            starting_cash: state.startingCash,
            orders: state.orders,
            event_type: 'lower_circuit_trap',
          })
          .then(setCoachNote)
          .catch(() => {});
      }
    }
  };

  const handleConfirmBuy = (buyData) => {
    const r = state.research[buyData.code] || {};
    const watchedBefore = Boolean(state.watchlist[buyData.code] && state.watchlist[buyData.code] < state.day);
    executeOrder({
      day: state.day,
      code: buyData.code,
      side: 'buy',
      qty: buyData.qty,
      mtf: buyData.mtf,
      reason_tag: buyData.reason_tag,
      reason_text: buyData.reason_text,
      think_ms: buyData.thinkMs,
      meta: {
        opened_fundamentals: Boolean(r.info),
        read_news: Boolean(r.news),
        viewed_chart: Boolean(r.chart),
        watched_before: watchedBefore,
        gate_score: buyData.gate_score,
        gate_verdict: buyData.gate_verdict,
        gate_flags: buyData.gate_flags,
      },
    });
  };

  const handleDirectSell = ({ code, qty, thinkMs, reason_tag }) => {
    executeOrder({
      day: state.day,
      code,
      side: 'sell',
      qty,
      mtf: false,
      reason_tag: reason_tag || 'target',
      reason_text: `Manual sell (${reason_tag || 'target'})`,
      think_ms: thinkMs,
      meta: {},
    });
  };

  const selectedStock = market?.stocks?.find((s) => s.code === selectedCode) || null;

  return (
    <div className="app-shell">
      <TopBar
        lang={state.lang}
        theme={state.theme}
        day={state.day}
        seasonDays={21}
        aiEnabled={aiEnabled}
        onNextDay={handleNextDay}
        onToggleLang={() => setState((p) => ({ ...p, lang: p.lang === 'en' ? 'hi' : 'en' }))}
        onToggleTheme={() => setState((p) => ({ ...p, theme: p.theme === 'dark' ? 'light' : 'dark' }))}
        onOpenAsk={() => setShowAsk(true)}
      />

      {toast && (
        <div className="page" style={{ paddingBottom: 0 }}>
          <div className="banner-warn" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{toast}</span>
            <button className="btn btn-sm" onClick={() => setToast('')}>✕</button>
          </div>
        </div>
      )}

      {selectedStock ? (
        <StockDetail
          lang={state.lang}
          stock={selectedStock}
          day={state.day}
          holding={portfolio.holdings?.[selectedStock.code]}
          freeCash={portfolio.cash}
          experienced={state.experienced}
          marketNews={market?.news}
          onBack={() => setSelectedCode(null)}
          onTrackResearch={handleTrackResearch}
          onStartBuy={(b) => setPendingBuy(b)}
          onDirectSell={handleDirectSell}
          onAddAlert={(al) => {
            setState((p) => ({ ...p, alerts: [...p.alerts, al] }));
            setToast(state.lang === 'hi' ? 'सूचना अलर्ट सेव हो गया 🔔' : 'Notification alert saved 🔔');
          }}
        />
      ) : tab === 'explore' || tab === 'watchlist' ? (
        <ExploreTab
          lang={state.lang}
          name={state.name}
          market={market}
          coachNote={coachNote}
          onDismissCoach={() => setCoachNote(null)}
          watchlist={state.watchlist}
          onlyWatchlist={tab === 'watchlist'}
          triggeredAlerts={triggeredAlerts}
          showTip={!state.seenTips?.explore}
          onDismissTip={() => handleDismissTip('explore')}
          onSelectStock={(code) => setSelectedCode(code)}
          onToggleWatch={handleToggleWatch}
        />
      ) : tab === 'portfolio' || tab === 'orders' ? (
        <PortfolioTab
          lang={state.lang}
          mode={tab}
          state={state}
          portfolio={portfolio}
          orders={state.orders}
          alerts={state.alerts}
          market={market}
          showTip={!state.seenTips?.portfolio}
          onDismissTip={() => handleDismissTip('portfolio')}
          onSelectStock={(code) => setSelectedCode(code)}
          onDeleteAlert={(id) => setState((p) => ({ ...p, alerts: p.alerts.filter((a) => a.id !== id) }))}
          onImportState={handleImportState}
          onReset={handleReset}
        />
      ) : (
        <ReportTab lang={state.lang} state={state} onReset={handleReset} />
      )}

      {pendingBuy && selectedStock && (
        <ReasoningGate
          lang={state.lang}
          pendingBuy={pendingBuy}
          stock={selectedStock}
          state={state}
          onCancel={() => setPendingBuy(null)}
          onConfirmBuy={handleConfirmBuy}
        />
      )}

      {showAsk && <AskDrawer lang={state.lang} onClose={() => setShowAsk(false)} />}

      <nav className="bottom-nav">
        {[
          { id: 'explore', icon: '📈', label: t(state.lang, 'explore') },
          { id: 'watchlist', icon: '★', label: t(state.lang, 'watchlist') },
          { id: 'portfolio', icon: '💼', label: t(state.lang, 'portfolio') },
          { id: 'orders', icon: '🧾', label: t(state.lang, 'orders') },
          { id: 'report', icon: '📊', label: t(state.lang, 'report') },
        ].map((item) => (
          <button
            key={item.id}
            className={`nav-btn ${tab === item.id && !selectedCode ? 'active' : ''}`}
            onClick={() => {
              setSelectedCode(null);
              setTab(item.id);
            }}
          >
            <span style={{ fontSize: '1.05rem' }}>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
