"""Fictional company catalog and 21-day Guided Story definition (Hindi + English).

Guardrail: Every company, index, price, and news headline here is 100% fictional.
No real NSE/BSE tickers or live market data are ever used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SEASON_DAYS: int = 21          # 21-day habit-building cycle
PRE_DAYS: int = 60             # 60 days of pre-season chart history (for 3M chart & 20D SMA)
GUIDED_CRASH_WINDOW: tuple[int, int] = (8, 12)


@dataclass(frozen=True)
class BilingualText:
    en: str
    hi: str

    def to_dict(self) -> dict[str, str]:
        return {"en": self.en, "hi": self.hi}


@dataclass(frozen=True)
class Fundamentals:
    mcap_cr: int                              # Fictional market cap in ₹ crore
    pe: float | None                          # Price-to-Earnings (None if loss-making)
    sales_3y_cr: tuple[int, int, int]         # 3-year sales trend in ₹ crore
    profit_trend: Literal["up", "down", "loss"]
    debt_level: Literal["low", "mid", "high", "bank"]
    red_flags: tuple[str, ...] = ()           # Disclosed warning tags shown under Fundamentals ⓘ


@dataclass(frozen=True)
class Company:
    code: str
    name: str
    color: str
    base_price: float                         # Day-0 starting price in ₹
    beta: float                               # Sensitivity to the overall market index
    daily_vol_pct: float                      # Company's own daily volatility (%)
    drift_pct: float                          # Small daily drift during pre-season history (%)
    sector: BilingualText
    about: BilingualText
    fundamentals: Fundamentals
    guided_events: dict[int, float] = field(default_factory=dict)  # Day -> scripted % shock
    guided_lower_circuits: tuple[int, ...] = ()                    # Days with 0-buyer LC lock


@dataclass(frozen=True)
class IndexDef:
    id: str
    name: str
    base_value: float
    beta: float


@dataclass(frozen=True)
class NewsItem:
    day: int
    text: BilingualText
    stock_code: str | None = None
    severity: Literal["info", "rumour", "warning", "crash"] = "info"

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "stock_code": self.stock_code,
            "severity": self.severity,
            "text": self.text.to_dict(),
        }


# ── 8 Fictional Companies ─────────────────────────────────────────────────────
COMPANIES: tuple[Company, ...] = (
    Company(
        code="SAHYURJA",
        name="Sahyadri Urja Ltd",
        color="#F59E0B",
        base_price=182.0,
        beta=0.45,
        daily_vol_pct=0.6,
        drift_pct=0.05,
        sector=BilingualText(en="Power", hi="बिजली"),
        about=BilingualText(
            en="Generates and distributes power across Maharashtra and Karnataka. Slow, steady earnings.",
            hi="महाराष्ट्र और कर्नाटक में बिजली बनाती और बाँटती है। कमाई धीमी पर नियमित।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=18400, pe=14.0, sales_3y_cr=(4120, 4380, 4610),
            profit_trend="up", debt_level="mid",
        ),
    ),
    Company(
        code="GANGOTRI",
        name="Gangotri Foods Ltd",
        color="#10B981",
        base_price=645.0,
        beta=0.55,
        daily_vol_pct=0.7,
        drift_pct=0.06,
        sector=BilingualText(en="Packaged Food", hi="खाने का सामान"),
        about=BilingualText(
            en="Makes flour, biscuits, and snacks sold across small towns and cities.",
            hi="आटा, बिस्किट और नमकीन बनाती है। गाँव-शहर दोनों में बिकता है।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=52300, pe=38.0, sales_3y_cr=(7900, 8650, 9480),
            profit_trend="up", debt_level="low",
        ),
        guided_events={6: 2.5},
    ),
    Company(
        code="NAVYUGBK",
        name="Navyug Bank Ltd",
        color="#3B82F6",
        base_price=312.0,
        beta=1.35,
        daily_vol_pct=1.0,
        drift_pct=0.05,
        sector=BilingualText(en="Banking", hi="बैंक"),
        about=BilingualText(
            en="Private bank with 900 branches in Tier-2 and Tier-3 towns. Takes deposits and gives loans.",
            hi="छोटे शहरों में 900 शाखाओं वाला निजी बैंक। लोन और जमा का काम।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=61200, pe=12.0, sales_3y_cr=(11800, 13100, 14250),
            profit_trend="up", debt_level="bank",
        ),
        guided_events={10: -2.5, 17: 3.0},
    ),
    Company(
        code="VIKISPAT",
        name="Vikram Ispat Ltd",
        color="#94A3B8",
        base_price=96.0,
        beta=1.60,
        daily_vol_pct=1.4,
        drift_pct=0.02,
        sector=BilingualText(en="Steel", hi="स्टील"),
        about=BilingualText(
            en="Makes steel sheets and bars. Has borrowed heavily over the past three years.",
            hi="स्टील की चादरें और सरिया बनाती है। पिछले तीन सालों में बहुत कर्ज़ लिया है।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=6100, pe=31.0, sales_3y_cr=(9800, 9200, 8900),
            profit_trend="down", debt_level="high",
            red_flags=("high_debt", "falling_sales"),
        ),
        guided_events={14: -12.0, 15: -4.0, 16: -3.0, 18: -1.5},
    ),
    Company(
        code="CHANDNI",
        name="Chandni Pharma Ltd",
        color="#EC4899",
        base_price=1240.0,
        beta=0.50,
        daily_vol_pct=0.8,
        drift_pct=0.05,
        sector=BilingualText(en="Medicines", hi="दवाइयाँ"),
        about=BilingualText(
            en="Manufactures affordable medicines for fever, diabetes, and blood pressure.",
            hi="बुख़ार, शुगर और BP की सस्ती दवाइयाँ बनाती है।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=33800, pe=27.0, sales_3y_cr=(5200, 5650, 6100),
            profit_trend="up", debt_level="low",
        ),
    ),
    Company(
        code="ROCKINFR",
        name="Rocket Infra Ltd",
        color="#EF4444",
        base_price=38.0,
        beta=0.30,
        daily_vol_pct=0.4,
        drift_pct=0.0,
        sector=BilingualText(en="Construction", hi="निर्माण"),
        about=BilingualText(
            en="Small road and bridge contractor. Loss-making for two years with heavy promoter debt.",
            hi="सड़क और पुल बनाने के छोटे ठेके लेती है। दो साल से घाटे में और भारी कर्ज़ है।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=410, pe=None, sales_3y_cr=(190, 160, 150),
            profit_trend="loss", debt_level="high",
            red_flags=("loss_making", "high_debt", "rumour_driven", "pledged_shares"),
        ),
        # Classic pump-and-dump trajectory: rapid 6-day pump -> fake rumour exposed -> lower circuits
        guided_events={
            1: 3.0, 2: 8.0, 3: 9.0, 4: 7.0, 5: 10.0, 6: 5.0,
            7: -3.0, 8: -10.0, 9: -10.0, 10: -7.5, 11: -5.0, 12: -6.0,
            13: -2.0, 14: -1.0,
        },
        guided_lower_circuits=(8, 9),
    ),
    Company(
        code="KISANTRC",
        name="Kisan Tractors Ltd",
        color="#84CC16",
        base_price=715.0,
        beta=0.90,
        daily_vol_pct=1.0,
        drift_pct=0.04,
        sector=BilingualText(en="Tractors", hi="ट्रैक्टर"),
        about=BilingualText(
            en="Builds tractors for small farmers. A strong monsoon usually lifts sales.",
            hi="छोटे किसानों के लिए ट्रैक्टर बनाती है। अच्छा मानसून मतलब ज़्यादा बिक्री।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=14900, pe=21.0, sales_3y_cr=(3300, 3150, 3550),
            profit_trend="up", debt_level="low",
        ),
        guided_events={4: 5.0},
    ),
    Company(
        code="DIGIDKN",
        name="Digital Dukaan Tech",
        color="#8B5CF6",
        base_price=428.0,
        beta=1.50,
        daily_vol_pct=1.6,
        drift_pct=0.08,
        sector=BilingualText(en="Technology", hi="टेक्नोलॉजी"),
        about=BilingualText(
            en="Billing and UPI app for kirana stores. Growing fast, though profits are still small.",
            hi="किराना दुकानों के लिए बिलिंग और UPI ऐप। तेज़ी से बढ़ रही है, मुनाफ़ा अभी कम।",
        ),
        fundamentals=Fundamentals(
            mcap_cr=22700, pe=64.0, sales_3y_cr=(880, 1240, 1710),
            profit_trend="up", debt_level="low",
            red_flags=("high_pe",),
        ),
        guided_events={16: 6.0, 19: 5.5},
    ),
)

COMPANY_BY_CODE: dict[str, Company] = {c.code: c for c in COMPANIES}

INDICES: tuple[IndexDef, ...] = (
    IndexDef(id="sim50", name="SIM 50", base_value=18240.0, beta=1.0),
    IndexDef(id="simmid", name="SIM Midcap 100", base_value=32610.0, beta=1.3),
)

# 21-day guided market index daily moves (%)
# Shape: Calm (1-6) -> Wobble (7) -> Crash (8-12) -> Recovery (13-17) -> Normal/Temptation (18-20) -> Graduation (21)
GUIDED_MARKET_RETURNS: tuple[float, ...] = (
    0.6, 0.4, 0.7, 0.3, 0.5, 0.2,     # Days 1-6: Calm bull drift
    -1.2,                              # Day 7: Early caution
    -4.0, -3.1, -2.2, 1.0, -2.4,      # Days 8-12: Market crash (~11% drawdown)
    1.4, 0.9, 1.2, 1.0, 1.3,          # Days 13-17: Gradual recovery
    0.6, 0.8, 0.5,                     # Days 18-20: Normal trading + late FOMO test
    0.4,                               # Day 21: 21-day Habit Graduation close
)

assert len(GUIDED_MARKET_RETURNS) == SEASON_DAYS

GUIDED_NEWS: tuple[NewsItem, ...] = (
    NewsItem(1, BilingualText("Calm start to the 21-day season. SIM 50 edges up.", "21-दिन के सीज़न की शांत शुरुआत। SIM 50 में हल्की बढ़त।")),
    NewsItem(2, BilingualText("Rumour: Rocket Infra may win a huge govt contract. Company has not confirmed.", "अफ़वाह: Rocket Infra को बड़ा सरकारी ठेका मिल सकता है। कंपनी ने पुष्टि नहीं की।"), stock_code="ROCKINFR", severity="rumour"),
    NewsItem(3, BilingualText("Rocket Infra jumps over 20% in three days on heavy social-media buzz.", "सोशल मीडिया चर्चा के बीच Rocket Infra तीन दिन में 20% से ज़्यादा ऊपर।"), stock_code="ROCKINFR", severity="rumour"),
    NewsItem(4, BilingualText("Weather office forecasts a strong monsoon. Kisan Tractors rises 5%.", "मौसम विभाग: इस साल मानसून अच्छा रहेगा। Kisan Tractors 5% चढ़ा।"), stock_code="KISANTRC"),
    NewsItem(5, BilingualText("Rocket Infra hits upper circuit! Up 40%+ in five days.", "Rocket Infra में अपर सर्किट! पाँच दिन में 40% से ज़्यादा ऊपर।"), stock_code="ROCKINFR", severity="rumour"),
    NewsItem(6, BilingualText("Gangotri Foods: sales up 10%, quarterly results match estimates.", "Gangotri Foods: बिक्री 10% बढ़ी, तिमाही नतीजे उम्मीद के मुताबिक़।"), stock_code="GANGOTRI"),
    NewsItem(7, BilingualText("Global markets slip overnight. Domestic investors turn cautious.", "विदेशी बाज़ारों में गिरावट। घरेलू निवेशक सतर्क।"), severity="warning"),
    NewsItem(8, BilingualText("Sharp sell-off worldwide. SIM 50 drops 4% today.", "दुनिया भर के बाज़ार गिरे। SIM 50 आज 4% नीचे।"), severity="crash"),
    NewsItem(8, BilingualText("Rocket Infra: govt contract story was FALSE. Locked in Lower Circuit — zero buyers.", "Rocket Infra: सरकारी ठेके की खबर झूठी निकली। लोअर सर्किट — कोई ख़रीदार नहीं।"), stock_code="ROCKINFR", severity="crash"),
    NewsItem(9, BilingualText("Panic selling continues across markets. Rocket Infra remains locked at Lower Circuit.", "बाज़ार में घबराहट जारी। Rocket Infra आज भी लोअर सर्किट में फँसा है।"), stock_code="ROCKINFR", severity="crash"),
    NewsItem(10, BilingualText("Banking stocks under pressure. Navyug Bank slips 2.5%; Rocket Infra reopens sharply lower.", "बैंक शेयरों पर दबाव। Navyug Bank 2.5% गिरा; Rocket Infra भारी गिरावट के साथ खुला।"), stock_code="NAVYUGBK", severity="warning"),
    NewsItem(11, BilingualText("Brief relief rally: SIM 50 bounces 1%, though volatility stays high.", "थोड़ी राहत: SIM 50 1% चढ़ा, पर उतार-चढ़ाव अभी भी ज़्यादा।")),
    NewsItem(12, BilingualText("SIM 50 is now roughly 11% below its recent peak.", "SIM 50 अपने ऊँचे स्तर से लगभग 11% नीचे।"), severity="warning"),
    NewsItem(13, BilingualText("Global cues stabilise. Patient buying returns to SIM 50.", "विदेशी बाज़ार सँभले। SIM 50 में धैर्यपूर्ण ख़रीदारी लौटी।")),
    NewsItem(14, BilingualText("Vikram Ispat reports trouble repaying a loan instalment. Shares tumble 12%.", "Vikram Ispat: कर्ज़ की किस्त चुकाने में दिक्कत। शेयर 12% गिरा।"), stock_code="VIKISPAT", severity="crash"),
    NewsItem(15, BilingualText("Broad market recovery continues steadily.", "बाज़ार में सुधार लगातार जारी।")),
    NewsItem(16, BilingualText("Digital Dukaan doubles active kirana merchants. Shares jump 6%.", "Digital Dukaan के किराना ग्राहक दोगुने हुए। शेयर 6% चढ़ा।"), stock_code="DIGIDKN"),
    NewsItem(17, BilingualText("Navyug Bank bad loans decline; shares recover 3%.", "Navyug Bank के डूबे कर्ज़ घटे; शेयर 3% ऊपर।"), stock_code="NAVYUGBK"),
    NewsItem(18, BilingualText("Steady trading day. Investors review their portfolios.", "सामान्य कारोबार। निवेशक अपने पोर्टफ़ोलियो की समीक्षा कर रहे हैं।")),
    NewsItem(19, BilingualText("Digital Dukaan rallies again on breakout chatter. Valuation stays high (P/E 64).", "ब्रेकआउट चर्चा पर Digital Dukaan फिर चढ़ा। मूल्यांकन अभी भी ऊँचा (P/E 64)।"), stock_code="DIGIDKN", severity="warning"),
    NewsItem(20, BilingualText("One day left in your 21-day habit season. Markets steady.", "आपके 21-दिन के अभ्यास का आख़िरी दिन क़रीब। बाज़ार शांत।")),
    NewsItem(21, BilingualText("Day 21 complete! Your 21-Day Investor Resilience Report is ready.", "दिन 21 पूरा! आपकी 21-दिन की निवेश लचीलापन रिपोर्ट तैयार है।")),
)
