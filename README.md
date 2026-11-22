# NiveshSetu (निवेश सेतु) — 21-Day Investor Resilience Simulator (v2)

A public-good, no-login, Hindi + English **21-day investor resilience & habit simulator** built as an installable **React PWA** backed by a **Python (FastAPI)** quantitative engine and a **3-layer defense-in-depth Sarvam AI safety guardrail**.

Inspired by **SEBI & NSDL** investor-protection principles:
- **Zero stock tips & zero live tickers:** 100% fictional companies, pretend money, no broker or affiliate links.
- **Privacy by design:** No login or server-side user database — progress stays in browser `localStorage` with user-controlled JSON export/import. When Sarvam AI is enabled, short voice clips are sent to Sarvam for transcription and immediately discarded.
- **Consequence-first learning:** Real **Lower-Circuit exit traps** (zero buyers), EWMA-style **volatility clustering**, **2× MTF margin calls**, and pre-trade rupee downside estimates.

## Architecture

```text
┌──────────────────────────────┐        HTTPS / JSON        ┌─────────────────────────────────────────┐
│   React + Vite PWA (Phone)   │ ─────────────────────────► │        Python FastAPI Backend           │
│  • localStorage + JSON backup│                            │  • 21-Day Seeded Regime Simulator       │
│  • Recharts Stock & Habit UI │ ◄───────────────────────── │  • Pure-Function Server Portfolio Replay│
│  • Full Hindi + English i18n │   Day-bounded snapshots    │  • 9-Habit Deterministic Scoring Engine │
│  • Centralized Voice Manager │   (zero future leakage)    │  • 3-Layer Prototype Safety Guardrail   │
└──────────────────────────────┘                            │  • Rate Limiter (30 req/m) & 4MB Cap    │
                                                            └────────────────────┬────────────────────┘
                                                                                 │ (optional)
                                                                                 ▼
                                                            ┌─────────────────────────────────────────┐
                                                            │             Sarvam AI API               │
                                                            │  • Chat (sarvam-105b-conversations)     │
                                                            │  • Voice TTS (bulbul:v3 · Simran)       │
                                                            │  • Voice STT (saarika:v2.5)             │
                                                            │  ↳ Auto deterministic fallback if off   │
                                                            └─────────────────────────────────────────┘
```

## Key Technical Highlights

### 1. 21-Day Quantitative Market & Portfolio Engine (`backend/app/market/`)
- **Guided Mode + Practice Mode:** Guided Mode delivers an illustrative 21-day learning arc (calm → rumour pump → crash + 2-day Lower-Circuit trap → debt default → Day-21 graduation). Practice Mode generates reproducible seasons from any integer seed using a 4-state **Regime-Switching generator** (`CALM` → `HYPE` → `CRASH` → `RECOVERY`).
- **Volatility Clustering & Lower Circuits:** Daily volatility scales dynamically during stress windows, volume spikes during rumour pumps, and Lower-Circuit (`LC`) days reject sell orders with zero buyers.
- **Server-Side Portfolio Replay:** Every order preview, validation, and report replays the user's ledger deterministically on the server (including 0.05%/day MTF interest and automatic 50% maintenance margin calls).

### 2. Deterministic 9-Habit Behavioural Scoring (`backend/app/scoring/habits.py`)
All habit scores (0–100) are calculated by transparent mathematical formulas—never invented by an LLM:
- **Research Depth (17%)**, **Reasoning Quality (17%)**, **Crash Composure (15%)**, **FOMO Control (14%)**, **Concentration (12%)**, **Thinking Time (10%)**, **Leverage Discipline (7%)**, **Churn/Overtrading (4%)**, and **Pause Adherence (4%)**.
- Compares the user's **stated crash reaction** from onboarding against their **actual behaviour** during the crash window.

### 3. 3-Layer Prototype Safety Guardrail & Hardening (`backend/app/ai/safety.py`, `security.py`)
1. **Layer 1 (Pre-LLM):** Deterministic regex gate blocks common English and Hindi stock-tip/buy-sell/target-price requests *before* calling Sarvam.
2. **Layer 2 (Prompt):** Strict prompts evaluate the user's *reasoning* (never the stock) using only server-computed facts.
3. **Layer 3 (Post-LLM):** Validates every string in the AI's JSON reply for advice/directives and checks `numbers_grounded()` (across both Latin and Devanagari digits `०-९`). Any hallucinated figure rejects the AI reply and falls back cleanly.
4. **API Hardening:** Sliding-window per-IP rate limiting (30 req/min on AI/voice routes), 4 MB audio upload cap, and bounded Pydantic schemas (max 200 orders, max 50 alerts).

## Known Limitations & Future Roadmap
- **Prototype safety layer:** Regex + number-grounding significantly reduces unsafe LLM outputs, but is a prototype engineering guardrail rather than formal regulatory certification.
- **Backend connectivity:** While AI coaching degrades to deterministic offline fallbacks and the PWA shell caches locally, market snapshots and server-side order replay require the FastAPI backend.
- **Next steps:** Migrate frontend API contracts to TypeScript + OpenAPI codegen, add Vitest frontend tests, and expand verified regional languages.

## Run Locally (Windows PowerShell)

### 1. Start FastAPI Backend (`http://localhost:8000`)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```
*(Optional: copy `.env.example` to `.env` in the repo root, add `SARVAM_API_KEY`, and restart `uvicorn`. Leave blank for deterministic AI fallback mode.)*

### 2. Start React PWA Frontend (`http://localhost:5173`)
```powershell
cd frontend
npm install
npm run dev
```

## Deploy for Free on Vercel (Single URL)
Both the React PWA and Python FastAPI backend deploy together via `vercel.json` + `api/index.py`:
1. Import your GitHub repo on [Vercel](https://vercel.com) with **Root Directory** set to `./`.
2. *(Optional)* Add `SARVAM_API_KEY` under **Project Settings → Environment Variables** (leave unset to run in deterministic AI fallback mode).
3. Click **Deploy** — `/api/*` routes directly to FastAPI on the same domain with zero CORS configuration.
