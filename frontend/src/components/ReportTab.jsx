import React, { useEffect, useState } from 'react';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/client';
import { useVoice } from '../api/voice';
import { TRANSLATIONS, t } from '../i18n/translations';

export default function ReportTab({ lang, state, onReset }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openFormula, setOpenFormula] = useState({});
  const [error, setError] = useState('');
  const { speakingId, toggleSpeak } = useVoice();

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .getReport({
        mode: state.mode,
        seed: state.seed,
        as_of_day: state.day,
        starting_cash: state.startingCash,
        orders: state.orders,
        stated_crash_reaction: state.statedCrashReaction,
        lang,
      })
      .then((res) => { if (active) setData(res); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [state.day, state.orders.length, lang]);

  if (loading) return <div className="page"><div className="card">{t(lang, 'loadingReport')}</div></div>;
  if (error) return <div className="page"><div className="banner-danger">{error}</div></div>;
  if (!data) return null;

  const { scorecard, narrative } = data;
  const bandColor = (band) => (band === 'good' ? '#15803d' : band === 'ok' ? '#b45309' : '#b91c1c');
  const habitNames = TRANSLATIONS[lang]?.habits || TRANSLATIONS.en.habits;
  const lessonTexts = TRANSLATIONS[lang]?.lessons || TRANSLATIONS.en.lessons;
  const crashLabels = TRANSLATIONS[lang]?.crashLabels || TRANSLATIONS.en.crashLabels;
  const chartData = scorecard.habits.map((h) => ({ ...h, label: habitNames[h.id] || h.id }));

  const handleResetClick = () => {
    if (window.confirm(t(lang, 'confirmReset'))) onReset();
  };

  return (
    <div className="page">
      {/* Top Score Card */}
      <div className="card" style={{ textAlign: 'center' }}>
        <div className="muted">{t(lang, 'resilienceScore')} ({t(lang, 'dayLabel')} {scorecard.day}/21)</div>
        <div style={{ fontSize: '2.6rem', fontWeight: 900, color: bandColor(scorecard.resilience_band) }}>
          {scorecard.resilience_score}<span style={{ fontSize: '1rem', color: 'var(--muted)' }}>/100</span>
        </div>
        <p style={{ margin: '6px 0' }}><strong>{narrative.headline}</strong></p>
        <p className="muted" style={{ margin: '0 0 10px' }}>{narrative.summary}</p>
        <button
          className="btn btn-sm"
          onClick={() => toggleSpeak('report_summary', `${narrative.headline}. ${narrative.summary}`, lang)}
        >
          {speakingId === 'report_summary' ? t(lang, 'stop') : t(lang, 'listen')}
        </button>
      </div>

      {/* Stated vs Actual Crash Reaction (readable bilingual labels!) */}
      <div className="card">
        <strong>⚡ {t(lang, 'statedVsActual')}</strong>
        <div className="grid-2" style={{ marginTop: 8, fontSize: '0.88rem' }}>
          <div>
            <div className="muted">{lang === 'hi' ? 'आपने कहा था:' : 'You said:'}</div>
            <strong>{crashLabels[scorecard.stated_vs_actual_crash.stated] || scorecard.stated_vs_actual_crash.stated}</strong>
          </div>
          <div>
            <div className="muted">{lang === 'hi' ? 'आपने किया:' : 'You did:'}</div>
            <strong>{crashLabels[scorecard.stated_vs_actual_crash.actual] || scorecard.stated_vs_actual_crash.actual}</strong>
          </div>
        </div>
      </div>

      {/* Recharts 9-Habit Bar Chart */}
      <div className="card">
        <strong>📊 {lang === 'hi' ? 'आपकी 9 आदतें (0–100)' : 'Your 9 Investing Habits (0–100)'}</strong>
        <div style={{ width: '100%', height: 240, marginTop: 8 }}>
          <ResponsiveContainer>
            <BarChart data={chartData} layout="vertical" margin={{ left: 12, right: 16 }}>
              <XAxis type="number" domain={[0, 100]} hide />
              <YAxis type="category" dataKey="label" width={118} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => [`${v}/100`, 'Score']} />
              <Bar dataKey="score" radius={[0, 6, 6, 0]}>
                {chartData.map((h) => (
                  <Cell key={h.id} fill={bandColor(h.band)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Transparent Formula Cards */}
      {scorecard.habits.map((h) => (
        <div key={h.id} className="card" style={{ padding: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>{habitNames[h.id] || h.id}</strong>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className={`pill ${h.band === 'good' ? 'pill-up' : h.band === 'ok' ? 'pill-warn' : 'pill-down'}`}>
                {h.score}/100
              </span>
              <button
                className="btn btn-sm"
                onClick={() => setOpenFormula((p) => ({ ...p, [h.id]: !p[h.id] }))}
              >
                {t(lang, 'howWeMeasure')}
              </button>
            </div>
          </div>
          {openFormula[h.id] && (
            <p className="muted" style={{ margin: '8px 0 0', fontSize: '0.82rem' }}>{h.formula[lang]}</p>
          )}
        </div>
      ))}

      {/* Targeted Trap Lessons */}
      {scorecard.lesson_topics?.length > 0 && (
        <div className="card">
          <strong>⚠️ {t(lang, 'trapLessons')}</strong>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            {scorecard.lesson_topics.map((topic) => (
              <div key={topic} className="banner-warn" style={{ fontSize: '0.86rem' }}>
                {lessonTexts[topic] || topic}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3 Personal Rules */}
      <div className="card">
        <strong>🧭 {t(lang, 'personalRules')}</strong>
        <ol style={{ margin: '8px 0 0', paddingLeft: 20, fontSize: '0.9rem' }}>
          {(narrative.rules || []).map((r, i) => (
            <li key={i} style={{ marginBottom: 6 }}>{r}</li>
          ))}
        </ol>
      </div>

      {/* Honest Educational Disclaimer */}
      <div className="muted" style={{ fontSize: '0.8rem', textAlign: 'center', padding: '0 6px' }}>
        {t(lang, 'scenarioDisclaimer')}
      </div>

      <button className="btn btn-primary" onClick={handleResetClick}>{t(lang, 'resetSeason')}</button>
    </div>
  );
}
