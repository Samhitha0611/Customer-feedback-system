import sqlite3

from src.analysis import (
    analyze_text,
    clean_text,
    predict_sentiment,
    predict_theme,
    priority_for,
)


def test_email_redaction():
    assert "private@example.com" not in clean_text("private@example.com")
    assert "[EMAIL_REDACTED]" in clean_text("private@example.com")


def test_phone_redaction():
    assert "9876543210" not in clean_text("Call me at 9876543210")


def test_positive():
    assert predict_sentiment("Excellent product and helpful support") == "positive"


def test_negative():
    assert predict_sentiment("Delivery was late and service was poor") == "negative"


def test_mixed_sentiment():
    assert predict_sentiment("The product is great, but delivery was late") == "mixed"


def test_negation_is_respected():
    assert predict_sentiment("The support agent was not helpful") == "negative"


def test_theme_delivery():
    assert predict_theme("My shipping was late") == "Delivery"


def test_theme_does_not_match_inside_happy():
    # The word "happy" must not accidentally trigger the substring "app".
    assert predict_theme("I am happy with the product") == "Other"


def test_theme_refund():
    assert predict_theme("My refund has not arrived") == "Returns & Refunds"


def test_theme_unknown():
    assert predict_theme("The colour is exactly as shown") == "Other"


def test_analyze_text_redacts_before_returning():
    result = analyze_text("Great service. Contact private@example.com")
    assert "private@example.com" not in result["clean_text"]
    assert result["sentiment"] == "positive"


def test_priority():
    assert priority_for(20, 0.6) == "High"
    assert priority_for(5, 0.6) == "Medium"
    assert priority_for(1, 0.1) == "Low"
