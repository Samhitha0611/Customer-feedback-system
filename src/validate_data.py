"""Validate referential integrity, uniqueness, and analysis coverage."""
from __future__ import annotations

import json
import sqlite3

from .config import DB, OUTPUT, GENERATED

KEY_TABLES = [
    ("Customer", "customer_id"),
    ("Product", "product_id"),
    ("Channel", "channel_id"),
    ("Survey", "survey_id"),
    ("SurveyResponse", "response_id"),
    ("Review", "review_id"),
    ("SupportMessage", "message_id"),
    ("Theme", "theme_id"),
]


def validate() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}. Run `python -m src.build_database`.")

    result = {}
    conn = sqlite3.connect(DB)
    try:
        result["foreign_key_violations"] = len(
            conn.execute("PRAGMA foreign_key_check").fetchall()
        )
        duplicate_counts = []
        for table, key in KEY_TABLES:
            result[f"{table.lower()}_rows"] = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            duplicates = conn.execute(
                f"""SELECT COUNT(*) FROM (
                    SELECT {key} FROM {table}
                    GROUP BY {key} HAVING COUNT(*) > 1
                )"""
            ).fetchone()[0]
            result[f"{table.lower()}_duplicate_keys"] = duplicates
            duplicate_counts.append(duplicates)

        result["invalid_ratings"] = conn.execute(
            "SELECT COUNT(*) FROM Review WHERE rating NOT BETWEEN 1 AND 5"
        ).fetchone()[0]
        result["analysis_rows"] = conn.execute(
            "SELECT COUNT(*) FROM FeedbackAnalysis"
        ).fetchone()[0]
        result["unmatched_analysis_sources"] = sum([
            conn.execute(
                """SELECT COUNT(*) FROM Review r
                   WHERE NOT EXISTS (
                       SELECT 1 FROM FeedbackAnalysis a
                       WHERE a.source_type='review' AND a.source_id=r.review_id
                   )"""
            ).fetchone()[0],
            conn.execute(
                """SELECT COUNT(*) FROM SurveyResponse r
                   WHERE NOT EXISTS (
                       SELECT 1 FROM FeedbackAnalysis a
                       WHERE a.source_type='survey_response' AND a.source_id=r.response_id
                   )"""
            ).fetchone()[0],
            conn.execute(
                """SELECT COUNT(*) FROM SupportMessage m
                   WHERE NOT EXISTS (
                       SELECT 1 FROM FeedbackAnalysis a
                       WHERE a.source_type='support_message' AND a.source_id=m.message_id
                   )"""
            ).fetchone()[0],
        ])
        result["action_items"] = conn.execute(
            "SELECT COUNT(*) FROM ActionItem"
        ).fetchone()[0]
        result["data_quality_issues"] = conn.execute(
            "SELECT COUNT(*) FROM DataQualityIssue"
        ).fetchone()[0]
        result["unredacted_email_count"] = conn.execute(
            """SELECT COUNT(*) FROM FeedbackAnalysis
               WHERE cleaned_text LIKE '%@%.%'"""
        ).fetchone()[0]
    finally:
        conn.close()

    ground_truth_path = GENERATED / "ground_truth.json"
    result["labelled_anomalies"] = (
        len(json.loads(ground_truth_path.read_text(encoding="utf-8"))["anomalies"])
        if ground_truth_path.exists() else None
    )
    result["passed"] = all([
        result["foreign_key_violations"] == 0,
        not any(duplicate_counts),
        result["invalid_ratings"] == 0,
        result["unmatched_analysis_sources"] == 0,
        result["unredacted_email_count"] == 0,
        result["data_quality_issues"] == result["labelled_anomalies"],
    ])

    (OUTPUT / "validation_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    validate()
