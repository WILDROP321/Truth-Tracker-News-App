import json
from collections import defaultdict
import pandas as pd
import os

# -----------------------------
# Tunables
# -----------------------------
# Extra weight applied ONLY to negative-valence emotions when computing per-article emotion effect.
NEG_EMOTION_EXTRA = 0.5

# Emotion valence: +1 positive, -1 negative, 0 neutral (can be fractional)
EMOTION_VALENCE = {
    "admiration": 0.8,
    "amusement": 0.7,
    "approval": 0.6,
    "caring": 0.9,
    "curiosity": 0.3,
    "desire": 0.5,
    "excitement": 1.0,
    "gratitude": 0.9,
    "joy": 1.0,
    "love": 1.0,
    "pride": 0.8,
    "relief": 0.7,
    "neutral": 0.0,
    "realization": 0.2,
    "confusion": -0.3,
    "nervousness": -0.6,
    "disappointment": -0.7,
    "disapproval": -0.8,
    "embarrassment": -0.6,
    "fear": -0.9,
    "grief": -1.0,
    "remorse": -0.8,
    "sadness": -0.8,
    "anger": -1.0,
    "annoyance": -0.7,
    "disgust": -0.9,
    # Surprise is ambiguous; keep mildly positive by default.
    "surprise": 0.3,
}

# -----------------------------
# Helpers
# -----------------------------
def _to_0_1(score) -> float:
    """Normalize a score that may be 0..1 or 0..100 into 0..1."""
    if score is None:
        return 0.0
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.0
    if s > 1.0:
        s = s / 100.0
    # clamp
    if s < 0.0:
        return 0.0
    if s > 1.0:
        return 1.0
    return s


def weighted_mean_valence(top_emotions, neg_extra: float = NEG_EMOTION_EXTRA) -> float:
    """
    Compute a score-weighted mean valence in [-1, 1].

    numerator = Σ (valence * score * weight)
    denom     = Σ (score * weight)

    where weight = abs(valence) + (neg_extra if valence < 0 else 0)
    """
    if not top_emotions:
        return 0.0

    numerator = 0.0
    denom = 0.0

    for emo in top_emotions:
        label = str(emo.get("label", "neutral")).lower().strip()
        valence = float(EMOTION_VALENCE.get(label, 0.0))
        score = _to_0_1(emo.get("score", 0.0))

        extra = neg_extra if valence < 0 else 0.0
        weight = abs(valence) + extra

        numerator += valence * score * weight
        denom += score * weight

    if denom <= 0.0:
        return 0.0

    effect = numerator / denom
    if effect < -1.0:
        return -1.0
    if effect > 1.0:
        return 1.0
    return effect


def emotion_confidence(top_emotions) -> float:
    """Simple confidence proxy: sum of emotion probabilities, clamped to [0, 1]."""
    if not top_emotions:
        return 0.0
    conf = sum(_to_0_1(e.get("score", 0.0)) for e in top_emotions)
    if conf < 0.0:
        return 0.0
    if conf > 1.0:
        return 1.0
    return conf


def article_mood_score(article) -> float:
    """
    Compute a 0..100 mood score for a single article.

    - Sentiment: -100..100 => 0..100
    - Emotion: weighted mean valence -1..1 => 0..100
    - Blend weight: depends on emotion confidence (more confident => more emotion influence)
    """
    sentiment = float(article.get("sentiment_score", 0.0))  # expected -100..100
    normalized_sentiment = (sentiment + 100.0) / 2.0  # 0..100

    emo_effect = weighted_mean_valence(article.get("top_emotions", []))  # -1..1
    emotion_0_100 = ((emo_effect + 1.0) / 2.0) * 100.0  # 0..100

    conf = emotion_confidence(article.get("top_emotions", []))  # 0..1
    emotion_weight = min(0.45, 0.15 + 0.30 * conf)  # 0.15..0.45
    sent_weight = 1.0 - emotion_weight

    mood = sent_weight * normalized_sentiment + emotion_weight * emotion_0_100

    if mood < 0.0:
        return 0.0
    if mood > 100.0:
        return 100.0
    return mood


