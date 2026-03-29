import requests
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

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


# Fix RSS subdomains → main domains
domain_overrides = {
    "feeds.bbci.co.uk": "bbc.com",
    "rss.cnn.com": "cnn.com",
    "rss.nytimes.com": "nytimes.com",
    "feeds.foxnews.com": "foxnews.com",
    "www.bloomberg.com": "bloomberg.com",
    "api.foxsports.com/": "foxsports.com",
    


}

def get_domain(url):
    parsed = urlparse(url)
    return domain_overrides.get(parsed.netloc, parsed.netloc)

def scrape_icons(domain):
    """Scrape homepage for apple-touch-icon or favicon"""
    homepage = f"https://{domain}"
    try:
        resp = requests.get(homepage, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        icons = []

        # Look for apple-touch-icon first (best for quality)
        for link in soup.find_all("link", rel=lambda x: x and "apple-touch-icon" in x):
            href = link.get("href")
            if href:
                icons.append(urljoin(homepage, href))

        # Look for large favicons
        for link in soup.find_all("link", rel=lambda x: x and "icon" in x):
            href = link.get("href")
            if href:
                icons.append(urljoin(homepage, href))

        # Deduplicate and prefer biggest
        if icons:
            icons = list(dict.fromkeys(icons))  # preserve order, remove dups
            return {
                "touch_icon": icons[0],
                "favicon": icons[-1]  # often last one is the smaller .ico
            }
    except Exception as e:
        print(f"[ERROR] Scraping failed for {domain}: {e}")

    # fallback
    return {
        "touch_icon": f"https://{domain}/favicon.ico",
        "favicon": f"https://{domain}/favicon.ico"
    }

def build_icons_json(feeds):
    results = {}
    for category, sources in feeds.items():
        results[category] = {}
        for name, url in sources.items():
            domain = get_domain(url)
            print(f"Fetching icons for {name} ({domain})...")
            icons = scrape_icons(domain)
            results[category][name] = {
                "domain": domain,
                "touch_icon": icons["touch_icon"],
                "favicon": icons["favicon"]
            }
    return results

if __name__ == "__main__":
    icons_data = build_icons_json(rss_feeds)
    with open("news_icons.json", "w", encoding="utf-8") as f:
        json.dump(icons_data, f, indent=2)
    print("✅ Saved icons to news_icons.json")
