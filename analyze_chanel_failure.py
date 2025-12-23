from bs4 import BeautifulSoup
import re
import json

# --- Helper Functions ---
def normalize_product_data(data, domain):
    return data

def extract_from_ebay_dom(soup, domain, brand_name):
    products = []
    # eBay list view or grid view
    # Common container: ul.srp-results or ul.b-list__items_nofooter
    items = []
    ul = soup.select_one("ul.srp-results, ul.b-list__items_nofooter")
    if ul:
        items = ul.find_all("li", recursive=False)
    
    if not items:
         # Fallback to search all s-item (generic)
         items = soup.find_all(class_="s-item")
    
    print(f"DEBUG: eBay found {len(items)} potential items")
    
    for i, item in enumerate(items[:5]):
        try:
            # Skip "Shop on eBay" pseudo items
            classes = item.get("class", [])
            if "s-item__pl-on-bottom" in classes: continue
            
            # Title
            title_tag = item.select_one(".s-item__title, .s-card__title, h3.s-item__title")
            if not title_tag:
                 # Check first link text
                 link = item.select_one("a")
                 if link and len(link.get_text(strip=True)) > 10:
                      title_tag = link
            
            if not title_tag:
                print(f"Item {i}: No title found")
                continue
            
            name = title_tag.get_text(strip=True)
            print(f"Item {i}: Title Candidate: {name}")
            
            if "Shop on eBay" in name: continue
            
            # Price
            price_tag = item.select_one(".s-item__price, .s-card__price")
            price = price_tag.get_text(strip=True) if price_tag else "N/A"
            print(f"Item {i}: Price: {price}")
            
            products.append(normalize_product_data({
                "name": name,
                "price": price,
                "seller": "N/A",
                "url": "",
                "method": "eBay DOM"
            }, domain))
        except Exception as e:
            print(f"Item {i} Error: {e}")
            continue
        
    return products

def extract_from_hidden_data(soup, domain, brand_name):
    products = []
    state_scripts = soup.find_all('script')
    for script in state_scripts:
        if not script.string: continue
        content = script.string
        
        if "window.__PRELOADED_STATE__" in content or "window.__INITIAL_STATE__" in content:
            try:
                match = re.search(r"window\.__[A-Z_]+__\s*=\s*({.*});?", content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    if json_str.endswith(";"): json_str = json_str[:-1]
                    data = json.loads(json_str)
                    
                    # Debug Keys
                    if 'pageDataV4' in data and 'page' in data['pageDataV4']:
                         pdata = data['pageDataV4']['page']['data']
                         print("Flipkart PageData Keys:", list(pdata.keys()))
                         if '10003' in pdata:
                              print(f"Slot 10003 count: {len(pdata['10003'])}")

                    def find_products_in_state(node, depth=0):
                        found = []
                        if depth > 10: return found
                        if isinstance(node, dict):
                             name = node.get('name') or node.get('title')
                             if not name and 'titles' in node and isinstance(node['titles'], dict):
                                  name = node['titles'].get('title')
                             
                             price = node.get('price') or node.get('finalPrice') or node.get('offerPrice') or node.get('displayPrice') or node.get('listingPrice')
                             if not price and 'pricing' in node and isinstance(node['pricing'], dict):
                                  price = node['pricing'].get('finalPrice', {}).get('value') or node['pricing'].get('displayPrice', {}).get('value')
                             
                             if name and price:
                                  # Loose match for debugging
                                  if "chanel" in name.lower() or "perfume" in name.lower() or True:
                                      found.append({"name": name, "price": price})
                                        
                             for k, v in node.items():
                                 found.extend(find_products_in_state(v, depth+1))
                        elif isinstance(node, list):
                            for item in node:
                                found.extend(find_products_in_state(item, depth+1))
                        return found

                    state_products = find_products_in_state(data)
                    print(f"Found {len(state_products)} hidden state items")
                    if state_products:
                         print("Sample:", state_products[0])
                    products.extend(state_products)
            except Exception as e:
                print(f"Hidden Data Error: {e}")
                pass
    return products

# --- Run Analysis ---
def analyze_live():
    # eBay
    try:
        print("\n--- Analyzing eBay Chanel Live ---")
        with open("ebay_chanel_live.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, 'html.parser')
        res = extract_from_ebay_dom(soup, "ebay", "Chanel")
        print(f"Total eBay extraction: {len(res)}")
    except FileNotFoundError:
        print("ebay_chanel_live.html not found")

    # Flipkart
    try:
        print("\n--- Analyzing Flipkart Chanel Live ---")
        with open("flipkart_chanel_live.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, 'html.parser')
        res = extract_from_hidden_data(soup, "flipkart", "Chanel")
        print(f"Total Flipkart extraction: {len(res)}")
    except FileNotFoundError:
        print("flipkart_chanel_live.html not found")

if __name__ == "__main__":
    analyze_live()