def _distribution_from_totals(totals: dict, n_articles: int) -> dict:
    """
    Build a true emotion distribution:
    - totals[label] is sum of emotion scores across articles (missing => 0)
    - avg per-article = totals / n_articles
    - normalize so sum = 1.0 (if possible)
    Returns a dict[label] -> prob (0..1) that sums to 1.
    """
    if n_articles <= 0:
        return {"neutral": 1.0}

    avg_per_article = {k: (v / n_articles) for k, v in totals.items() if v > 0}
    total_mass = sum(avg_per_article.values())

    if total_mass <= 0.0:
        return {"neutral": 1.0}

    return {k: (v / total_mass) for k, v in avg_per_article.items()}


def _negativity_index(dist: dict) -> float:
    """Sum of distribution mass where valence < 0."""
    neg = 0.0
    for emo, p in dist.items():
        if EMOTION_VALENCE.get(emo, 0.0) < 0:
            neg += float(p)
    if neg < 0.0:
        return 0.0
    if neg > 1.0:
        return 1.0
    return neg


# -----------------------------
# Public API
# -----------------------------
def calculate_world_mood(file_path):
    with open(file_path, "r") as f:
        articles = json.load(f)

    sentiment_sum, n_articles = 0.0, 0
    emotion_totals = defaultdict(float)   # sum of probabilities per label across ALL articles
    mood_scores = []

    for article in articles:
        sentiment_sum += float(article.get("sentiment_score", 0.0))
        n_articles += 1

        # Sum emotion probabilities; missing emotions implicitly contribute 0 for that article.
        for emo in article.get("top_emotions", []):
            label = str(emo.get("label", "neutral")).lower().strip()
            emotion_totals[label] += _to_0_1(emo.get("score", 0.0))

        mood_scores.append(article_mood_score(article))

    avg_sentiment = sentiment_sum / n_articles if n_articles else 0.0
    normalized_sentiment = (avg_sentiment + 100.0) / 2.0

    # TRUE distribution (sums to 1)
    avg_emotions = _distribution_from_totals(emotion_totals, n_articles)

    dominant_emotion = max(avg_emotions, key=avg_emotions.get, default="neutral")
    dominant_emotion_score = float(avg_emotions.get(dominant_emotion, 0.0))

    final_world_mood_score = sum(mood_scores) / len(mood_scores) if mood_scores else 0.0
    negativity = _negativity_index(avg_emotions)

    return {
        "average_sentiment": round(avg_sentiment, 2),
        "normalized_sentiment": round(normalized_sentiment, 2),
        # Now a TRUE distribution (0..1, sums to 1)
        "average_emotions": {k: round(v, 6) for k, v in avg_emotions.items()},
        "dominant_emotion": dominant_emotion,
        "dominant_emotion_score": round(dominant_emotion_score, 6),
        "negativity_index": round(negativity, 6),
        "final_world_mood_score": round(final_world_mood_score, 2),
        "article_count": n_articles,
    }


def calculate_source_moods(file_path):
    with open(file_path, "r") as f:
        articles = json.load(f)

    source_data = defaultdict(lambda: {
        "sentiment_sum": 0.0,
        "n": 0,
        "mood_sum": 0.0,
        "emotion_totals": defaultdict(float),
    })

    for article in articles:
        src = article.get("source", "Unknown")
        source_data[src]["sentiment_sum"] += float(article.get("sentiment_score", 0.0))
        source_data[src]["n"] += 1
        source_data[src]["mood_sum"] += article_mood_score(article)

        for emo in article.get("top_emotions", []):
            label = str(emo.get("label", "neutral")).lower().strip()
            source_data[src]["emotion_totals"][label] += _to_0_1(emo.get("score", 0.0))

    results = {}
    for src, data in source_data.items():
        n = data["n"] if data["n"] else 0
        avg_sentiment = (data["sentiment_sum"] / n) if n else 0.0
        normalized_sentiment = (avg_sentiment + 100.0) / 2.0
        mood_score = (data["mood_sum"] / n) if n else 0.0

        dist = _distribution_from_totals(data["emotion_totals"], n)
        top_emotion = max(dist, key=dist.get, default="neutral")

        results[src] = {
            "average_sentiment": round(avg_sentiment, 2),
            "normalized_sentiment": round(normalized_sentiment, 2),
            "mood_score": round(mood_score, 2),
            "average_emotions": {k: round(v, 6) for k, v in dist.items()},
            "top_emotion": top_emotion,
            "top_emotion_score": round(float(dist.get(top_emotion, 0.0)), 6),
            "negativity_index": round(_negativity_index(dist), 6),
            "article_count": n,
        }

    return results


