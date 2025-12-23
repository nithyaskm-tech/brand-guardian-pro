from curl_cffi import requests
from bs4 import BeautifulSoup
import re

def fetch_live_debug():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }
    
    # 1. Test eBay for "Chanel"
    ebay_url = "https://www.ebay.com/sch/i.html?_nkw=Chanel"
    print(f"Fetching eBay: {ebay_url}")
    try:
        r_ebay = requests.get(ebay_url, impersonate="chrome120", headers=headers, timeout=20)
        print(f"eBay Status: {r_ebay.status_code}")
        with open("ebay_chanel_live.html", "w", encoding="utf-8") as f:
            f.write(r_ebay.text)
        
        if "captcha" in r_ebay.text.lower() or "suspicious" in r_ebay.text.lower():
             print("eBay: Startling CAPTCHA/Block detected!")
        elif "Chanel" in r_ebay.text:
             print("eBay: Found 'Chanel' in text")
        else:
             print("eBay: 'Chanel' NOT found in text")
             
    except Exception as e:
        print(f"eBay Error: {e}")

    # 2. Test Flipkart for "Chanel"
    flip_url = "https://www.flipkart.com/search?q=Chanel"
    print(f"\nFetching Flipkart: {flip_url}")
    try:
        r_flip = requests.get(flip_url, impersonate="chrome120", headers=headers, timeout=20)
        print(f"Flipkart Status: {r_flip.status_code}")
        with open("flipkart_chanel_live.html", "w", encoding="utf-8") as f:
            f.write(r_flip.text)
            
        if "Chanel" in r_flip.text:
             print("Flipkart: Found 'Chanel' in text")
        else:
             print("Flipkart: 'Chanel' NOT found in text")
             
    except Exception as e:
        print(f"Flipkart Error: {e}")

if __name__ == "__main__":
    fetch_live_debug()
