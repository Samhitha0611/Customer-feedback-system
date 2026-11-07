# Data dictionary
| Entity | Primary key | Main fields / rules |
|---|---|---|
| Customer | customer_id | name, region, created_at |
| Product | product_id | product_name, category |
| Channel | channel_id | channel_name, channel_type |
| Survey | survey_id | name, product_id FK, channel_id FK, start/end dates, status |
| SurveyResponse | response_id | survey_id/customer_id/product_id FKs, date, text, issue_type |
| Review | review_id | customer_id/product_id/channel_id FKs, date, rating 1–5, text, language, issue_type |
| SupportMessage | message_id | ticket_id, customer/product/channel FKs, date, text, ticket status |
| Theme | theme_id | unique theme_name, description |
| SentimentLabel | sentiment_id | unique positive/negative/neutral/mixed label |
| FeedbackAnalysis | analysis_id | source_type/source_id, date, product, cleaned text, predicted sentiment/theme |
| ActionItem | action_id | theme, priority, description, source_count, negative_rate, status, created_at |
| StateEvent | event_id | entity, old/new state, event time, note |
| DataQualityIssue | issue_id | source type/id, issue type, details, expected handling; stores labelled anomalies independently of model predictions |

IDs follow `SUR-2026-000001`, `RESP-<survey-id>-000001`, `REV-2026-000001`, `MSG-<ticket-id>-001`, `THEME-000001`. IDs are immutable strings and references must match exactly.
