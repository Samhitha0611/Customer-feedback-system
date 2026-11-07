"""Text cleaning and explainable feedback classification utilities."""
from __future__ import annotations

import re
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _analyzer = SentimentIntensityAnalyzer()
except ImportError:  # Keeps core tests and the app's basic analysis usable before pip install.
    _analyzer = None

_POSITIVE = {
    "good", "great", "excellent", "helpful", "love", "easy", "smooth",
    "reliable", "happy", "fast", "quick", "satisfied", "resolved",
}
_NEGATIVE = {
    "bad", "poor", "late", "broken", "slow", "terrible", "disappointed",
    "frustrating", "expensive", "damaged", "issue", "incorrect", "failed",
}
_NEGATIONS = {"not", "never", "no", "hardly", "isn't", "wasn't", "didn't", "doesn't"}

# Extra phrases improve recall while keeping the taxonomy understandable.
_THEME_TERMS = {
    "Delivery": ("delivery", "shipping", "late", "courier", "arrived", "arrival",
                 "delay", "delayed", "dispatch", "tracking", "package"),
    "Product Quality": ("quality", "broken", "defective", "damaged", "works",
                        "stopped", "durable", "performance", "faulty", "malfunction"),
    "Customer Support": ("support", "agent", "representative", "response", "help",
                         "ticket", "service", "staff", "客服", "contacted"),
    "Pricing": ("price", "cost", "expensive", "charged", "billing", "fee",
                "overpriced", "payment", "subscription", "value"),
    "App Experience": ("app", "website", "login", "interface", "crash", "slow",
                       "navigation", "screen", "loading", "checkout", "platform"),
    "Returns & Refunds": ("return", "refund", "replacement", "exchange", "cancel",
                          "cancellation", "reimburse", "reimbursement"),
}


def clean_text(text: object) -> str:
    """Normalize whitespace and redact common email and phone patterns."""
    value = str(text or "")
    value = re.sub(r"(?i)\b[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b", "[EMAIL_REDACTED]", value)
    value = re.sub(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)", "[PHONE_REDACTED]", value)
    return re.sub(r"\s+", " ", value).strip()


def _sentiment_word_counts(text: str) -> tuple[int, int]:
    tokens = re.findall(r"[a-z']+", text.lower())
    positive = negative = 0
    for index, token in enumerate(tokens):
        negated = any(word in _NEGATIONS for word in tokens[max(0, index - 3):index])
        if token in _POSITIVE:
            if negated:
                negative += 1
            else:
                positive += 1
        elif token in _NEGATIVE:
            if negated:
                positive += 1
            else:
                negative += 1
    return positive, negative


def predict_sentiment(text: str) -> str:
    """Return positive, negative, neutral, or mixed sentiment."""
    value = str(text or "")
    positive, negative = _sentiment_word_counts(value)
    if positive and negative:
        return "mixed"
    if positive:
        return "positive"
    if negative:
        return "negative"
    if _analyzer is not None:
        score = _analyzer.polarity_scores(value)["compound"]
        return "positive" if score >= 0.15 else "negative" if score <= -0.15 else "neutral"
    return "neutral"


def predict_theme(text: str) -> str:
    """Classify a primary theme using whole-word/phrase matching, not substrings."""
    value = str(text or "").lower()
    scores: dict[str, int] = {}
    for theme, terms in _THEME_TERMS.items():
        score = 0
        for term in terms:
            if " " in term:
                score += 2 if term in value else 0
            else:
                matches = len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", value))
                score += matches * (2 if theme == "Returns & Refunds" else 1)
        scores[theme] = score
    best = max(scores, key=scores.get)
    return best if scores[best] else "Other"


def analyze_text(text: object) -> dict[str, str]:
    safe_text = clean_text(text)
    return {
        "clean_text": safe_text,
        "sentiment": predict_sentiment(safe_text),
        "theme": predict_theme(safe_text),
    }


def priority_for(count: int, negative_rate: float) -> str:
    """Transparent baseline priority based on volume multiplied by negative rate."""
    score = max(0, int(count)) * max(0.0, float(negative_rate))
    return "High" if score >= 8 else "Medium" if score >= 3 else "Low"
