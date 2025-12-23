from bs4 import BeautifulSoup
import re
import json

def normalize_product_data(data, domain):
    return data

# --- Copy of function from app.py ---
def extract_from_ebay_dom(soup, domain, brand_name):
    print("DEBUG: Starting eBay extraction...")
    products = []
    # eBay list view or grid view
    # Common container: ul.srp-results or ul.b-list__items_nofooter
    items = soup.select("ul.srp-results > li.s-item, ul.b-list__items_nofooter > li.s-item")
    print(f"DEBUG: Found {len(items)} items using specific select")
    
    if not items:
         # Fallback to children of UL
         ul = soup.select_one("ul.srp-results, ul.b-list__items_nofooter")
         if ul:
             items = ul.find_all("li", recursive=False)
             print(f"DEBUG: Found {len(items)} items as children of result UL")
             for i, item in enumerate(items[:3]):
                 print(f"DEBUG: UL Child {i} classes: {item.get('class')}")

    if not items:
         items = soup.find_all(class_="s-item")
         print(f"DEBUG: Found {len(items)} items using generic class 's-item'")
    
    for i, item in enumerate(items[:5]): # inspect first 5
        try:
            print(f"--- Item {i} ---")
            # Skip "Shop on eBay" pseudo items
            classes = item.get("class", [])
            print(f"Item Tag: {item.name}, Classes: {classes}")

            # Try to find title in various ways
            title_tag = item.select_one(".s-item__title, h3")
            if not title_tag:
                 # Try finding just text?
                 pass
            
            if not title_tag: 
                print("Skipped: No title tag")
                continue
            name = title_tag.get_text(strip=True)
            print(f"Title: {name}")
            if "Shop on eBay" in name: 
                print("Skipped: 'Shop on eBay' in name")
                continue
            
            # Price
            price_tag = item.select_one(".s-item__price")
            price = price_tag.get_text(strip=True) if price_tag else "N/A"
            print(f"Price: {price}")
            
            # Brand check
            if brand_name and brand_name.lower() not in name.lower():
                 print(f"Warning: Brand '{brand_name}' not in title (taking it anyway for debug)")
                 
            products.append({"name": name, "price": price})
        except Exception as e:
            print(f"Error parsing item: {e}")
            continue
        
    return products

def extract_from_hidden_data(soup, domain, brand_name):
    print("DEBUG: Starting Hidden Data extraction...")
    products = []
    
    state_scripts = soup.find_all('script')
    for script in state_scripts:
        if not script.string: continue
        content = script.string
        
        if "window.__PRELOADED_STATE__" in content or "window.__INITIAL_STATE__" in content:
            print("DEBUG: Found State Script")
            try:
                match = re.search(r"window\.__[A-Z_]+__\s*=\s*({.*});?", content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    if json_str.endswith(";"): json_str = json_str[:-1]
                    
                    data = json.loads(json_str)
                    print("DEBUG: JSON Loaded successfully")
                    
                    def find_products_in_state(node, depth=0):
                        found = []
                        if depth > 10: return found # Safety break
                        
                        if isinstance(node, dict):
                             name = node.get('name') or node.get('title')
                             if not name and 'titles' in node and isinstance(node['titles'], dict):
                                  name = node['titles'].get('title')
                             
                             price = node.get('price') or node.get('finalPrice') or node.get('offerPrice') or node.get('displayPrice') or node.get('listingPrice')
                             
                             if not price and 'pricing' in node and isinstance(node['pricing'], dict):
                                  price = node['pricing'].get('finalPrice', {}).get('value') or node['pricing'].get('displayPrice', {}).get('value')
                             
                             if name and price:
                                  # Found one
                                  print(f"DEBUG: Found candidate in JSON: {name[:40]}... Price: {price}")
                                  found.append({"name": name, "price": price})
                                        
                             # Recurse
                             for k, v in node.items():
                                 found.extend(find_products_in_state(v, depth+1))
                                 
                        elif isinstance(node, list):
                            for item in node:
                                found.extend(find_products_in_state(item, depth+1))
                        return found

                    state_products = find_products_in_state(data)
                    print(f"DEBUG: Found {len(state_products)} products in state")
                    products.extend(state_products)
            except Exception as e:
                print(f"DEBUG: Error extracting hidden data: {e}")
                pass
            
    return products

def run_tests():
    # eBay
    try:
        print("\n=== Testing eBay ===")
        with open("ebay_debug.html", "r", encoding="utf-8") as f:
            soup_ebay = BeautifulSoup(f, "html.parser")
        res = extract_from_ebay_dom(soup_ebay, "ebay.com", "Canon")
        print(f"eBay Result Count: {len(res)}")
    except FileNotFoundError:
        print("ebay_debug.html not found")

    # Flipkart
    try:
        print("\n=== Testing Flipkart ===")
        with open("flipkart_debug.html", "r", encoding="utf-8") as f:
            soup_flip = BeautifulSoup(f, "html.parser")
        res = extract_from_hidden_data(soup_flip, "flipkart.com", "Canon")
        print(f"Flipkart Result Count: {len(res)}")
    except FileNotFoundError:
        print("flipkart_debug.html not found")

if __name__ == "__main__":
    run_tests()
