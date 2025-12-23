from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import re

def debug_flipkart(brand="Canon"):
    url = f"https://www.flipkart.com/search?q={brand}"
    print(f"Fetching {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": "https://www.flipkart.com"
    }
    
    try:
        response = requests.get(url, impersonate="chrome120", headers=headers, timeout=20)
        print(f"Status: {response.status_code}")
        
        with open("flipkart_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved flipkart_debug.html")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check 1: Redux/State
        scripts = soup.find_all('script')
        found_state = False
        for s in scripts:
            if s.string and "window.__INITIAL_STATE__" in s.string:
                print("Found window.__INITIAL_STATE__")
                found_state = True
                # Snippet
                print(s.string[:500] + "...")
                break
        
        if not found_state:
            print("Did NOT find window.__INITIAL_STATE__")
            
        # Check 2: Classes
        # Flipkart grid classes often: _1AtVbE, _13oc-S
        divs = soup.find_all("div", class_=re.compile(r"(_1AtVbE|_13oc-S|_4ddWXP)"))
        print(f"Found {len(divs)} common Flipkart product divs.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_flipkart()
