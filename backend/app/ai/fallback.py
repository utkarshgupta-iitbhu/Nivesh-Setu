"""Deterministic offline evaluators and fallback responses (Hindi + English).

Used in two situations:
1. `SARVAM_API_KEY` is not set (so anyone cloning the repo can test the full app immediately).
2. Sarvam times out or fails Layer 3 safety/number-grounding validation.
"""

from __future__ import annotations

import re
from typing import Any

_TIP_RE = re.compile(r"\b(tip|telegram|whatsapp|friend|youtube|insta|rumour|rumor|viral|influencer)\b|टिप|दोस्त|टेलीग्राम|अफ़वाह", re.IGNORECASE)
_FOMO_RE = re.compile(r"\b(running|rising|moon|rocket|fast|double|upper\s+circuit|fomo|trending)\b|भाग\s*रहा|तेज़|अपर\s*सर्किट|दोगुना", re.IGNORECASE)
_FUNDAMENTAL_RE = re.compile(r"\b(sales|profit|debt|pe|p/e|earnings|steady|long\s*term|diversif|monsoon|branch|business|revenue)\b|बिक्री|मुनाफ़ा|कर्ज़|लंबे\s*समय|कमाई|व्यापार", re.IGNORECASE)


def evaluate_reasoning_deterministic(
    *,
    reason_text: str,
    reason_tag: str,
    preview: dict[str, Any],
    opened_fundamentals: bool,
    read_news: bool,
    lang: str = "en",
) -> dict[str, Any]:
    """Deterministically score a buy reason (0-100) and produce a grounded 1-question pause card."""
    text = (reason_text or "").strip()
    flags: list[str] = []
    score = 55

    if reason_tag == "tip" or _TIP_RE.search(text):
        flags.append("tip")
        score -= 35
    if reason_tag == "rising" or _FOMO_RE.search(text) or preview["change_5d_pct"] >= 15.0:
        flags.append("fomo")
        score -= 22
    if _FUNDAMENTAL_RE.search(text):
        score += 22
    if opened_fundamentals:
        score += 15
    else:
        flags.append("no_fundamentals")
        score -= 10
    if read_news:
        score += 8
    if len(text) < 12:
        flags.append("too_brief")
        score -= 12
    if preview["post_trade_weight_pct"] >= 35.0:
        flags.append("high_concentration")
        score -= 10
    if preview["borrowed"] > 0:
        flags.append("mtf_leverage")
        score -= 10

    score = max(5, min(100, score))
    verdict = "sound" if score >= 70 and "tip" not in flags else ("mixed" if score >= 45 else "weak")

    loss_2s = preview["loss_on_2sigma_rupees"]
    drop_2s = preview["two_sigma_5d_drop_pct"]
    weight = preview["post_trade_weight_pct"]

    if lang == "hi":
        consequence = f"अगर यह शेयर 5 दिन में {drop_2s}% गिरे, तो इस ऑर्डर पर लगभग ₹{loss_2s:,.0f} का नुक़सान हो सकता है (कुल पोर्टफ़ोलियो का {weight}% हिस्सा)।"
        if preview["margin_call_price"]:
            consequence += f" 2× MTF पर ₹{preview['margin_call_price']} पर मार्जिन कॉल लग सकता है।"

        if verdict == "sound":
            question = ""
            right = "आपने ख़रीदने से पहले कंपनी के कारोबार और जोखिम पर सोचा।"
            missing = "अगर बाज़ार अचानक गिरे, तो पहले से तय रखें कि आप कितने समय तक रुकेंगे।"
            tip = "हर ऑर्डर से पहले 1 मिनट रुककर फ़ंडामेंटल्स ⓘ ज़रूर देखें।"
        elif "tip" in flags:
            question = "यह टिप देने वाला अगर ग़लत निकला और शेयर अटक गया, तो आपका कितना नुक़सान होगा?"
            right = "आपने ईमानदारी से बताया कि यह विचार कहाँ से आया।"
            missing = "टिप या अफ़वाह में कंपनी की बिक्री, मुनाफ़े और कर्ज़ की जानकारी नहीं होती।"
            tip = "किसी भी टिप पर पैसा लगाने से पहले कंपनी का कर्ज़ और 3 साल की बिक्री ख़ुद जाँचें।"
        else:
            question = f"इस कंपनी के फ़ंडामेंटल्स ⓘ देखे बिना पोर्टफ़ोलियो का {weight}% लगाना क्या आपके जोखिम के अनुकूल है?"
            right = "आपने ऑर्डर से पहले अपना कारण लिखने के लिए समय लिया।"
            missing = "क़ीमत की हालिया चाल के अलावा कंपनी के कर्ज़ और मुनाफ़े की जाँच बाक़ी है।"
            tip = "एक ही शेयर में 25% से ज़्यादा पैसा लगाने से बचें और पहले ⓘ ज़रूर पढ़ें।"
    else:
        consequence = f"A {drop_2s}% 5-day drop could cost roughly ₹{loss_2s:,.0f} on this order ({weight}% of your portfolio)."
        if preview["margin_call_price"]:
            consequence += f" With 2× MTF, a drop to ₹{preview['margin_call_price']} triggers a forced margin call."

        if verdict == "sound":
            question = ""
            right = "You anchored your decision in the company's fundamentals rather than hype."
            missing = "Even strong businesses swing during market crashes—decide your holding horizon now."
            tip = "Keep checking Fundamentals ⓘ and position size before every buy."
        elif "tip" in flags:
            question = "If the person behind this tip is wrong and buyers disappear, how much of this rupee loss can you absorb?"
            right = "You were honest about where this idea came from."
            missing = "Tips and social-media buzz hide whether the company actually makes a profit or carries heavy debt."
            tip = "Never act on a tip without checking 3-year sales, debt, and red flags under ⓘ first."
        else:
            question = f"Are you comfortable putting {weight}% of your portfolio here without checking all red flags under Fundamentals ⓘ?"
            right = "You paused to state a reason before placing the order."
            missing = "Your reason focuses more on price movement than on business earnings, debt, or downside risk."
            tip = "Aim to keep any single stock under 25% of your portfolio and review Fundamentals ⓘ first."

    return {
        "score": score,
        "verdict": verdict,
        "flags": flags,
        "question": question,
        "what_is_right": right,
        "what_is_missing": missing,
        "next_time_tip": tip,
        "consequence_text": consequence,
        "source": "offline_fallback",
    }


