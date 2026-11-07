"""Build the SQLite database from the generated CSV files."""
from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone

from .config import GENERATED, DB, DATA
from .analysis import analyze_text, priority_for

SCHEMA = """
CREATE TABLE IF NOT EXISTS Customer(
    customer_id TEXT PRIMARY KEY, customer_name TEXT NOT NULL, region TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS Product(
    product_id TEXT PRIMARY KEY, product_name TEXT NOT NULL, category TEXT
);
CREATE TABLE IF NOT EXISTS Channel(
    channel_id TEXT PRIMARY KEY, channel_name TEXT NOT NULL, channel_type TEXT
);
CREATE TABLE IF NOT EXISTS Survey(
    survey_id TEXT PRIMARY KEY, survey_name TEXT, product_id TEXT NOT NULL,
    channel_id TEXT NOT NULL, start_date TEXT, end_date TEXT, status TEXT,
    FOREIGN KEY(product_id) REFERENCES Product(product_id),
    FOREIGN KEY(channel_id) REFERENCES Channel(channel_id)
);
CREATE TABLE IF NOT EXISTS Theme(
    theme_id TEXT PRIMARY KEY, theme_name TEXT UNIQUE, description TEXT
);
CREATE TABLE IF NOT EXISTS SentimentLabel(
    sentiment_id TEXT PRIMARY KEY, label TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS SurveyResponse(
    response_id TEXT PRIMARY KEY, survey_id TEXT NOT NULL, customer_id TEXT NOT NULL,
    product_id TEXT NOT NULL, response_date TEXT, response_text TEXT, issue_type TEXT,
    FOREIGN KEY(survey_id) REFERENCES Survey(survey_id),
    FOREIGN KEY(customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY(product_id) REFERENCES Product(product_id)
);
CREATE TABLE IF NOT EXISTS Review(
    review_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, product_id TEXT NOT NULL,
    channel_id TEXT NOT NULL, review_date TEXT,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5), review_text TEXT,
    source_language TEXT, issue_type TEXT,
    FOREIGN KEY(customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY(product_id) REFERENCES Product(product_id),
    FOREIGN KEY(channel_id) REFERENCES Channel(channel_id)
);
CREATE TABLE IF NOT EXISTS SupportMessage(
    message_id TEXT PRIMARY KEY, ticket_id TEXT, customer_id TEXT NOT NULL,
    product_id TEXT NOT NULL, channel_id TEXT NOT NULL, message_date TEXT,
    message_text TEXT, ticket_status TEXT, issue_type TEXT,
    FOREIGN KEY(customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY(product_id) REFERENCES Product(product_id),
    FOREIGN KEY(channel_id) REFERENCES Channel(channel_id)
);
CREATE TABLE IF NOT EXISTS FeedbackAnalysis(
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT, source_type TEXT NOT NULL,
    source_id TEXT NOT NULL, feedback_date TEXT, product_id TEXT, channel_id TEXT,
    cleaned_text TEXT, predicted_sentiment TEXT, predicted_theme TEXT,
    UNIQUE(source_type, source_id)
);
CREATE TABLE IF NOT EXISTS ActionItem(
    action_id TEXT PRIMARY KEY, theme_name TEXT, priority TEXT, description TEXT,
    source_count INTEGER, negative_rate REAL, status TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS StateEvent(
    event_id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT, entity_id TEXT,
    old_state TEXT, new_state TEXT, event_time TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS DataQualityIssue(
    issue_id TEXT PRIMARY KEY, source_type TEXT NOT NULL, source_id TEXT NOT NULL,
    issue_type TEXT NOT NULL, details TEXT, expected_handling TEXT
);
"""

CSV_TABLES = [
    ("Customer", "customers"),
    ("Product", "products"),
    ("Channel", "channels"),
    ("Survey", "surveys"),
    ("Theme", "themes"),
    ("SentimentLabel", "sentiment_labels"),
    ("SurveyResponse", "survey_responses"),
    ("Review", "reviews"),
    ("SupportMessage", "support_messages"),
]

DELETE_ORDER = [
    "FeedbackAnalysis", "ActionItem", "StateEvent", "DataQualityIssue",
    "SurveyResponse", "Review",
    "SupportMessage", "Survey", "Theme", "SentimentLabel", "Customer",
    "Product", "Channel",
]


