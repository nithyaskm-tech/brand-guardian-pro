from bs4 import BeautifulSoup
import re

def find_seller_patterns(filename, domain):
    print(f"\n--- Searching for SELLER info in {domain} ---")
    with open(filename, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    # Text patterns that usually indicate seller
    keywords = ["sold by", "seller", "store", "brand", "visit the", "by "]
    
    found_nodes = []
    
    for kw in keywords:
        nodes = soup.find_all(string=lambda t: t and kw in str(t).lower())
        for n in nodes[:5]: # Take first few samples
            text = n.strip()
            if len(text) > 50: continue # Ignore long paragraphs
            
            parent = n.parent
            classes = parent.get("class")
            tag = parent.name
            
            print(f"[{kw.upper()}] Found: '{text}' | Tag: <{tag} class='{classes}'>")
            found_nodes.append((tag, classes, text))

find_seller_patterns("nykaa_test.html", "nykaa")
find_seller_patterns("amazon_test_sample.html", "amazon") # I don't have this localized, but logic applies if I had it
find_seller_patterns("flipkart_test.html", "flipkart")
find_seller_patterns("ebay_test.html", "ebay")
