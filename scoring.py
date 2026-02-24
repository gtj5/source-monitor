"""
scoring.py

Keyword-based newsworthiness scorer for pipeline items.
Built for general journalism — works across any topic or beat.

Scale:
  5 — Break / publish immediately or investigate urgently
      (public safety, major crimes, disasters, major scandals)
  4 — High public interest
      (significant legal action, corporate misconduct, major policy impact)
  3 — Moderate interest
      (regulation, tech developments, notable business/political activity)
  2 — Lower interest
      (personnel changes, scheduled events, routine reports)
  1 — Routine / administrative
"""

# ── Tier 5: Urgent, break-worthy ─────────────────────────────────────────────
# Public safety, major crimes, disasters, systemic failures
_TIER5 = [
    # Crimes & legal
    "arrest", "arrested", "indicted", "indictment", "charged", "charges",
    "convicted", "conviction", "prison", "jail", "criminal",
    "fraud", "wire fraud", "money laundering", "bribery", "corruption",
    "insider trading", "market manipulation", "ponzi", "pump and dump",
    "whistleblower exposes", "leaked", "cover-up",

    # Public safety & disasters
    "dead", "deaths", "killed", "casualties", "fatalities", "mass shooting",
    "explosion", "collapse", "disaster", "emergency", "outbreak",
    "recall", "safety alert", "health warning", "contamination",
    "hack", "breach", "cyberattack", "data breach", "ransomware",

    # Systemic/government
    "scandal", "corruption", "impeach", "resign under", "fired",
    "cover up", "cover-up", "suppressed", "concealed",
]

# ── Tier 4: High public interest ─────────────────────────────────────────────
# Legal actions, corporate misconduct, significant accountability
_TIER4 = [
    # Legal & regulatory action
    "lawsuit", "sued", "sues", "litigation", "enforcement",
    "penalty", "penalties", "fine", "fined", "settlement", "settled",
    "investigation", "probe", "subpoena", "injunction", "ban", "banned",
    "sanction", "sanctions", "violation", "misconduct", "misconduct",
    "disgorgement", "restitution", "damages",

    # Accountability & impact
    "layoffs", "job cuts", "bankruptcy", "bankrupt", "collapse",
    "data exposed", "privacy violation", "surveillance", "spying",
    "monopoly", "antitrust", "price fixing", "exploitation",
    "whistleblower", "leak", "internal documents", "exclusive",
    "misleading", "false claims", "misinformation",
]

# ── Tier 3: Moderate interest ─────────────────────────────────────────────────
# Policy changes, technology, notable business/political developments
_TIER3 = [
    # Policy & regulation
    "regulation", "law", "legislation", "bill", "act", "policy",
    "proposed rule", "final rule", "rulemaking", "amendment",
    "guidance", "executive order", "mandate",

    # Technology & privacy
    "ai", "artificial intelligence", "algorithm", "surveillance tech",
    "crypto", "bitcoin", "blockchain", "digital asset", "stablecoin",
    "social media", "platform", "censorship", "content moderation",

    # Business & economy
    "merger", "acquisition", "ipo", "deal", "contract", "partnership",
    "interest rate", "inflation", "recession", "market crash",
    "earnings miss", "profit warning", "debt",

    # Government & politics
    "election", "vote", "ballot", "congress", "senate", "white house",
    "supreme court", "ruling", "hearing", "testimony",
]

# ── Tier 2: Lower interest ────────────────────────────────────────────────────
# Personnel, scheduled events, industry updates
_TIER2 = [
    "appoint", "appointed", "appointment", "names", "named",
    "hire", "hired", "promoted", "promotion", "resign", "retirement",
    "committee", "meeting", "forum", "conference", "summit", "event",
    "budget", "annual report", "quarterly", "statistics", "data release",
    "publishes", "releases report", "study finds", "survey",
    "partnership announced", "expansion", "new office",
]


def score_newsworthiness(item: dict) -> int:
    """Return a 1–5 newsworthiness score based on title + summary keywords."""
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    if any(kw in text for kw in _TIER5):
        return 5
    if any(kw in text for kw in _TIER4):
        return 4
    if any(kw in text for kw in _TIER3):
        return 3
    if any(kw in text for kw in _TIER2):
        return 2
    return 1
