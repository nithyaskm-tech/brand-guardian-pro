from app import extract_from_amazon_containers, normalize_product_data
from bs4 import BeautifulSoup
from curl_cffi import requests

def debug_extraction_failure():
    # The URL from the screenshot
    url = "https://www.amazon.in/s?k=Canon-Pixma-E470-Inkjet-Printer"
    
    # Hypothesis: User entered this long string as the "Brand Name"
    brand_name_input = "Canon-Pixma-E470-Inkjet-Printer" 
    
    print(f"Testing extraction for URL: {url}")
    print(f"Brand Input: '{brand_name_input}'")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        response = requests.get(url, impersonate="chrome110", headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print("\n--- Running Extraction ---")
        products = extract_from_amazon_containers(soup, "amazon.in", brand_name_input)
        
        print(f"Found {len(products)} products.")
        if len(products) == 0:
            print("FAILURE: No products found.")
            
            # Debug why
            cards = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
            print(f"DEBUG: Found {len(cards)} raw cards in DOM.")
            
            if cards:
                card = cards[0]
                # Re-run manual check on first card
                h2 = card.find("h2")
                if h2:
                    name = h2.get_text(strip=True)
                    print(f"Top Card Name: '{name}'")
                    
                    # Reproduce Quality Check Logic
                    print("\n--- Debugging Quality Check ---")
                    brand_lower = brand_name_input.lower()
                    name_lower = name.lower()
                    
                    print(f"Brand Lower: {brand_lower}")
                    print(f"Name Lower: {name_lower}")
                    
                    if brand_lower not in name_lower:
                        print("Exact match failed.")
                        brand_parts = [b for b in brand_lower.split() if len(b) > 2] # split() only splits by whitespace!
                        print(f"Brand Parts (split by space): {brand_parts}")
                        
                        has_part = any(part in name_lower for part in brand_parts)
                        print(f"Any part found? {has_part}")
                        
                        if not has_part:
                            print("CONCLUSION: Quality Check filtered this product out because the brand name input has hyphens/no spaces.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_extraction_failure()
