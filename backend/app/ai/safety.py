"""3-Layer SEBI-Compliant Safety Guardrail for NiveshSetu.

Layer 1 (Pre-LLM):  `is_advice_request()` blocks stock tips / buy-sell requests
                    deterministically BEFORE any AI call is made.
Layer 2 (Prompt):   System prompts forbid advice, predictions, and future-day leaks.
Layer 3 (Post-LLM): `validate_output()` rejects any AI reply containing advice
                    phrases, directives, or invented numbers not present in the
                    server-computed facts — triggering an automatic safe fallback.
"""

from __future__ import annotations

import re
from typing import Any

# Devanagari digits -> Latin digits so Hindi numbers are verified too
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Layer 1: User asking for a stock tip, recommendation, or price target (EN + HI)
_ADVICE_REQUEST_RE = re.compile(
    r"("
    r"\b(should\s+i|can\s+i|is\s+it\s+good\s+to)\s+(buy|sell|hold|invest\s+in)\b|"
    r"\b(which|what)\s+(stock|share|company)\s+(should\s+i|to)\s+(buy|pick|invest)\b|"
    r"\b(best|top|multibagger)\s+(stock|share)s?\s+to\s+buy\b|"
    r"\b(target\s+price|price\s+prediction|will\s+.+\s+go\s+up|will\s+.+\s+crash)\b|"
    r"\bgive\s+me\s+(a\s+)?(stock\s+)?tip\b|"
    r"(खरीदूँ|ख़रीदूँ|खरीदना\s+चाहिए|बेचना\s+चाहिए|कौन\s*सा\s*शेयर\s*खरीद|टारगेट\s*प्राइस|"
    r"कब\s*खरीद|कब\s*बेच|पैसा\s*लगाऊँ|ऊपर\s*जाएगा\s*क्या|नीचे\s*जाएगा\s*क्या)"
    r")",
    re.IGNORECASE,
)

# Layer 3 (strict): AI output giving buy/sell/hold advice or judging a stock as good/bad
_ADVICE_OUTPUT_RE = re.compile(
    r"("
    r"\b(you\s+should|i\s+recommend|i\s+suggest|go\s+ahead\s+and)\s+(buy|sell|hold|invest|avoid|skip)\b|"
    r"\b(buy|sell|hold)\s+(it|this|the\s+stock)\s+(now|today|immediately)\b|"
    r"\b(good|great|best|bad|terrible)\s+(stock|share|company|time)\s+to\s+(buy|sell|invest)\b|"
    r"\b(guaranteed\s+returns?|sure\s+profit|target\s+price|will\s+double|will\s+rise\s+to)\b|"
    r"(खरीद\s*(लो|लें|लीजिए|डालो)|ख़रीद\s*(लो|लें|लीजिए)|बेच\s*(दो|दें|दीजिए)|"
    r"होल्ड\s*(करो|करें|कीजिए)|निवेश\s*(करो|करें|कीजिए)|"
    r"अच्छा\s*शेयर\s*है|बुरा\s*शेयर\s*है|टारगेट\s*प्राइस|पक्का\s*मुनाफ़ा|पक्का\s*फायदा)"
    r")",
    re.IGNORECASE,
)

# Layer 3 (coach): Strips quoted text first, then blocks direct commands
_QUOTED_RE = re.compile(r'"[^"]*"|“[^”]*”|\'[^\']{6,}\'|‘[^’]*’')


def is_advice_request(text: str) -> bool:
    """Layer 1: Return True if the user is asking for a stock tip or prediction."""
    return bool(_ADVICE_REQUEST_RE.search(text or ""))


def looks_like_advice(text: str) -> bool:
    """Layer 3 (strict): Return True if text reads like investment advice."""
    return bool(_ADVICE_OUTPUT_RE.search(text or ""))


def looks_like_directive(text: str) -> bool:
    """Layer 3 (coach): Ignore quoted phrases, then block direct buy/sell instructions."""
    cleaned = _QUOTED_RE.sub(" ", text or "")
    return bool(_ADVICE_OUTPUT_RE.search(cleaned))


def _extract_numbers(text: str) -> list[float]:
    normalized = (text or "").translate(_DEV_DIGITS)
    # Remove Indian/Western commas inside numbers (e.g. 1,00,000 -> 100000)
    normalized = re.sub(r"(?<=\d),(?=\d)", "", normalized)
    return [float(m.group(0)) for m in re.finditer(r"\d+(?:\.\d+)?", normalized)]


def numbers_grounded(output_text: str, facts_text: str) -> bool:
    """Ensure every number > 12 in the AI output appears in `facts_text` (within 3% or ±1).

    Small counting numbers (0..12, e.g. "2 days", "3 rules") are allowed naturally.
    Any larger figure (prices, ₹ losses, percentages, P/E, market cap) MUST come
    from the server-computed facts string.
    """
    allowed = _extract_numbers(facts_text)
    for n in _extract_numbers(output_text):
        if n <= 12.0:
            continue
        if not any(abs(n - f) <= max(1.0, abs(f) * 0.03) for f in allowed):
            return False
    return True


def validate_text_output(
    text: str,
    facts_text: str,
    *,
    max_len: int = 900,
    coach_mode: bool = False,
) -> str | None:
    """Return an error reason string if invalid, or None if the text passes all checks."""
    if not text or len(text.strip()) < 10:
        return "empty"
    if len(text) > max_len:
        return "too_long"
    if coach_mode:
        if looks_like_directive(text):
            return "advice"
    else:
        if looks_like_advice(text):
            return "advice"
    if facts_text and not numbers_grounded(text, facts_text):
        return "ungrounded_number"
    return None


def validate_json_output(
    obj: Any,
    facts_text: str,
    *,
    required_keys: tuple[str, ...] = (),
    max_field_len: int = 600,
    coach_mode: bool = False,
) -> str | None:
    """Validate every string inside a structured JSON response from the LLM."""
    if not isinstance(obj, dict):
        return "not_object"
    for k in required_keys:
        if k not in obj:
            return f"missing_key:{k}"

    strings: list[str] = []

    def _walk(val: Any) -> None:
        if isinstance(val, str):
            strings.append(val)
        elif isinstance(val, list):
            for item in val:
                _walk(item)
        elif isinstance(val, dict):
            for item in val.values():
                _walk(item)

    _walk(obj)
    for s in strings:
        if len(s) > max_field_len:
            return "too_long"
        if coach_mode:
            if looks_like_directive(s):
                return "advice"
        else:
            if looks_like_advice(s):
                return "advice"
        if facts_text and not numbers_grounded(s, facts_text):
            return "ungrounded_number"
    return None


def advice_refusal_message(lang: str = "en") -> dict[str, str]:
    """Standard SEBI-aligned refusal when a user asks for a stock tip."""
    if lang == "hi":
        return {
            "text": (
                "मैं कोई स्टॉक टिप, ख़रीदने/बेचने की सलाह या टारगेट प्राइस नहीं दे सकता। "
                "निवेश सेतु केवल आपको जोखिम समझना, फ़ंडामेंटल्स पढ़ना और शांत रहकर निर्णय लेना सिखाता है।"
            ),
            "source": "guardrail_refusal",
        }
    return {
        "text": (
            "I cannot give stock tips, buy/sell/hold advice, or price predictions. "
            "NiveshSetu only helps you understand risk, check fundamentals, and make calmer decisions."
        ),
        "source": "guardrail_refusal",
    }
