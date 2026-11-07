# Architecture and workflow
1. Generate master data: Customer, Product, Channel, Survey, Theme, SentimentLabel.
2. Generate dependent SurveyResponse, Review and SupportMessage rows with valid parent IDs.
3. Redact obvious email/phone patterns; analyze text for sentiment and theme.
4. Persist source and analysis records in SQLite; keep source IDs for traceability.
5. Aggregate theme volume, negative rate and monthly sentiment trends.
6. Generate action items for recurring themes with meaningful negative rates.
7. Preserve labelled data-quality anomalies in `DataQualityIssue`, including duplicate IDs rejected from transactional tables.
8. Validate keys, foreign keys, rating ranges, PII redaction and analysis coverage.
9. Evaluate predictions against separate `ground_truth.json`; never load it as model input.
10. Display metrics, trends, source records, actions and quality issues in Streamlit.

## Relationships
Customer 1:N SurveyResponse, Review, SupportMessage. Product 1:N Survey, SurveyResponse, Review, SupportMessage, FeedbackAnalysis. Channel 1:N Survey, Review, SupportMessage. Survey 1:N SurveyResponse. Theme is a controlled taxonomy; this baseline assigns one primary theme per analysis. A future multi-label design should add a ThemeAssignment bridge table.

## Exception paths
Duplicate response IDs are rejected by primary-key uniqueness and retained in `DataQualityIssue` for review. Potential email/phone strings are redacted in the analysis copy. Unmapped text becomes `Other`. Ground-truth anomaly labels are stored separately from prediction inputs.
