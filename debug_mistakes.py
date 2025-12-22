import re

def test_extraction(text, brand_name="Ozone"):
    print(f"--- Testing Text: '{text[:50]}...' ---")
    
    # Current Regex (roughly)
    regex_patterns = [
        r"(?i)(?:sold by|seller|courtesy of|merchant|importer|marketed by)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)",
        r"(?i)(?:brand)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)"
    ]
    
    candidates = []
    for pattern in regex_patterns:
        match = re.search(pattern, text)
        if match:
            cand = match.group(1).strip()
            print(f"Matched Pattern '{pattern}': '{cand}'")
            candidates.append(cand)

    # Simulation of block list logic
    block_list = [
        "amazon", "available", "more buying", "details", 
        "installation", "add to cart", "cart", "warranty",
        "protection", "plan", "service", "get it", "tomorrow",
        "free delivery", "days", "replacement"
    ]
    
    final_seller = "N/A"
    for cand in candidates:
        if 2 < len(cand) < 60:
             # Cleaning
             cand = re.sub(r"(?i)(\d+(\.\d+)?\s?(stars?|ratings?|reviews?))", "", cand).strip()
             
             if any(w in cand.lower() for w in block_list):
                  print(f"Blocked: '{cand}'")
                  continue
             final_seller = cand.title()
             break
    
    print(f"Final Result: {final_seller}\n")

if __name__ == "__main__":
    # Test cases gathered from user feedback
    cases = [
        "Seller who Offers Good Customer Service",
        "Items That You Chose", # Implicitly might not have "Seller" keyword but let's see why it matched
        "Brand: Ozone 30 Litres Fingerprint Safe Locker", # Exploring the "Ozone 30 Litres..." match
        "Sold by Plantex - (Black)",
        "Sold by Plantex (Grey)" 
    ]
    
    for c in cases:
        test_extraction(c)
