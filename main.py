import feedparser
import json
import re
from bs4 import BeautifulSoup
import html


# RSS feed URLs grouped by category
rss_feeds = {
    "Global": {
        "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "Reuters": "http://feeds.reuters.com/reuters/topNews",
        "The Guardian": "https://www.theguardian.com/world/rss",
        "Yahoo News" : "https://www.yahoo.com/news/rss/world/",
        'Vox' : "https://www.vox.com/rss/index.xml",
        
    },
    "US": {
        "CNN": "http://rss.cnn.com/rss/edition.rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "FOX": "http://feeds.foxnews.com/foxnews/latest"
    },
    "Business": {
        "Bloomberg": "https://www.bloomberg.com/feed/podcast/etf-report.xml",
        "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "Forbes": "https://www.forbes.com/real-time/feed2/",
        "Wired Business": "https://www.wired.com/feed/category/business/latest/rss"
    },
    "Tech": {
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "Wired": "https://www.wired.com/feed/tag/ai/latest/rss",
        "TechCrunch": "https://techcrunch.com/feed/",

    },
    "Sports": {
        "ESPN": "https://www.espn.com/espn/rss/news",
        "CBS Sports": "https://www.cbssports.com/rss/headlines/",
        'Fox Sports': "https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30",

    },
    "Entertainment": {
        "Variety": "https://variety.com/feed/",
        "Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
        "Rolling Stone": "https://www.rollingstone.com/feed/"
    },

    "Science"   : {
        "National Geographic": "https://www.nationalgeographic.com/content/nationalgeographic/en_us/news/all-news.rss",
        "Science News": "https://www.sciencenews.org/feed",
        "Wired Science": "https://www.wired.com/feed/category/science/latest/rss"
    },

    "India" : {
        "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
        "Times of India": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
        "Indian Express": "https://indianexpress.com/feed/"
    }
}

def clean_summary(summary):
    """Clean HTML, decode entities, and normalize whitespace in summaries."""
    if not summary:
        return ""
    
    # Fix encoding issues (common in feeds)
    try:
        summary = summary.encode("latin1").decode("utf-8")
    except:
        pass

    # Decode HTML entities
    decoded = html.unescape(summary)

    # Strip HTML tags
    soup = BeautifulSoup(decoded, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    # Normalize whitespace
    return " ".join(text.split())




def extract_image(entry):
    """Try to extract an image from the RSS entry and upgrade quality if possible."""
    def upgrade_bbc(url):
        if url and "ichef.bbci.co.uk" in url:
            return re.sub(r"/\d{2,4}/", "/800/", url)
        return url

    # Check for media:content
    if "media_content" in entry:
        url = entry.media_content[0].get("url", None)
        return upgrade_bbc(url)

    # Check for media:thumbnail
    if "media_thumbnail" in entry:
        url = entry.media_thumbnail[0].get("url", None)
        return upgrade_bbc(url)

    # Look for an <img> tag in the summary
    if "summary" in entry:
        match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
        if match:
            return upgrade_bbc(match.group(1))

    # Some feeds put images in content
    if "content" in entry:
        for c in entry.content:
            match = re.search(r'<img[^>]+src="([^">]+)"', c.value)
            if match:
                return upgrade_bbc(match.group(1))

    return None



def fetch_feeds(feeds, max_articles=5):
    """Fetch latest articles from given RSS feeds grouped by category."""
    articles = []

    for category, sources in feeds.items():
        for source, url in sources.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_articles]:
                    summary = clean_summary(entry.get("summary", ""))
                    if not summary:
                        continue  # skip if no usable summary
                    
                    articles.append({
                        "category": category,
                        "source": source,
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published", "N/A"),
                        "summary": summary,
                        "image": extract_image(entry)
                    })
            except Exception as e:
                print(f"[ERROR] Failed to fetch {source}: {e}")

    return articles

if __name__ == "__main__":
    news_articles = fetch_feeds(rss_feeds, max_articles=10)
    print(json.dumps(news_articles, indent=2, ensure_ascii=False))

    # Save the fetched articles to a JSON file
    with open("news_articles.json", "w", encoding="utf-8") as f:
        json.dump(news_articles, f, indent=2, ensure_ascii=False)
