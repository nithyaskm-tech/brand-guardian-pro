from curl_cffi import requests
from bs4 import BeautifulSoup

def check_nykaa(query):
    url = f"https://www.nykaa.com/search/result/?q={query}"
    print(f"Checking {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, impersonate="chrome120", headers=headers)
    print(f"Status: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    
    if "No results found" in text or "We couldn't find any results" in text:
        print("Text indicates NO results.")
    else:
        print("Text does NOT explicitly say no results.")
        
    titles = [x.get_text(strip=True) for x in soup.find_all(['h1', 'h2', 'div'], class_=lambda x: x and 'title' in x.lower())]
    print(f"Found {len(titles)} potential titles.")
    print(titles[:5])

check_nykaa("Canon PIXMA E470")
