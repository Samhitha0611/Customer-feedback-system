# Customer Feedback Intelligence & Service Priority System

A local Streamlit application that combines customer reviews, survey responses and support messages to identify sentiment, recurring feedback themes, trends and service-priority signals.

## Ready-to-run project

This package includes the generated datasets and a populated SQLite database with **70,000 analyzed feedback records**. You do not need to regenerate the data to open the dashboard.

### Option 1 — Windows one-click launch

1. Install Python 3.11 or newer and make sure the Python launcher (`py`) is available.
2. Double-click `run_project.bat`.
3. On its first run, the script creates `.venv`, installs the requirements and starts Streamlit.
4. Open the local URL printed in the terminal (normally `http://localhost:8501`).

### Option 2 — Run manually (PowerShell)

Open a terminal in the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

The included database is used automatically.

## Rebuild the database

The project includes its generated CSV files and `data/customer_feedback.db`. If you edit the CSV data and want to rebuild the database, run:

```powershell
python -m src.build_database
```

The build script checks that all required CSV files exist before it changes the current database. It recreates the database tables, analyzes the feedback, stores labelled data-quality anomalies separately and checks foreign-key integrity.

## Regenerate the data

To create the full brief-volume dataset from scratch:

```powershell
python -m src.generate_data --reviews 25000 --responses 25000 --messages 20000 --seed 20261022
python -m src.build_database
```

This creates 25,000 reviews, 25,000 survey responses and 20,000 support messages. The generator uses synthetic data and a fixed seed for reproducibility.

For a quicker development dataset:

```powershell
python -m src.generate_data --reviews 2500 --responses 2500 --messages 1000
python -m src.build_database
```

## Validation and evaluation

Run each command from the project root:

```powershell
pytest -q
python -m src.validate_data
python -m src.evaluate
```

- `pytest -q` runs the unit tests.
- `src.validate_data` checks primary-key uniqueness, foreign keys, rating ranges, source-to-analysis coverage, PII redaction and data-quality issue retention. The result is written to `outputs/validation_summary.json`.
- `src.evaluate` compares model predictions with the separate generated `ground_truth.json`. The result is written to `outputs/evaluation_summary.json`.

## Dashboard features

- Overview KPIs and sentiment distribution.
- Feedback source and product filters.
- Date, sentiment and theme filters.
- Theme volume and negative-feedback rate.
- Monthly sentiment trends.
- Searchable feedback records and CSV export.
- Analyze-a-new-message tool.
- Data-quality exception register, including the duplicate response record.

## Project structure

```text
customer_feedback_intelligence/
├── app.py
├── run_project.bat
├── requirements.txt
├── README.md
├── check_db.py
├── src/
│   ├── config.py
│   ├── analysis.py
│   ├── generate_data.py
│   ├── build_database.py
│   ├── validate_data.py
│   └── evaluate.py
├── data/
│   ├── customer_feedback.db
│   └── generated/
├── outputs/
├── docs/
└── tests/
```

## Important assumptions and limitations

- The included records are synthetic; they are not evidence of actual customer behavior.
- Sentiment and theme classification are explainable baselines, not a fine-tuned production model.
- Each feedback record receives one primary theme; real feedback may contain multiple themes.
- Keyword/rule-based classification can miss sarcasm, context, spelling variations and multilingual nuance.
- The priority score is a transparent triage heuristic (feedback count × negative rate), not an approved service-level agreement.
- Data-quality labels are stored separately from model inputs. A duplicate source row is rejected from its transactional table but retained in `DataQualityIssue`.
- PII redaction uses simple email and phone patterns; it is not a complete privacy detector.
- Human review is required before acting on predictions or suggested priorities.

## Submission checklist

- Review the source code and make sure you can explain each module.
- Run the tests, validation and evaluation commands and retain the resulting reports.
- Review `docs/AI_USAGE_AND_PROMPT_LOG.md` and add any additional exact prompts required by your program. Do not invent prompt history.
- Keep `.env`, credentials, virtual environments and unrelated personal files out of the public repository.
- Use a dedicated repository and follow the fellowship/program's submission rules.
