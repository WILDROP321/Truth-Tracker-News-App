import json
import os
from pathlib import Path

from transformers import pipeline

# We reuse the same per-article mood logic that the Flask app uses for aggregation,
# so per-article labels and the global dashboards stay consistent.
try:
    from calculate import article_mood_score, weighted_mean_valence, emotion_confidence, EMOTION_VALENCE  # type: ignore
except Exception:
    article_mood_score = None  # fallback if calculate.py isn't present
    weighted_mean_valence = None
    emotion_confidence = None
    EMOTION_VALENCE = {
        "admiration": 0.8, "amusement": 0.7, "approval": 0.6, "caring": 0.9, "curiosity": 0.3,
        "desire": 0.5, "excitement": 1.0, "gratitude": 0.9, "joy": 1.0, "love": 1.0,
        "pride": 0.8, "relief": 0.7, "neutral": 0.0, "realization": 0.2, "confusion": -0.3,
        "nervousness": -0.6, "disappointment": -0.7, "disapproval": -0.8, "embarrassment": -0.6,
        "fear": -0.9, "grief": -1.0, "remorse": -0.8, "sadness": -0.8, "anger": -1.0,
        "annoyance": -0.7, "disgust": -0.9, "surprise": 0.3,
    }

# ---------- Config ----------
# Use env vars to override without changing code.
SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")
EMOTION_MODEL = os.getenv("EMOTION_MODEL", "joeddav/distilbert-base-uncased-go-emotions-student")

DATA_PATH = Path("news_articles.json")
OUTPUT_PATH = Path("news_articles_scored.json")

TOP_EMOTIONS_K = int(os.getenv("TOP_EMOTIONS_K", "5"))

# Load pipelines
sentiment_pipeline = pipeline("sentiment-analysis", model=SENTIMENT_MODEL)
emotion_pipeline = pipeline("text-classification", model=EMOTION_MODEL, return_all_scores=True)


def _to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def analyze_article(headline, summary):
    text = f"{headline}. {summary}" if summary else headline
    truncated_text = text[:512]

    # --- Sentiment ---
    sent = sentiment_pipeline(truncated_text)[0]
    sent_label = str(sent.get("label", "neutral")).lower()
    sent_conf = _to_float(sent.get("score", 0.0), 0.0)

    # Map sentiment label/conf to -100..100
    # Supports 2-class and 3-class sentiment models.
    if "positive" in sent_label:
        sentiment_score = (sent_conf * 2 - 1) * 100  # 0..1 => -100..100
        sentiment_label = "positive"
    elif "negative" in sent_label:
        sentiment_score = -((sent_conf * 2 - 1) * 100)
        sentiment_label = "negative"
    else:
        sentiment_score = 0.0
        sentiment_label = "neutral"

    # --- Emotions (Top K) ---
    emotions_raw = emotion_pipeline(truncated_text)[0]
    emotions_sorted = sorted(emotions_raw, key=lambda x: x.get("score", 0.0), reverse=True)
    top_k = emotions_sorted[:max(1, TOP_EMOTIONS_K)]

    top_emotions = [
        {"label": str(e.get("label", "neutral")).lower(), "score": round(_to_float(e.get("score", 0.0)), 6)}
        for e in top_k
    ]

    # Compute emotion valence and confidence for interpretability
    if weighted_mean_valence:
        emo_val = weighted_mean_valence(top_emotions)
    else:
        # Simple fallback: score-weighted valence average
        num = 0.0
        den = 0.0
        for e in top_emotions:
            v = _to_float(e.get("score", 0.0))
            val = _to_float(EMOTION_VALENCE.get(e["label"], 0.0))
            num += val * v
            den += v
        emo_val = (num / den) if den else 0.0

    if emotion_confidence:
        emo_conf = emotion_confidence(top_emotions)
    else:
        emo_conf = min(1.0, sum(_to_float(e.get("score", 0.0)) for e in top_emotions))

    # --- Mood score (0..100) ---
    article_payload = {
        "sentiment_score": round(sentiment_score, 2),  # -100..100
        "top_emotions": top_emotions,
    }
    if article_mood_score:
        mood_0_100 = article_mood_score(article_payload)
    else:
        # Fallback blend: sentiment (0..100) + emotion (0..100) with confidence weight
        sent_0_100 = (sentiment_score + 100.0) / 2.0
        emo_0_100 = ((emo_val + 1.0) / 2.0) * 100.0
        w = min(0.45, 0.15 + 0.30 * emo_conf)
        mood_0_100 = (1.0 - w) * sent_0_100 + w * emo_0_100

    # Helpful labels
    top_emotion_label = top_emotions[0]["label"] if top_emotions else "neutral"
    mood_label = "positive" if mood_0_100 >= 60 else ("negative" if mood_0_100 <= 40 else "mixed")

    return {
        "sentiment_label": sentiment_label,
        "sentiment_model_conf": round(sent_conf, 6),
        "sentiment_score": round(sentiment_score, 2),  # -100..100
        "top_emotions": top_emotions,  # list of {label, score} in 0..1
        "top_emotion": top_emotion_label,
        "emotion_valence": round(float(emo_val), 6),   # -1..1
        "emotion_confidence": round(float(emo_conf), 6),  # 0..1
        "mood_score_0_100": round(float(mood_0_100), 2),  # 0..100
        "mood_label": mood_label,
    }


if __name__ == "__main__":
    if not DATA_PATH.exists():
        raise SystemExit(f"❌ Missing input file: {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        articles = json.load(f)

    for i, art in enumerate(articles):
        result = analyze_article(art.get("title", ""), art.get("summary", ""))
        art.update(result)
        print(
            f"[OK] {i+1}/{len(articles)} "
            f"→ mood {result['mood_score_0_100']}/100 ({result['mood_label']}), "
            f"sent {result['sentiment_label']} ({result['sentiment_score']}), "
            f"top emo {result['top_emotion']}"
        )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved enriched articles to {OUTPUT_PATH}")