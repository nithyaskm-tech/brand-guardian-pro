from curl_cffi import requests
from bs4 import BeautifulSoup
import time

def get_html(url, filename):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, impersonate="chrome120", headers=headers, timeout=20)
        print(f"Status: {response.status_code}")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Saved to {filename}")
    except Exception as e:
        print(f"Error: {e}")

# Nykaa
get_html("https://www.nykaa.com/search/result/?q=chanel", "nykaa_test.html")
# Flipkart
get_html("https://www.flipkart.com/search?q=samsung", "flipkart_test.html")
# eBay
get_html("https://www.ebay.com/sch/i.html?_nkw=chanel", "ebay_test.html")
