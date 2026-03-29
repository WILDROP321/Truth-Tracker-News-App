import json
from collections import defaultdict
import pandas as pd
import os



# --- Mood blending weights (tweak to tune influence) ---
# Sentiment is on 0..100; emotion_effect is -1..1 averaged.
SENTIMENT_WEIGHT = 1.0
EMOTION_WEIGHT = 25.0   # scales -1..1 into ±25 points
NEG_EMOTION_EXTRA = 0.5  # extra weight on negative valence when computing per-article weighted effect

# Emotion valence: +1 positive, -1 negative, 0 neutral
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
    "surprise": 0.3  # could be pos or neg, your choice
}

def calculate_world_mood(file_path):
    with open(file_path, "r") as f:
        articles = json.load(f)

    sentiment_sum, sentiment_count = 0, 0
    emotion_totals = defaultdict(float)
    emotion_counts = defaultdict(int)
    mood_scores = []

    for article in articles:
        sentiment_sum += article["sentiment_score"]
        sentiment_count += 1

        # --- Weighted emotion effect ---
        weighted_effect = 0
        total_weight = 0
        for emo in article["top_emotions"]:
            emo_score = emo.get("score", 0.0)
            if emo_score > 1:
                emo_score = emo_score / 100.0
            label = emo["label"].lower()
            valence = EMOTION_VALENCE.get(label, 0)
            extra = NEG_EMOTION_EXTRA if valence < 0 else 0.0
            weight = abs(valence) + extra
            weighted_effect += valence * emo_score * weight
            total_weight += weight

            emotion_totals[label] += emo_score
            emotion_counts[label] += 1

        if total_weight > 0:
            weighted_effect /= total_weight

        normalized_sentiment = (article["sentiment_score"] + 100) / 2

        # --- Final mood score per article ---
        emotion_0_100 = ((weighted_effect + 1) / 2) * 100
        mood_score = 0.6 * normalized_sentiment + 0.4 * emotion_0_100

        mood_scores.append(mood_score)

    avg_sentiment = sentiment_sum / sentiment_count if sentiment_count else 0
    normalized_sentiment = (avg_sentiment + 100) / 2
    avg_emotions = {emo: emotion_totals[emo] / emotion_counts[emo] for emo in emotion_totals}

    dominant_emotion = max(avg_emotions, key=avg_emotions.get, default="neutral")
    dominant_emotion_score = avg_emotions.get(dominant_emotion, 0)

    final_world_mood_score = sum(mood_scores) / len(mood_scores) if mood_scores else 0

    return {
        "average_sentiment": round(avg_sentiment, 2),
        "normalized_sentiment": round(normalized_sentiment, 2),
        "average_emotions": {k: round(v, 2) for k, v in avg_emotions.items()},
        "dominant_emotion": dominant_emotion,
        "dominant_emotion_score": round(dominant_emotion_score, 2),
        "final_world_mood_score": round(final_world_mood_score, 2)
    }


def calculate_source_moods(file_path):
    with open(file_path, "r") as f:
        articles = json.load(f)

    source_data = defaultdict(lambda: {
        "sentiment_sum": 0,
        "sentiment_count": 0,
        "mood_sum": 0,
        "mood_count": 0,
        "emotion_totals": defaultdict(float),
        "emotion_counts": defaultdict(int)
    })

    for article in articles:
        src = article["source"]
        source_data[src]["sentiment_sum"] += article["sentiment_score"]
        source_data[src]["sentiment_count"] += 1

        emotion_effect = 0
        for emo in article["top_emotions"]:
            emo_score = emo.get("score", 0.0)
            if emo_score > 1:
                emo_score = emo_score / 100.0
            label = emo["label"].lower()
            valence = EMOTION_VALENCE.get(label, 0)
            emotion_effect += valence * emo_score
            source_data[src]["emotion_totals"][label] += emo_score
            source_data[src]["emotion_counts"][label] += 1

        total = 0.0
        emotion_effect = 0.0
        for emo in article["top_emotions"]:
            s = emo.get("score", 0.0)
            if s > 1: s /= 100.0
            v = EMOTION_VALENCE.get(emo["label"].lower(), 0)
            emotion_effect += v * s
            total += s

        if total > 0:
            emotion_effect /= total   # weighted mean valence
        else:
            emotion_effect = 0.0

        normalized_sentiment = (article["sentiment_score"] + 100) / 2
        mood_score = max(min(SENTIMENT_WEIGHT * normalized_sentiment + EMOTION_WEIGHT * emotion_effect, 100), 0)

        source_data[src]["mood_sum"] += mood_score
        source_data[src]["mood_count"] += 1

    results = {}
    for src, data in source_data.items():
        avg_sentiment = data["sentiment_sum"] / data["sentiment_count"] if data["sentiment_count"] else 0
        normalized_sentiment = (avg_sentiment + 100) / 2
        avg_emotions = {emo: data["emotion_totals"][emo] / data["emotion_counts"][emo] for emo in data["emotion_totals"]}
        mood_score = data["mood_sum"] / data["mood_count"] if data["mood_count"] else 0

        results[src] = {
            "average_sentiment": round(avg_sentiment, 2),
            "normalized_sentiment": round(normalized_sentiment, 2),
            "average_emotions": {k: round(v, 2) for k, v in avg_emotions.items()},
            "mood_score": round(mood_score, 2)
        }

    return results


