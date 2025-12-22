from bs4 import BeautifulSoup

def inspect_html(filename, domain):
    print(f"--- Inspecting {domain} ---")
    with open(filename, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    if domain == "nykaa":
        # Look for product containers
        # Nykaa usually uses div with class 'product-wrapper' or similar
        # Let's try to find text and see parent
        examples = soup.find_all("div", class_="css-d5z3ro") # Common class saw in past? No, hashes change.
        # Try generic search for item with a price
        products = soup.find_all(attrs={"data-test-id": "product-box"}) # Nykaa often uses data-test-id?
        if not products:
             # Fallback: look for class containing "product"
             products = soup.select("div[class*='productCard']")
        
        print(f"Found {len(products)} potential products")
        if products:
            p = products[0]
            print(f"Sample Classes: {p.get('class')}")
            print(f"Sample Text: {p.get_text()[:100]}")
            
    elif domain == "flipkart":
        # Flipkart usually uses div class="_1AtVbE" for rows, and "_13oc-S" for grid items
        # Or standard div class="_2kHMtA" for list view
        products = soup.find_all("div", class_="_1AtVbE")
        # a more reliable one often is data-id
        products_data_id = soup.find_all(attrs={"data-id": True})
        print(f"Found {len(products_data_id)} items with data-id")
        if products_data_id:
            p = products_data_id[0]
            print(f"Classes: {p.get('class')}")
            # Try to find price
            price = p.find("div", class_="_30jeq3")
            print(f"Price found? {price.get_text() if price else 'No'}")
            name = p.find("div", class_="_4rR01T") # List view title
            if not name: name = p.find("a", class_="s1Q9rs") # Grid view title
            print(f"Name found? {name.get_text() if name else 'No'}")

    elif domain == "ebay":
        # eBay usually s-item
        products = soup.find_all("li", class_="s-item")
        print(f"Found {len(products)} s-items")
        if products:
             p = products[1] # first is usually header
             print(f"Title: {p.find('div', class_='s-item__title').get_text() if p.find('div', class_='s-item__title') else '?'}")
             print(f"Price: {p.find('span', class_='s-item__price').get_text() if p.find('span', class_='s-item__price') else '?'}")

inspect_html("nykaa_test.html", "nykaa")
inspect_html("flipkart_test.html", "flipkart")
inspect_html("ebay_test.html", "ebay")