def fallback_coach_note(event_type: str, lang: str = "en") -> dict[str, Any]:
    notes_en = {
        "welcome": (
            "Welcome to Day 1",
            "Over the next 21 days, your goal isn't chasing the highest return—it's spotting traps and staying calm under pressure.",
            "Which habit do you want to watch most closely this season: avoiding FOMO or checking fundamentals?",
        ),
        "rumour_buzz": (
            "Watch out for social buzz",
            "When a small, loss-making stock jumps quickly on an unconfirmed rumour, volume spikes often signal hype rather than real earnings.",
            "Have you checked the company's 3-year sales and debt under Fundamentals ⓘ?",
        ),
        "lower_circuit_trap": (
            "Locked in Lower Circuit",
            "When a rumour collapses, sellers flood the market and buyers vanish—meaning even a stop-loss order cannot execute.",
            "How does experiencing a locked exit change how you'll treat future hot tips?",
        ),
        "crash_start": (
            "Market volatility spiked",
            "Broad market drops feel scary, and panic selling locks in temporary paper losses permanently.",
            "Does this drop match what you said you would do during onboarding?",
        ),
        "debt_shock": (
            "Debt trouble hits hard",
            "When a heavily indebted company misses a loan instalment, the stock can drop sharply even while the broader market recovers.",
            "Did you notice the high-debt red flag under Fundamentals ⓘ before today?",
        ),
        "recovery_start": (
            "Markets are steadying",
            "After a sharp multi-day fall, calm buying often returns gradually—which is why panic selling at the bottom hurts so much.",
            "How did your emotions change between the crash days and today?",
        ),
        "margin_call": (
            "Forced MTF margin call",
            "Borrowed money amplifies losses twice as fast and takes the exit decision out of your hands when equity falls below maintenance.",
            "Would you have survived this dip if you had used only your own cash?",
        ),
    }
    notes_hi = {
        "welcome": (
            "दिन 1 में स्वागत है",
            "अगले 21 दिनों में लक्ष्य सबसे ज़्यादा मुनाफ़ा नहीं, बल्कि ठगी से बचना और दबाव में शांत रहना सीखना है।",
            "इस सीज़न में आप किस आदत पर सबसे ज़्यादा ध्यान देना चाहेंगे—FOMO रोकना या फ़ंडामेंटल्स जाँचना?",
        ),
        "rumour_buzz": (
            "अफ़वाह और शोर से सावधान",
            "जब घाटे वाली छोटी कंपनी बिना पुष्टि के तेज़ी से भागती है, तो ज़्यादा वॉल्यूम अक्सर अफ़वाह का संकेत होता है।",
            "क्या आपने फ़ंडामेंटल्स ⓘ में इसकी 3 साल की बिक्री और कर्ज़ देखा?",
        ),
        "lower_circuit_trap": (
            "लोअर सर्किट में फँसाव",
            "जब अफ़वाह झूठी निकलती है, तो बेचने वाले बहुत होते हैं और ख़रीदार शून्य—इसलिए सेल ऑर्डर भी अटक जाता है।",
            "बाहर न निकल पाने के इस अनुभव के बाद आप अगली 'हॉट टिप' को कैसे देखेंगे?",
        ),
        "crash_start": (
            "बाज़ार में तेज़ गिरावट",
            "बाज़ार गिरने पर डर लगना स्वाभाविक है, पर घबराकर बेचने से अस्थायी घाटा पक्का हो जाता है।",
            "क्या आपका आज का फ़ैसला वही है जो आपने शुरुआत में कहा था?",
        ),
        "debt_shock": (
            "भारी कर्ज़ का झटका",
            "जब ज़्यादा कर्ज़ वाली कंपनी किस्त चूकती है, तो बाज़ार सुधरने पर भी उसका शेयर तेज़ी से गिर सकता है।",
            "क्या आपने आज से पहले फ़ंडामेंटल्स ⓘ में भारी कर्ज़ का संकेत देखा था?",
        ),
        "recovery_start": (
            "बाज़ार सँभल रहा है",
            "तेज़ गिरावट के बाद अक्सर धीरे-धीरे सुधार लौटता है—इसीलिए डर में निचले स्तर पर बेचने से ज़्यादा नुक़सान होता है।",
            "गिरावट के दिनों और आज के बीच आपके मन में क्या बदलाव आया?",
        ),
        "margin_call": (
            "MTF मार्जिन कॉल लगा",
            "उधार के पैसे (MTF) से घाटा दोगुनी तेज़ी से बढ़ता है और शेयर अपने आप बिक जाते हैं।",
            "अगर आपने केवल अपने नक़द पैसे लगाए होते, तो क्या आप इस गिरावट में टिक पाते?",
        ),
    }
    bank = notes_hi if lang == "hi" else notes_en
    title, note, question = bank.get(event_type, bank["welcome"])
    return {"title": title, "note": note, "question": question, "source": "offline_fallback"}


