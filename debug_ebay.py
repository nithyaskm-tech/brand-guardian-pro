from curl_cffi import requests
from bs4 import BeautifulSoup
import re

def debug_ebay(brand="Canon"):
    url = f"https://www.ebay.com/sch/i.html?_nkw={brand}"
    print(f"Fetching {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, impersonate="chrome120", headers=headers, timeout=20)
        print(f"Status: {response.status_code}")
        
        with open("ebay_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved ebay_debug.html")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # eBay usually uses 's-item' class
        items = soup.find_all(class_=re.compile(r"s-item", re.I))
        print(f"Found {len(items)} items with 's-item' in class.")
        
        if items:
            print("First item classes:", items[0].get('class'))
            print("First item text snippet:", items[0].get_text()[:100])
        else:
            print("No 's-item' classes found. Structure might have changed.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_ebay()
