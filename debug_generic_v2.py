from bs4 import BeautifulSoup

def extract_bottom_up(soup, domain):
    products = []
    seen_urls = set()
    
    # Symbols to look for
    symbols = ['₹', '$', '€', '£', 'Rs', 'USD', 'INR', 'RP', 'MRP']
    
    # 1. Find all text nodes containing price symbols
    price_nodes = soup.find_all(string=lambda t: t and any(s in str(t) for s in symbols))
    
    print(f"DEBUG: Found {len(price_nodes)} price nodes")
    
    for node in price_nodes:
        # Walk up to find a container that has an anchor tag
        parent = node.parent
        card = None
        
        # Traverse up max 5 levels to find a wrapper with a link
        for _ in range(5):
            if parent is None: break
            if parent.name in ['body', 'html']: break
            
            # Check if this parent has an 'a' tag (could be the parent itself or a child)
            # If parent is 'a', that's great. If parent contains 'a', also good.
            links = parent.find_all("a", href=True)
            if links:
                # Determine if this is a "good" card. 
                # A good card usually shouldn't be the entire page (body/main).
                # It should be relatively small? 
                # Let's just say the first parent that contains a link and is not 'body' is our candidate.
                card = parent
                break
            parent = parent.parent
            
        if not card: continue
        
        # Now extract details from this card
        try:
             # Link
             link_nodes = card.find_all("a", href=True)
             # Heuristic: The main link is often the one with the title or the image. 
             # Let's take the first one or the one with the most text?
             # Usually the first one is the image link or title link.
             target_link = link_nodes[0] 
             href = target_link['href']
             if href.startswith(("javascript:", "#")): continue
             
             url = f"https://{domain}{href}" if href.startswith("/") else href
             if url in seen_urls: continue
             
             # Name
             # Look for Header tags first
             name = ""
             headers = card.find_all(['h1', 'h2', 'h3', 'h4', 'div']) # Divs often used for titles too
             
             # Filter for text length > 5 to avoid "New" "Sale" badges
             potential_names = []
             for h in headers:
                 txt = h.get_text(strip=True)
                 if len(txt) > 5 and len(txt) < 150:
                     potential_names.append(txt)
            
             # Fallback to link text
             if not potential_names:
                 txt = target_link.get_text(strip=True)
                 if len(txt) > 5: potential_names.append(txt)

             name = potential_names[0] if potential_names else "Unknown Product"
             
             # Price
             price = node.strip()
             
             products.append({
                 "name": name,
                 "price": price,
                 "url": url,
                 "card_html_len": len(str(card)) # rough size check
             })
             seen_urls.add(url)
             
        except Exception as e:
            # print(e)
            continue
            
    print(f"DEBUG: Extracted {len(products)} products via Bottom-Up")
    for p in products[:3]:
        print(p)

    return products

with open("nykaa_test.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

extract_bottom_up(soup, "nykaa.com")