def read_csv(name: str) -> list[dict[str, str]]:
    path = GENERATED / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Required input file is missing: {path}. "
            "Run `python -m src.generate_data` before building the database."
        )
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load(conn: sqlite3.Connection, table: str, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    sql = (
        f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) "
        f"VALUES ({','.join('?' for _ in columns)})"
    )
    conn.executemany(sql, [[row.get(column) for column in columns] for row in rows])


def build() -> int:
    """Rebuild all project tables atomically; return analyzed record count."""
    DATA.mkdir(parents=True, exist_ok=True)

    # Read and validate all inputs before touching the existing database.
    source_rows = {table: read_csv(filename) for table, filename in CSV_TABLES}
    conn = sqlite3.connect(DB)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")

        for table in DELETE_ORDER:
            conn.execute(f"DELETE FROM {table}")

        for table, _filename in CSV_TABLES:
            load(conn, table, source_rows[table])

        feedback_sources = []
        feedback_sources.extend(
            ("review", *row)
            for row in conn.execute(
                "SELECT review_id, review_date, product_id, channel_id, review_text FROM Review"
            )
        )
        feedback_sources.extend(
            ("survey_response", *row)
            for row in conn.execute(
                "SELECT response_id, response_date, product_id, NULL, response_text "
                "FROM SurveyResponse"
            )
        )
        feedback_sources.extend(
            ("support_message", *row)
            for row in conn.execute(
                "SELECT message_id, message_date, product_id, channel_id, message_text "
                "FROM SupportMessage"
            )
        )

        analysis_rows = []
        for source_type, source_id, date, product_id, channel_id, raw_text in feedback_sources:
            result = analyze_text(raw_text)
            analysis_rows.append((
                source_type, source_id, date, product_id, channel_id,
                result["clean_text"], result["sentiment"], result["theme"],
            ))

        conn.executemany(
            """INSERT INTO FeedbackAnalysis
            (source_type, source_id, feedback_date, product_id, channel_id,
             cleaned_text, predicted_sentiment, predicted_theme)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            analysis_rows,
        )

        # Preserve labelled data-quality anomalies separately. This is important
        # for duplicate source IDs, which are intentionally rejected by INSERT OR IGNORE.
        ground_truth_path = GENERATED / "ground_truth.json"
        if ground_truth_path.exists():
            import json

            anomalies = json.loads(ground_truth_path.read_text(encoding="utf-8")).get("anomalies", [])
            anomaly_rows = []
            for index, anomaly in enumerate(anomalies, start=1):
                anomaly_rows.append((
                    f"DQI-{index:06d}",
                    anomaly.get("record_type", "unknown"),
                    anomaly.get("record_id", "unknown"),
                    anomaly.get("issue_type", "unspecified"),
                    anomaly.get("details", "Labelled data-quality anomaly in generated source data."),
                    anomaly.get("expected_handling", "Review manually"),
                ))
            conn.executemany(
                """INSERT INTO DataQualityIssue
                (issue_id, source_type, source_id, issue_type, details, expected_handling)
                VALUES (?, ?, ?, ?, ?, ?)""",
                anomaly_rows,
            )

        aggregate_rows = conn.execute(
            """SELECT predicted_theme, COUNT(*),
                      AVG(CASE WHEN predicted_sentiment = 'negative' THEN 1.0 ELSE 0.0 END)
               FROM FeedbackAnalysis
               GROUP BY predicted_theme
               ORDER BY predicted_theme"""
        ).fetchall()

        created_at = datetime.now(timezone.utc).isoformat()
        for index, (theme, count, negative_rate) in enumerate(aggregate_rows, start=1):
            if theme != "Other" and count >= 3 and negative_rate >= 0.15:
                conn.execute(
                    """INSERT INTO ActionItem
                    (action_id, theme_name, priority, description, source_count,
                     negative_rate, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"ACT-{index:06d}", theme, priority_for(count, negative_rate),
                        f"Investigate recurring {theme.lower()} feedback and validate root causes.",
                        count, round(negative_rate, 4), "Open", created_at,
                    ),
                )

        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise sqlite3.IntegrityError(f"Foreign-key validation failed: {fk_errors[:5]}")
        conn.commit()
        print(f"Database rebuilt: {DB}")
        print(f"Analyzed {len(analysis_rows):,} feedback records.")
        print("Foreign-key validation: passed")
        return len(analysis_rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    build()
