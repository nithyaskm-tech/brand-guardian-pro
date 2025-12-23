from bs4 import BeautifulSoup
import re
import json

def analyze_flipkart():
    print("--- Analyzing Flipkart ---")
    try:
        with open("flipkart_debug.html", "r", encoding="utf-8") as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and "window.__INITIAL_STATE__" in script.string:
                print("Found State Script")
                # Test App.py Regex
                match = re.search(r"window\.__[A-Z_]+__\s*=\s*({.*});?", script.string)
                if match:
                    print("Regex Match Success!")
                    data_str = match.group(1)
                    if data_str.endswith(";"): data_str = data_str[:-1]
                    try:
                        data = json.loads(data_str)
                        # Inspect pageDataV4
                        if 'pageDataV4' in data and 'page' in data['pageDataV4']:
                             page = data['pageDataV4']['page']
                             # data -> pageDataV4 -> page -> data -> 10002 (slots)
                             if 'data' in page:
                                  print("Keys in pageDataV4.page.data:", list(page['data'].keys()))
                                  # Inspect Slot 10003 (Likely products)
                                  if '10003' in page['data']:
                                       items = page['data']['10003']
                                       if items:
                                            print("\n--- Inspecting Slot 10003 Item 0 ---")
                                            # It has 'childArrangement'. Let's see what's inside.
                                            # Flatten it to find a widget.
                                            def find_widget(node, depth=0):
                                                 if depth > 5: return None
                                                 if isinstance(node, dict):
                                                      if 'widget' in node:
                                                           return node['widget']
                                                      for k, v in node.items():
                                                           res = find_widget(v, depth+1)
                                                           if res: return res
                                                 elif isinstance(node, list):
                                                      for item in node:
                                                           res = find_widget(item, depth+1)
                                                           if res: return res
                                                 return None

                                            widget = find_widget(items[0])
                                            if widget:
                                                 print(f"Found Widget! Type: {widget.get('type')}")
                                                 # Print data keys
                                                 if 'data' in widget:
                                                      print(f"Widget Data Keys: {list(widget['data'].keys())}")
                                                      print(f"Widget Data Sample: {str(widget['data'])[:300]}")
                                            else:
                                                 print("No widget found in Slot 10003 item.")
                        else:
                            print("No pageDataV4 or page key found.")
                            print("Top Keys:", list(data.keys()))

                    except json.JSONDecodeError as e:
                        print(f"JSON Decode Error: {e}")
                else:
                    print("Regex Match FAILED.")
    except Exception as e:
        print(f"Error in Flipkart Analysis: {e}")

def analyze_ebay():
    print("\n--- Analyzing eBay ---")
    try:
        with open("ebay_debug.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, 'html.parser')
            
        # Search for text "Canon" to find a product title
        print("Searching for 'Canon' text nodes...")
        candidates = soup.find_all(string=re.compile("Canon", re.I))
        print(f"Found {len(candidates)} text matches")
        
        for i, text in enumerate(candidates[:5]):
            print(f"\nMatch {i}: {text[:50]}...")
            parent = text.parent
            # Walk up 5 levels
            for level in range(5):
                if not parent: break
                cls = parent.get('class')
                id_ = parent.get('id')
                print(f"  Level {level}: {parent.name} class={cls} id={id_}")
                parent = parent.parent
                
        # Also check if there are ULs with results
        ul = soup.find("ul", class_=re.compile("b-list__items_nofooter|srp-results"))
        if ul:
            print(f"Found Result List UL: {ul.get('class')}")
            print(f"Number of children: {len(ul.find_all('li', recursive=False))}")
            
    except Exception as e:
        print(f"Error in eBay Analysis: {e}")

if __name__ == "__main__":
    analyze_flipkart()
    analyze_ebay()
