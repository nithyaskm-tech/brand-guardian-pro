from curl_cffi import requests
from bs4 import BeautifulSoup
import time

def test_config(url, impersonate_ver, user_agent):
    print(f"\n--- Testing {impersonate_ver} on {url} ---")
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "User-Agent": user_agent,
        "Referer": "https://www.google.com/"
    }
    
    try:
        response = requests.get(
            url, 
            impersonate=impersonate_ver, 
            headers=headers,
            timeout=15
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else "No Title"
            print(f"Page Title: {title}")
            
            # Check for blocking text
            text = soup.get_text().lower()
            if "enter the characters you see below" in text:
                print("Result: CAPTCHA Blocked")
                return False
            elif "api-services-support@amazon.com" in text:
                print("Result: Hard Blocked")
                return False
            else:
                products = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
                print(f"Result: Success (Found {len(products)} standard product containers)")
                return True
        else:
            print("Result: HTTP Error")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# Test Scenarios
amazon_url = "https://www.amazon.in/s?k=Canon+Printer"
configs = [
    ("chrome110", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"),
    ("chrome120", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("safari15_5", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15"),
]

for imp, ua in configs:
    success = test_config(amazon_url, imp, ua)
    if success:
        print(f"✅ WORKING CONFIG: {imp}")
        break
    time.sleep(2)
