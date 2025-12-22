from bs4 import BeautifulSoup
import re

def normalize_product_data(item, source_domain):
    return item

def extract_from_generic_dom(soup, domain):
    print(f"DEBUG: Starting Generic Extraction for {domain}")
    products = []
    candidate_elements = []
    
    # 1. Identify potential product containers
    for tag in ['div', 'li', 'article', 'span']:
        elements = soup.find_all(tag)
        if not elements: continue
        
        class_groups = {}
        for el in elements:
            classes = " ".join(sorted(el.get('class', [])))
            if not classes: continue 
            if classes not in class_groups: class_groups[classes] = []
            class_groups[classes].append(el)
            
        for cls, group in class_groups.items():
            if len(group) >= 3:
                # print(f"DEBUG: Found group of {len(group)} items with class '{cls}'")
                candidate_elements.extend(group)

    print(f"DEBUG: Total Candidates found: {len(candidate_elements)}")
    
    seen_urls = set()
    
    for i, el in enumerate(candidate_elements[:20]): # Debug first 20
        # print(f"DEBUG: Item {i} Class: {el.get('class')}")
        try:
            # Must have a Link
            link_node = el.find("a", href=True)
            if not link_node: 
                # print("DEBUG: Reject - No Link")
                continue
            
            href = link_node['href']
            if href.startswith(("javascript:", "#")): 
                # print("DEBUG: Reject - Bad Link")
                continue
            
            url = f"https://{domain}{href}" if href.startswith("/") else href
            if url in seen_urls: continue
            
            # Name
            heading = el.find(['h1', 'h2', 'h3', 'h4'])
            if heading:
                name = heading.get_text(strip=True)
            else:
                name = link_node.get_text(strip=True)
            
            if len(name) < 3: 
                # print(f"DEBUG: Reject - Short Name: {name}")
                continue
            
            # Price Signal
            el_text = el.get_text(separator=" ", strip=True)
            has_price_signal = any(c in el_text for c in ['$', '₹', '€', '£', 'Rs', 'USD', 'INR'])
            
            if not has_price_signal:
                # print(f"DEBUG: Reject - No Price Signal in text: {el_text[:50]}...")
                # Nykaa might use special font or image for symbol? Or just "MRP"
                if "MRP" in el_text: # Relax rule for testing
                     pass
                else:
                    continue

            price = "N/A"
            if has_price_signal:
                 price_node = el.find(string=lambda t: t and any(c in str(t) for c in ['$', '₹', '€', '£']))
                 if price_node:
                     price = price_node.strip()
                     
            products.append({
                "name": name,
                "price": price,
                "url": url,
            })
            seen_urls.add(url)
            print(f"DEBUG: ACCEPTED {name}")
                
        except Exception as e:
            print(f"DEBUG: Error {e}")
            continue
            
    print(f"DEBUG: Total Products Extracted: {len(products)}")
    return products

with open("nykaa_test.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

extract_from_generic_dom(soup, "nykaa.com")
