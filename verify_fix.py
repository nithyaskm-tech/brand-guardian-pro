from app import detect_brand_products
import logging

# Setup basic logging to see what's happening
logging.basicConfig(level=logging.INFO)

print("\n--- Verifying Amazon Fix ---")
url = "https://www.amazon.in/s?k=Canon+Printer"
brand = "Canon"

print(f"Scanning {url} for brand '{brand}'...")
result = detect_brand_products(url, brand)

print(f"\nStatus: {result['status']}")
print(f"Details: {result['details']}")
print(f"Products Found: {len(result['products'])}")

# ... existing code ...
from bs4 import BeautifulSoup
from curl_cffi import requests

print("\n--- Deep Debug of Amazon Logic ---")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/"
}
resp = requests.get(url, impersonate="chrome110", headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')
cards = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
print(f"DEBUG: Found {len(cards)} cards manually.")

for i, card in enumerate(cards[:3]):
    print(f"\n--- Card {i} match attempt ---")
    title_node = card.find("h2")
    if not title_node:
        print("FAIL: No h2 title node")
        continue
    
    print("Starting Multi-Strategy Title Search...")
    link_node = None
    
    # Strategy 1: Link inside H2
    h2_candidates = card.find_all("h2")
    for h2 in h2_candidates:
        possible_link = h2.find("a", href=True)
        if possible_link:
            link_node = possible_link
            print("Found via Strategy 1 (H2)")
            break
            
    # Strategy 2: Look for standard title class if H2 failed
    if not link_node:
            link_node = card.find("a", class_=lambda x: x and "a-text-normal" in x, href=True)
            if link_node: print("Found via Strategy 2 (a-text-normal)")

    # Strategy 3: Look for link containing span with a-text-normal
    if not link_node:
            span_text = card.find("span", class_=lambda x: x and "a-text-normal" in x)
            if span_text and span_text.parent.name == "a":
                link_node = span_text.parent
                print("Found via Strategy 3 (parent of span)")

    if not link_node:
        print("FAIL: No link found via any strategy")
        continue

    name = link_node.get_text(strip=True)
    print(f"Name Found: {name}")
    
    # if brand.lower() not in name.lower():
    #      print("FAIL: Brand name mismatch")
    #      continue
         
    # print("SUCCESS: Product would be added.")

