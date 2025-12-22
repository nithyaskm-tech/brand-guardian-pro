from curl_cffi import requests
from bs4 import BeautifulSoup
import re

def identify_seller_from_card(card, domain, brand_name):
    # Mocking the function from app.py to reproduce issues
    seller_candidates = []
    text_nodes = list(card.stripped_strings)
    
    # 1. Regex Extraction
    full_text = " ".join(text_nodes)
    print(f"\n[DEBUG] Full Text of Card (First 300 chars): {full_text[:300]}...")
    
    regex_patterns = [
        r"(?i)(?:sold by|seller|courtesy of|merchant|importer|marketed by)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)",
        r"(?i)(?:brand)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)"
    ]
    
    for pattern in regex_patterns:
        match = re.search(pattern, full_text)
        if match:
            candidate = match.group(1).strip()
            print(f"[DEBUG] Regex Match '{pattern}': '{candidate}'")
            if 2 < len(candidate) < 60:
                 candidate = re.sub(r"(?i)(\d+(\.\d+)?\s?(stars?|ratings?|reviews?))", "", candidate).strip()
                 candidate_lower = candidate.lower()
                 if candidate_lower.startswith(("who offers", "that you chose", "items that")): continue
                 block_list_substrings = ["amazon", "available", "more buying", "details", "installation", "add to cart", "protection plan"]
                 if any(w in candidate_lower for w in block_list_substrings): continue
                 return candidate.title()

    # 2. Text Trigger Analysis
    seller_triggers = ["sold by", "merchant", "importer", "vendor", "shop name", "distributed by", "by "]
    for i, text in enumerate(text_nodes):
        text_lower = text.lower()
        
        # Brand Check
        if brand_name and len(text) < 50:
             if brand_name.lower() in text_lower and "brand" in text_lower:
                  print(f"[DEBUG] Brand Heuristic Match: '{text}'")
                  return brand_name.title()

        for trigger in seller_triggers:
            if trigger in text_lower:
                candidate = None
                if len(text) > len(trigger) + 2:
                    candidate = text_lower.split(trigger)[-1].strip(": -").title()
                elif i + 1 < len(text_nodes):
                    candidate = text_nodes[i+1].strip()
                
                if candidate:
                     print(f"[DEBUG] Trigger Match '{trigger}': '{candidate}'")
                     if 2 < len(candidate) < 60:
                          return candidate

    return "N/A"

def fetch_deep_scan(url, brand_name):
    print(f"Fetching {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    try:
        response = requests.get(url, impersonate="chrome110", headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find Buy Box
        buybox = soup.find(id="merchant-info")
        if buybox:
            print("[DEBUG] Found 'merchant-info' box.")
            print(f"[DEBUG] Box content: {buybox.get_text(separator=' ', strip=True)}")
            return identify_seller_from_card(buybox, "amazon.in", brand_name)
        else:
            print("[DEBUG] 'merchant-info' NOT FOUND.")
            # Standard Fallbacks
            if soup.find(id="tabular-buybox"): print("[DEBUG] Found 'tabular-buybox'")
            
            # Look for specific text
            print("Searching body for 'Sold by'...")
            body_text = soup.body.get_text(separator=" ", strip=True)
            match = re.search(r"(?i)sold by[\s:-]+([A-Za-z0-9\s]+)", body_text)
            if match:
                print(f"[DEBUG] Body Regex found: {match.group(1)[:50]}")
            else:
                print("[DEBUG] 'Sold by' check in body FAILED.")
                
        return "N/A"

    except Exception as e:
        print(f"Error: {e}")
        return "Error"

if __name__ == "__main__":
    # Test with the specific URL reported by user (Chanel Catwalk)
    url = "https://www.amazon.in/Chanel-Catwalk-Collections-Patrick-Mauries/dp/0500023441"
    print(f"Result: {fetch_deep_scan(url, 'Chanel')}")
