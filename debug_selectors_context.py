from bs4 import BeautifulSoup

def find_context(filename, keyword):
    print(f"\n--- Searching '{keyword}' in {filename} ---")
    with open(filename, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    # Find text matching keyword (case insensitive)
    # limit to first match to avoid noise
    elements = soup.find_all(string=lambda text: text and keyword.lower() in text.lower())
    
    for i, text in enumerate(elements[:3]):
        print(f"\nMatch {i+1}:")
        parent = text.parent
        # Go up a few levels to see container
        container = parent
        for _ in range(3):
            if container.parent: container = container.parent
        
        print(f"Parent Tag: {parent.name} | Classes: {parent.get('class')}")
        print(f"Container Tag: {container.name} | Classes: {container.get('class')}")
        # print(f"HTML Snippet: {container.prettify()[:500]}")

find_context("nykaa_test.html", "chanel")
find_context("ebay_test.html", "chanel")
find_context("flipkart_test.html", "samsung")
