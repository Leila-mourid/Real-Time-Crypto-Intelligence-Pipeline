# news_test.py
import requests
from datetime import datetime

API_KEY = "b61e2b4006ce493599bb179be55cfc89"  # replace this


def fetch_news():
    url = "https://newsapi.org/v2/everything"

    params = {
        # Focus on crypto + market relevance
        "q": '(bitcoin OR ethereum) AND (price OR trading OR market OR volatility)',
        # Only reliable financial/crypto sources
        "sources": "reuters,bloomberg,cnbc,cointelegraph,financial-times",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,   # number of articles per call
        "apiKey": API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("HTTP Error:", response.status_code)
        print(response.text)
        return

    data = response.json()

    if data["status"] != "ok":
        print("API Error:", data)
        return

    print("\n====== Crypto & Market News ======\n")

    for article in data["articles"]:
        print(f"Title        : {article['title']}")
        print(f"Source       : {article['source']['name']}")
        print(f"Published At : {article['publishedAt']}")
        print(f"Description  : {article['description']}")
        print("-" * 60)

    print("\nFetched at:", datetime.utcnow().isoformat())
    print("Total matching results:", data["totalResults"])


if __name__ == "__main__":
    fetch_news()