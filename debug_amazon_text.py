from curl_cffi import requests
from bs4 import BeautifulSoup

def debug_amazon_text():
    url = "https://www.amazon.in/s?k=Canon+Printer"
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        # Using the same user agent as app.py (chrome110)
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        print(f"Fetching {url}...")
        response = requests.get(
            url, 
            impersonate="chrome110", 
            headers=headers,
            timeout=20
        )
        print(f"Status Code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True).lower()
        
        print("\n--- Text Content Start ---")
        try:
            print(text_content[:2000]) # Print first 2000 chars
        except UnicodeEncodeError:
            print(text_content[:2000].encode('utf-8', errors='ignore'))
        print("--- Text Content End ---")

        negative_signals = [
            "no results found", 
            "did not match any products", 
            "0 results for", 
            "we couldn't find any results",
            "nothing matches your search"
        ]
        
        print("\n--- Negative Signal Check ---")
        for ns in negative_signals:
            if ns in text_content:
                print(f"FOUND NEGATIVE SIGNAL: '{ns}'")
            else:
                print(f"Did not find: '{ns}'")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_amazon_text()
