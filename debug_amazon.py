from curl_cffi import requests
from bs4 import BeautifulSoup

def test_amazon():
    url = "https://www.amazon.com/s?k=chanel" # use www
    configs = [
        ("chrome110", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}),
        ("safari15_3", {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15"}),
    ]
    
    for imp, ua in configs:
        print(f"\nTesting {imp}...")
        try:
            response = requests.get(
                url, 
                impersonate=imp, 
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Referer": "https://www.google.com/",
                    **ua
                }, 
                timeout=10
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True).lower()
                print("Look for result items...")
                items = soup.find_all(attrs={"data-component-type": "s-search-result"})
                print(f"Found {len(items)} items using data-component-type")
                
                if "captcha" in text or "enter the characters" in text:
                    print("CAPTCHA DETECTED")
                else:
                    print(text[:200])
                    break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_amazon()
