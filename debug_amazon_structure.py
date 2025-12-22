from curl_cffi import requests
from bs4 import BeautifulSoup

def debug_amazon_structure():
    url = "https://www.amazon.in/s?k=Canon+Printer"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        print(f"Fetching {url}...")
        response = requests.get(url, impersonate="chrome110", headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check standard container
        cards = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
        print(f"Found {len(cards)} 's-search-result' containers.")
        
        if len(cards) == 0:
            print("\n--- DEBUG: HTML Structure ---")
            # Print specific parts to identify layout
            main_content = soup.find("div", {"id": "search"})
            if main_content:
                print("Found #search div.")
                print("Classes in #search:", main_content.get("class"))
            else:
                print("DID NOT find #search div.")
                
            # List some potentially useful divs
            divs = soup.find_all("div", class_=True, limit=20)
            print("\nTop 20 divs with classes:")
            for d in divs:
                print(d.get("class"))
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_amazon_structure()
