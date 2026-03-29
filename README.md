# Truth Tracker News App

Truth Tracker is a Flask news app that scores articles, tracks sentiment and emotion, and summarizes the overall "world mood" across categories and sources. It turns article-level analysis into a browsable dashboard with source icons, category views, and emotion-based summaries.

This project mixes news aggregation, sentiment analysis, and lightweight visualization in a single web app.

## Tech

- Python
- Flask
- JSON data pipelines
- SQLite / ChromaDB assets

## Main Files

- `app.py` serves the main web app.
- `analysis.py` and `calculate.py` handle article scoring and mood calculations.
- `news_articles_scored.json` stores processed article data for the UI.
- `templates/` and `static/` contain the frontend.

