"""Streamlit dashboard for customer feedback intelligence."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import DB
from src.analysis import analyze_text

st.set_page_config(
    page_title="Customer Feedback Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_data(database_path: str, modified_time: float) -> dict[str, pd.DataFrame]:
    """Load dashboard tables; modified_time invalidates cache after DB rebuild."""
    del modified_time
    connection = sqlite3.connect(database_path)
    try:
        queries = {
            "analysis": "SELECT * FROM FeedbackAnalysis",
            "actions": "SELECT * FROM ActionItem ORDER BY CASE priority "
                       "WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, source_count DESC",
            "products": "SELECT * FROM Product ORDER BY product_name",
            "quality_issues": "SELECT * FROM DataQualityIssue ORDER BY issue_id",
            "reviews": """SELECT review_id AS source_id, review_text AS text,
                          issue_type, 'Review' AS source_type FROM Review""",
            "responses": """SELECT response_id AS source_id, response_text AS text,
                            issue_type, 'Survey' AS source_type FROM SurveyResponse""",
            "messages": """SELECT message_id AS source_id, message_text AS text,
                           issue_type, 'Support' AS source_type FROM SupportMessage""",
        }
        return {
            name: pd.read_sql_query(query, connection)
            for name, query in queries.items()
        }
    finally:
        connection.close()


def show_setup_help() -> None:
    st.error("The project database could not be loaded.")
    st.markdown("Open a terminal in the project folder and run:")
    st.code(
        "python -m src.generate_data --reviews 2500 --responses 2500 --messages 1000\n"
        "python -m src.build_database",
        language="powershell",
    )
    st.stop()


st.title("Customer Feedback Intelligence")
st.caption(
    "A unified view of customer reviews, survey responses and support messages — "
    "with sentiment, recurring themes and service-priority signals."
)

if not Path(DB).exists():
    show_setup_help()

try:
    data = load_data(str(DB), Path(DB).stat().st_mtime)
except (sqlite3.Error, pd.errors.DatabaseError) as error:
    st.error(f"Unable to read the project database: {error}")
    show_setup_help()

df = data["analysis"].copy()
if df.empty:
    st.warning("The database has no analyzed feedback records. Generate data and rebuild the database.")
    st.stop()

df["feedback_date"] = pd.to_datetime(df["feedback_date"], errors="coerce")
df = df.dropna(subset=["feedback_date"])

# Sidebar filters
st.sidebar.header("Filter feedback")
product_options = ["All products"] + data["products"]["product_name"].dropna().tolist()
selected_product = st.sidebar.selectbox("Product", product_options)
if selected_product != "All products":
    product_id = data["products"].loc[
        data["products"]["product_name"] == selected_product, "product_id"
    ].iloc[0]
    df = df[df["product_id"] == product_id]

source_options = ["All sources"] + sorted(df["source_type"].dropna().unique().tolist())
selected_source = st.sidebar.selectbox("Feedback source", source_options)
if selected_source != "All sources":
    df = df[df["source_type"] == selected_source]

sentiment_options = ["All sentiments"] + sorted(df["predicted_sentiment"].dropna().unique().tolist())
selected_sentiment = st.sidebar.selectbox("Sentiment", sentiment_options)
if selected_sentiment != "All sentiments":
    df = df[df["predicted_sentiment"] == selected_sentiment]

theme_options = ["All themes"] + sorted(df["predicted_theme"].dropna().unique().tolist())
selected_theme = st.sidebar.selectbox("Theme", theme_options)
if selected_theme != "All themes":
    df = df[df["predicted_theme"] == selected_theme]

if df.empty:
    st.info("No records match the selected filters. Change one or more filters.")
    st.stop()

min_date = df["feedback_date"].min().date()
max_date = df["feedback_date"].max().date()
date_value = st.sidebar.date_input(
    "Feedback date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_value, (tuple, list)):
    if len(date_value) == 2:
        start_date, end_date = date_value
        df = df[df["feedback_date"].dt.date.between(start_date, end_date)]
    elif len(date_value) == 1:
        df = df[df["feedback_date"].dt.date == date_value[0]]
else:
    df = df[df["feedback_date"].dt.date == date_value]

if df.empty:
    st.info("No records are available in this date range.")
    st.stop()

# KPI row
total = len(df)
negative_count = int((df["predicted_sentiment"] == "negative").sum())
negative_rate = negative_count / total if total else 0
mixed_count = int((df["predicted_sentiment"] == "mixed").sum())
open_actions = int((data["actions"]["status"] == "Open").sum()) if not data["actions"].empty else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Feedback records", f"{total:,}")
k2.metric("Negative feedback", f"{negative_count:,}", f"{negative_rate:.1%} of filtered records")
k3.metric("Mixed feedback", f"{mixed_count:,}")
k4.metric("Open action items", f"{open_actions:,}")

overview_tab, themes_tab, trends_tab, explore_tab, exceptions_tab = st.tabs(
    ["Overview", "Themes & actions", "Sentiment trends", "Explore & analyze", "Exceptions"]
)

with overview_tab:
    left, right = st.columns(2)
    with left:
        sentiment_counts = (
            df["predicted_sentiment"].value_counts().rename_axis("Sentiment")
            .reset_index(name="Records")
        )
        st.plotly_chart(
            px.pie(sentiment_counts, names="Sentiment", values="Records",
                   hole=0.42, title="Sentiment distribution"),
            use_container_width=True,
        )
    with right:
        source_counts = (
            df["source_type"].value_counts().rename_axis("Source")
            .reset_index(name="Records")
        )
        st.plotly_chart(
            px.bar(source_counts, x="Source", y="Records",
                   title="Feedback records by source", text_auto=True),
            use_container_width=True,
        )
    st.subheader("Latest feedback")
    latest = df.sort_values("feedback_date", ascending=False).head(25)
    st.dataframe(
        latest[["feedback_date", "source_type", "source_id", "cleaned_text",
                "predicted_sentiment", "predicted_theme"]],
        use_container_width=True,
        hide_index=True,
    )

with themes_tab:
    theme_summary = (
        df.groupby("predicted_theme")
        .agg(
            feedback_count=("analysis_id", "count"),
            negative_rate=("predicted_sentiment", lambda values: (values == "negative").mean()),
        )
        .reset_index()
        .sort_values("feedback_count", ascending=False)
    )
    st.plotly_chart(
        px.bar(
            theme_summary, x="predicted_theme", y="feedback_count",
            color="negative_rate", color_continuous_scale="Reds",
            title="Theme volume and negative-feedback rate",
            labels={"predicted_theme": "Theme", "feedback_count": "Feedback records",
                    "negative_rate": "Negative rate"},
        ),
        use_container_width=True,
    )
    st.caption(
        "Priority is a transparent baseline based on feedback volume × negative rate. "
        "It is a triage signal, not an approved SLA or proof of root cause."
    )
    st.subheader("Suggested service action items")
    if data["actions"].empty:
        st.info("No action items were generated for the current database.")
    else:
        st.dataframe(data["actions"], use_container_width=True, hide_index=True)

with trends_tab:
    trend = df.assign(month=df["feedback_date"].dt.to_period("M").astype(str))
    trend = (
        trend.groupby(["month", "predicted_sentiment"])
        .size().reset_index(name="records")
    )
    st.plotly_chart(
        px.line(
            trend, x="month", y="records", color="predicted_sentiment",
            markers=True, title="Feedback volume by month and sentiment",
            labels={"month": "Month", "records": "Feedback records",
                    "predicted_sentiment": "Sentiment"},
        ),
        use_container_width=True,
    )
    monthly_rate = (
        df.assign(month=df["feedback_date"].dt.to_period("M").astype(str))
        .groupby("month")
        .agg(
            total=("analysis_id", "count"),
            negative=("predicted_sentiment", lambda values: (values == "negative").sum()),
        )
        .reset_index()
    )
    monthly_rate["negative_rate"] = monthly_rate["negative"] / monthly_rate["total"]
    st.dataframe(monthly_rate, use_container_width=True, hide_index=True)

with explore_tab:
    st.subheader("Search feedback")
    query = st.text_input("Search words or phrases", placeholder="e.g. delayed delivery")
    results = df
    if query.strip():
        results = results[results["cleaned_text"].str.contains(
            query.strip(), case=False, na=False, regex=False
        )]
    st.caption(f"{len(results):,} matching records")
    st.dataframe(
        results[["source_type", "source_id", "feedback_date", "cleaned_text",
                 "predicted_sentiment", "predicted_theme"]],
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download filtered feedback (CSV)",
        data=results.to_csv(index=False).encode("utf-8"),
        file_name="filtered_customer_feedback.csv",
        mime="text/csv",
    )
    st.divider()
    st.subheader("Analyze a new feedback message")
    new_text = st.text_area(
        "Enter customer feedback",
        placeholder="Example: The delivery was late, but the product quality is excellent.",
        height=110,
    )
    if st.button("Analyze feedback", type="primary", disabled=not new_text.strip()):
        st.json(analyze_text(new_text))

with exceptions_tab:
    quality_issues = data["quality_issues"]
    if not quality_issues.empty:
        st.caption(f"{len(quality_issues):,} labelled data-quality issues retained for review.")
        st.dataframe(quality_issues, use_container_width=True, hide_index=True)
    else:
        st.info("No labelled data-quality issues were found in the generated data.")
    st.info(
        "Ground-truth labels are kept separate from model inputs. "
        "Duplicate source rows are rejected from transactional tables but retained here "
        "as quality issues. Run `python -m src.evaluate` to calculate labelled-data metrics."
    )

st.sidebar.divider()
st.sidebar.caption("Local project dashboard • SQLite • Streamlit")
