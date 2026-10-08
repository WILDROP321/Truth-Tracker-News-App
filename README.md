# Truth Tracker

**Explore the emotional tone of the news across sources and topics.**

Truth Tracker combines RSS aggregation, transformer-based sentiment and emotion analysis, and a Flask dashboard. It turns individual article scores into source-level comparisons, category summaries, and an aggregate World Mood Score.

## What it does

- Collects headlines and summaries from RSS feeds across global news, business, technology, sports, and other categories.
- Cleans feed content and extracts article imagery.
- Applies sentiment and emotion models to headlines and summaries.
- Aggregates results into mood scores and emotion distributions.
- Presents the results through a web dashboard.

## How it works

RSS feeds → cleaned articles → sentiment and emotion models → mood aggregation → Flask dashboard

| File | Responsibility |
| --- | --- |
| `main.py` | Fetch and normalize RSS articles |
| `analysis.py` | Score articles with Hugging Face Transformers |
| `calculate.py` | Calculate mood scores and emotion distributions |
| `app.py` | Serve the dashboard |
| `templates/` and `static/` | Interface, styles, and visual assets |

**Stack:** Python, Flask, Hugging Face Transformers, pandas, feedparser, Beautiful Soup, HTML, CSS, and JavaScript.

## Explore locally

From the repository root, create a Python virtual environment and install the dashboard dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install flask pandas
flask --app app run
```

The dashboard uses the included `news_articles_scored.json` and `news_icons.json` files. Open the local address printed by Flask.

To regenerate the article data, install the additional pipeline dependencies and run:

```bash
pip install feedparser beautifulsoup4 transformers torch
python main.py
python analysis.py
```

Model downloads and RSS ingestion require an internet connection. Individual feeds may change or become unavailable.

## Interpreting the results

The World Mood Score summarizes the model-estimated tone of the collected articles. It is an exploratory measure of news coverage, not a factual-accuracy rating or a measurement of public opinion. Results depend on the selected feeds, article sample, and model behavior.

Built by [Arya Prabhu](https://github.com/WILDROP321).
