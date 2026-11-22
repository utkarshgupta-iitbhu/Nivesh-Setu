// Local-only storage manager (100% Privacy-by-Design: nothing saved on any server).

const KEY = 'niveshsetu_v1_state';

export const DEFAULT_STATE = {
  onboarded: false,
  lang: 'en',
  theme: 'light',
  name: '',
  experienced: false,
  statedCrashReaction: 'hold',
  startingCash: 100000,
  mode: 'guided',
  seed: 42,
  day: 1,
  orders: [],
  watchlist: {},
  alerts: [],
  research: {},
  seenTips: {},
};

export function loadState() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULT_STATE };
    return { ...DEFAULT_STATE, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_STATE };
  }
}

export function saveState(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // ignore private-browsing quota errors
  }
}

export function resetSeasonState(prev) {
  const nextSeed = prev.mode === 'practice' ? Math.floor(100 + Math.random() * 9000) : 42;
  return {
    ...DEFAULT_STATE,
    lang: prev.lang,
    theme: prev.theme,
    name: prev.name,
    seenTips: prev.seenTips || {},
    seed: nextSeed,
  };
}
