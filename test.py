from calculate import (
    calculate_world_mood,
    calculate_source_moods,
    calculate_category_moods,
    generate_emotional_headline
)


print("emotional_headline:", generate_emotional_headline("news_articles_scored.json"))