def fallback_report_narrative(scorecard: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    score = scorecard["resilience_score"]
    habits = sorted(scorecard["habits"], key=lambda h: h["score"])
    weakest = habits[0]["id"] if habits else "research"
    strongest = habits[-1]["id"] if habits else "leverage"

    if lang == "hi":
        return {
            "headline": f"आपका 21-दिन का निवेश लचीलापन स्कोर {score}/100 है।",
            "summary": f"इस सीज़न में आपकी सबसे मज़बूत आदत '{strongest}' रही और सबसे ज़्यादा सुधार की गुंजाइश '{weakest}' में है।",
            "rules": [
                "हर ख़रीद से पहले फ़ंडामेंटल्स ⓘ और कंपनी के कर्ज़ की जाँच करें।",
                "अफ़वाह या 5 दिन में 15%+ भाग चुके शेयर के पीछे न भागें।",
                "एक ही कंपनी में अपने कुल पैसे का 25% से ज़्यादा न लगाएँ।",
            ],
            "source": "offline_fallback",
        }
    return {
        "headline": f"Your 21-Day Investor Resilience Score is {score}/100.",
        "summary": f"Your strongest habit this season was '{strongest}', while '{weakest}' has the biggest room to improve.",
        "rules": [
            "Open Fundamentals ⓘ and check 3-year sales and debt before every buy.",
            "Pause whenever a stock has jumped 15%+ in 5 days or comes from a social-media tip.",
            "Keep any single company below 25% of your portfolio and avoid borrowed MTF leverage.",
        ],
        "source": "offline_fallback",
    }