def calculate_category_moods(file_path):
    with open(file_path, "r") as f:
        articles = json.load(f)

    category_data = defaultdict(lambda: {
        "sentiment_sum": 0,
        "sentiment_count": 0,
        "mood_sum": 0,
        "mood_count": 0,
        "emotion_totals": defaultdict(float),
        "emotion_counts": defaultdict(int)
    })

    for article in articles:
        cat = article.get("category", "Other")
        category_data[cat]["sentiment_sum"] += article["sentiment_score"]
        category_data[cat]["sentiment_count"] += 1

        emotion_effect = 0
        for emo in article["top_emotions"]:
            emo_score = emo.get("score", 0.0)
            if emo_score > 1:
                emo_score = emo_score / 100.0
            label = emo["label"].lower()
            valence = EMOTION_VALENCE.get(label, 0)
            emotion_effect += valence * emo_score
            category_data[cat]["emotion_totals"][label] += emo_score
            category_data[cat]["emotion_counts"][label] += 1

        total = 0.0
        emotion_effect = 0.0
        for emo in article["top_emotions"]:
            s = emo.get("score", 0.0)
            if s > 1: s /= 100.0
            v = EMOTION_VALENCE.get(emo["label"].lower(), 0)
            emotion_effect += v * s
            total += s

        if total > 0:
            emotion_effect /= total   # weighted mean valence
        else:
            emotion_effect = 0.0

        normalized_sentiment = (article["sentiment_score"] + 100) / 2
        mood_score = max(min(SENTIMENT_WEIGHT * normalized_sentiment + EMOTION_WEIGHT * emotion_effect, 100), 0)

        category_data[cat]["mood_sum"] += mood_score
        category_data[cat]["mood_count"] += 1

    results = {}
    for cat, data in category_data.items():
        avg_sentiment = data["sentiment_sum"] / data["sentiment_count"] if data["sentiment_count"] else 0
        normalized_sentiment = (avg_sentiment + 100) / 2
        avg_emotions = {emo: data["emotion_totals"][emo] / data["emotion_counts"][emo] for emo in data["emotion_totals"]}
        top_emotion = max(avg_emotions, key=avg_emotions.get, default="neutral")
        top_emotion_score = avg_emotions.get(top_emotion, 0)
        mood_score = data["mood_sum"] / data["mood_count"] if data["mood_count"] else 0

        results[cat] = {
            "sentiment_score": round(normalized_sentiment, 2),
            "top_emotion": top_emotion,
            "top_emotion_score": round(top_emotion_score, 2),
            "mood_score": round(mood_score, 2)
        }

    return results


def prepare_emotion_data(file_path="news_articles_scored.json"):
    if not os.path.exists(file_path):
        return {"error": "Data file not found."}

    with open(file_path, "r") as f:
        articles = json.load(f)

    rows = []
    for art in articles:
        for emotion in art["top_emotions"]:
            rows.append({
                "category": art["category"],
                "emotion_label": emotion["label"],
                "emotion_score": (emotion["score"]/100.0 if emotion["score"] > 1 else emotion["score"])
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return {"error": "No data available."}

    category_emotions = (
        df.groupby(["category", "emotion_label"])["emotion_score"]
        .mean()
        .reset_index()
        .pivot(index="category", columns="emotion_label", values="emotion_score")
        .fillna(0)
        .to_dict(orient="index")
    )

    overall_emotions = (
        df.groupby("emotion_label")["emotion_score"]
        .mean()
        .reset_index()
        .to_dict(orient="records")
    )

    return {
        "category_emotions": category_emotions,
        "overall_emotions": overall_emotions
    }


if __name__ == "__main__":
    file_path = "news_articles_scored.json"
    world_mood = calculate_world_mood(file_path)
    print(json.dumps(world_mood, indent=2))

    source_moods = calculate_source_moods(file_path)
    print(json.dumps(source_moods, indent=2))

    category_moods = calculate_category_moods(file_path)
    print(json.dumps(category_moods, indent=2))
