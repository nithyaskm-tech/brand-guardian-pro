import re

def test_regex():
    patterns = [
        r"(?i)(?:sold by|seller|courtesy of|merchant)[\s:-]+([A-Za-z0-9\s&'\.]+)",
        r"(?i)(?:brand)[\s:-]+([A-Za-z0-9\s&'\.]+)"
    ]
    
    test_cases = [
        "Sold by: ABC Corp",
        "Sold by TP-Link",
        "Sold by: Seller (India)",
        "Seller: My-Store_123",
        "Sold by  ValidSeller",
        "Merchant: Global Trade Ltd."
    ]
    
    print("--- Current Regex Testing ---")
    for text in test_cases:
        matched = False
        for p in patterns:
            m = re.search(p, text)
            if m:
                print(f"'{text}' -> Match: '{m.group(1)}'")
                matched = True
        if not matched:
            print(f"'{text}' -> NO MATCH")

    # Improvements
    print("\n--- Improved Regex Testing ---")
    improved_patterns = [
        r"(?i)(?:sold by|seller|courtesy of|merchant|importer|marketed by)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),]+)",
        r"(?i)(?:brand)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),]+)"
    ]
    for text in test_cases:
        matched = False
        for p in improved_patterns:
            m = re.search(p, text)
            if m:
                print(f"'{text}' -> Match: '{m.group(1)}'")
                matched = True
        if not matched:
            print(f"'{text}' -> NO MATCH")

if __name__ == "__main__":
    test_regex()
