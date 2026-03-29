from flask import Flask, render_template, json
import os
import random

from calculate import (
    calculate_world_mood,
    calculate_source_moods,
    calculate_category_moods,
    prepare_emotion_data,
    article_mood_score,
)

app = Flask(__name__)

# ---------------------------
# Jinja helpers
# ---------------------------
def truncate_words(s, num=20):
    if not s:
        return ""
    words = s.split()
    if len(words) <= num:
        return s
    return " ".join(words[:num]) + "..."

app.jinja_env.filters["truncate_words"] = truncate_words


@app.template_filter("get_icon")
def get_icon(source, news_icons):
    """Usage in template: {{ source | get_icon(news_icons) }}"""
    if not news_icons:
        return None
    for _category, sources in news_icons.items():
        if source in sources:
            return sources[source].get("favicon") or sources[source].get("touch_icon")
    return None


def data():
    file_path = "news_articles_scored.json"
    if not os.path.exists(file_path):
        return {"error": "Data file not found. Run cron_job.py / analysis pipeline first."}

    with open(file_path, "r") as f:
        articles = json.load(f)

    # Ensure legacy data won't break the UI
    for a in articles:
        a.setdefault("sentiment_label", "neutral")
        a.setdefault("top_emotion", "neutral")
        a.setdefault("top_emotions", [{"label": a.get("top_emotion", "neutral"), "score": 1.0}])
        a.setdefault("emotion_valence", 0.0)
        a.setdefault("emotion_confidence", 0.0)

        if "mood_score_0_100" not in a:
            try:
                a["mood_score_0_100"] = round(float(article_mood_score(a)), 2)
            except Exception:
                a["mood_score_0_100"] = 50.0

        # For sorting/filtering convenience
        try:
            a["emotion_intensity"] = round(float(abs(a.get("emotion_valence", 0.0)) * a.get("emotion_confidence", 0.0)), 6)
        except Exception:
            a["emotion_intensity"] = 0.0

    world_mood = calculate_world_mood(file_path)
    source_moods = calculate_source_moods(file_path)
    category_moods = calculate_category_moods(file_path)
    emotion_data = prepare_emotion_data(file_path)

    categories = {}
    for article in articles:
        if not article.get("summary"):
            continue
        cat = article.get("category", "Other")
        categories.setdefault(cat, []).append(article)

    # diversify and shuffle within each category
    for cat, arts in categories.items():
        random.shuffle(arts)

        seen_sources = set()
        diverse_articles = []

        # First pass: unique sources
        for art in arts:
            if art.get("source") not in seen_sources:
                diverse_articles.append(art)
                seen_sources.add(art.get("source"))
            if len(diverse_articles) >= 6:
                break

        # Second pass: fill if less than 6 (allow duplicates)
        if len(diverse_articles) < 6:
            for art in arts:
                if art not in diverse_articles:
                    diverse_articles.append(art)
                if len(diverse_articles) >= 6:
                    break

        # Ensure featured article has image if possible
        if diverse_articles and not diverse_articles[0].get("image"):
            for idx, art in enumerate(diverse_articles):
                if art.get("image"):
                    diverse_articles.insert(0, diverse_articles.pop(idx))
                    break

        categories[cat] = diverse_articles

    # For dropdown: stable list of emotion labels
    emotion_labels = sorted(list(world_mood.get("average_emotions", {}).keys()))

    return {
        "world_mood_score": world_mood["final_world_mood_score"],
        "dominant_emotion": world_mood["dominant_emotion"],
        "dominant_emotion_score": world_mood["dominant_emotion_score"],
        "average_emotions": world_mood["average_emotions"],
        "emotion_labels": emotion_labels,
        "source_moods": source_moods,
        "category_moods": category_moods,
        "categories": categories,
        "category_emotions": emotion_data["category_emotions"],
        "overall_emotions": emotion_data["overall_emotions"],
    }


@app.route("/")
def home():
    data_dict = data()
    if "error" in data_dict:
        return render_template("error.html", error=data_dict["error"])

    with open("news_icons.json", "r") as f:
        news_icons = json.load(f)

    return render_template(
        "index.html",
        world_mood_score=data_dict["world_mood_score"],
        dominant_emotion=data_dict["dominant_emotion"],
        dominant_emotion_score=data_dict["dominant_emotion_score"],
        average_emotions=data_dict["average_emotions"],
        emotion_labels=data_dict["emotion_labels"],
        categories=data_dict["categories"],
        category_moods=data_dict["category_moods"],
        source_moods=data_dict["source_moods"],
        category_emotions=data_dict["category_emotions"],
        overall_emotions=data_dict["overall_emotions"],
        news_icons=news_icons,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)