from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import time

def fetch_depop_debug(brand_name="Richard Mille"):
    url = f"https://www.depop.com/search/?q={brand_name.replace(' ', '+')}"
    print(f"Target: {url}")
    
    # Google Cache Strategy
    cache_url = f"http://webcache.googleusercontent.com/search?q=cache:https://www.depop.com/search/?q={brand_name.replace(' ', '+')}"
    print(f"Target Cache: {cache_url}")
    
    # Profiles to test
    profiles = ["chrome110"]
    
    for profile in profiles:
        print(f"\n--- Testing Google Cache with Profile: {profile} ---")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            }

            response = requests.get(
                cache_url, 
                impersonate=profile, 
                headers=headers, 
                timeout=15
            )
            
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("SUCCESS: Cache Accessed!")
                soup = BeautifulSoup(response.text, 'html.parser')
                print(f"Title: {soup.title.string if soup.title else 'No Title'}")
                if "404" in str(soup.title) or "Error" in str(soup.title):
                     print("Cache might be empty/404.")
                else:
                     print("Cache seems valid. Do we see products?")
                     if "product" in response.text.lower():
                          print("Yes, 'product' keyword found.")
                return
            else:
                 print(f"Cache Blocked/Error: {response.status_code}")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Error with {profile}: {e}")

if __name__ == "__main__":
    fetch_depop_debug()
