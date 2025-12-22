import sys
import io

# Force utf-8 for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from bs4 import BeautifulSoup
import re

def identify_availability(card):
    """
    Identifies availability status from a product card or page.
    """
    text = card.get_text(separator=" ", strip=True).lower()
    
    # Positive signals
    if re.search(r"\bin stock\b", text):
        return "In Stock"
    if re.search(r"\bonly \d+ left\b", text):
        return "Low Stock"
    if re.search(r"\bavailable\b", text):
        return "Available"
        
    # Negative signals
    if re.search(r"\bout of stock\b", text):
        return "Out of Stock"
    if re.search(r"\bcurrently unavailable\b", text):
        return "Unavailable"
    if re.search(r"\bsold out\b", text):
        return "Sold Out"
        
    return "Unknown"

def test_extraction(file_path):
    print(f"Testing {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    soup = BeautifulSoup(html, "html.parser")
    
    # Generic extraction simulation
    products = []
    
    # Try Amazon specific container first if it looks like Amazon (heuristic)
    cards = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
    if cards:
        print(f"Found {len(cards)} Amazon cards.")
        for i, card in enumerate(cards[:3]):
            print(f"--- Amazon Card {i+1} ---")
            text_content = card.get_text(separator=" ", strip=True)
            print(f"Full Text: {text_content[:500]}...") # Print first 500 chars
            
            # Simple regex check for 'Sold by' which is the main target for non-deep scan
            sold_by = re.search(r"(?i)(?:sold by|seller|courtesy of|merchant)[\s:-]+([A-Za-z0-9\s&'\.]+)", text_content)
            if sold_by:
                print(f"Seller (Regex): {sold_by.group(1)}")
            else:
                print("Seller: N/A")
                
            # Availability
            avail = identify_availability(card)
            print(f"Availability: {avail}")

    else:
        # Fallback to generic strategy simulation (finding price nodes)
        print("Using generic strategy...")
        symbols = ['₹', '$', '€', '£', 'Rs', 'USD', 'INR', 'MRP']
        all_text_nodes = soup.find_all(string=True)
        price_nodes = []
        for t in all_text_nodes:
             if t.parent.name in ['script', 'style', 'noscript', 'head', 'meta', 'link', 'title']: continue
             if any(s in str(t) for s in symbols):
                  clean_t = t.strip()
                  if len(clean_t) > 40: continue 
                  price_nodes.append(t)
        
        print(f"Found {len(price_nodes)} potential price nodes.")
        
        seen_parents = set()
        count = 0
        for node in price_nodes:
            parent = node.parent
            card = None
            for _ in range(9): 
                if parent is None or parent.name in ['body', 'html']: break
                if parent.find("a", href=True):
                    card = parent
                    break
                parent = parent.parent
            
            if card and card not in seen_parents:
                seen_parents.add(card)
                count += 1
                if count > 3: break
                
                print(f"--- Generic Card {count} ---")
                text_content = card.get_text(separator=" ", strip=True)
                print(f"Full Text: {text_content[:500]}...")
                
                # Check for "Sold by"
                sold_by = re.search(r"(?i)(?:sold by|seller|courtesy of|merchant)[\s:-]+([A-Za-z0-9\s&'\.]+)", text_content)
                if sold_by:
                    print(f"Seller: {sold_by.group(1)}")
                else:
                    print("Seller: N/A")

                # Availability
                avail = identify_availability(card)
                print(f"Availability: {avail}")

if __name__ == "__main__":
    test_files = [
        "c:\\Users\\Nithya\\Brand Protection\\ebay_test.html",
        "c:\\Users\\Nithya\\Brand Protection\\flipkart_test.html",
        "c:\\Users\\Nithya\\Brand Protection\\nykaa_test.html"
    ]
    for p in test_files:
        test_extraction(p)