def calculate_category_moods(file_path):
    with open(file_path, "r") as f:
        articles = json.load(f)

    category_data = defaultdict(lambda: {
        "sentiment_sum": 0.0,
        "n": 0,
        "mood_sum": 0.0,
        "emotion_totals": defaultdict(float),
    })

    for article in articles:
        cat = article.get("category", "Other")
        category_data[cat]["sentiment_sum"] += float(article.get("sentiment_score", 0.0))
        category_data[cat]["n"] += 1
        category_data[cat]["mood_sum"] += article_mood_score(article)

        for emo in article.get("top_emotions", []):
            label = str(emo.get("label", "neutral")).lower().strip()
            category_data[cat]["emotion_totals"][label] += _to_0_1(emo.get("score", 0.0))

    results = {}
    for cat, data in category_data.items():
        n = data["n"] if data["n"] else 0
        avg_sentiment = (data["sentiment_sum"] / n) if n else 0.0
        normalized_sentiment = (avg_sentiment + 100.0) / 2.0
        mood_score = (data["mood_sum"] / n) if n else 0.0

        dist = _distribution_from_totals(data["emotion_totals"], n)
        top_emotion = max(dist, key=dist.get, default="neutral")

        results[cat] = {
            # Keep your template expectation: "sentiment_score" is 0..100
            "sentiment_score": round(normalized_sentiment, 2),
            "mood_score": round(mood_score, 2),
            "top_emotion": top_emotion,
            "top_emotion_score": round(float(dist.get(top_emotion, 0.0)), 6),
            "average_emotions": {k: round(v, 6) for k, v in dist.items()},
            "negativity_index": round(_negativity_index(dist), 6),
            "article_count": n,
        }

    return results


def prepare_emotion_data(file_path="news_articles_scored.json"):
    """
    Chart helper.
    Returns:
      - category_emotions: distribution per category (sums to 1 across emotions for each category)
      - overall_emotions: overall distribution (sums to 1)
    """
    if not os.path.exists(file_path):
        return {"error": "Data file not found."}

    with open(file_path, "r") as f:
        articles = json.load(f)

    # Accumulate totals and counts for true distributions (missing => 0)
    category_totals = defaultdict(lambda: defaultdict(float))
    category_counts = defaultdict(int)
    overall_totals = defaultdict(float)
    overall_count = 0

    for art in articles:
        cat = art.get("category", "Other")
        category_counts[cat] += 1
        overall_count += 1

        for emotion in art.get("top_emotions", []):
            label = str(emotion.get("label", "neutral")).lower().strip()
            score = _to_0_1(emotion.get("score", 0.0))
            category_totals[cat][label] += score
            overall_totals[label] += score

    category_emotions = {}
    for cat, totals in category_totals.items():
        dist = _distribution_from_totals(totals, category_counts[cat])
        category_emotions[cat] = dist

    overall_dist = _distribution_from_totals(overall_totals, overall_count)

    overall_emotions = [
        {"emotion_label": k, "emotion_score": v}
        for k, v in sorted(overall_dist.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "category_emotions": category_emotions,
        "overall_emotions": overall_emotions,
    }


if __name__ == "__main__":
    file_path = "news_articles_scored.json"
    print(json.dumps(calculate_world_mood(file_path), indent=2))
    print(json.dumps(calculate_source_moods(file_path), indent=2))
    print(json.dumps(calculate_category_moods(file_path), indent=2))
    print(json.dumps(prepare_emotion_data(file_path), indent=2))
