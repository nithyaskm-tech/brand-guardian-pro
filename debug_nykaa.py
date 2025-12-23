from curl_cffi import requests
from bs4 import BeautifulSoup

def check_nykaa(query="Chanel"): # Changed default query to a common brand
    url = f"https://www.nykaa.com/search/result/?q={query}"
    print(f"Checking {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, impersonate="chrome120", headers=headers, timeout=20)
        print(f"Status: {response.status_code}")
        
        with open("nykaa_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved HTML to nykaa_debug.html")

        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text().lower()
        
        # Check for block
        if "captcha" in text or "verify you are human" in text:
            print("ALERT: Likely CAPTCHA blocked.")
            return

        # Check for price symbols (critical for generic extractor)
        if "₹" in response.text:
            print("Success: Found '₹' symbol in text.")
        else:
            print("Warning: No '₹' symbol found. Generic extractor requires this.")
            
        # Quick check for product containers using generic heuristics
        candidates = soup.find_all("div", class_=lambda x: x and "product" in x.lower())
        print(f"Found {len(candidates)} divs with 'product' in class.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_nykaa()
