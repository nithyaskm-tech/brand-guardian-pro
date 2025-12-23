from bs4 import BeautifulSoup
import os

def inspect():
    file_path = "nykaa_debug.html"
    if not os.path.exists(file_path):
        print("File not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    target_text = "N°5 EAU DE PARFUM SPRAY"
    print(f"Searching for: {target_text}")
    
    # partial match
    found = soup.find(string=lambda x: x and target_text in x)
    
    if found:
        print("Found Element!")
        current = found.parent
        # Walk up to find the container 'css-1vs468q'
        container = None
        while current:
             if current.name == 'div' and 'css-1vs468q' in current.get('class', []):
                  container = current
                  break
             current = current.parent
             
        if container:
             print(f"Found Container: {container.name} {container.attrs}")
             print("--- Children ---")
             for child in container.find_all(recursive=True):
                  if child.name == 'a':
                       print(f"LINK FOUND: {child.get('href')}")
                  
                  # Also print if it's the image wrapper that might have the link
                  if child.name == 'img':
                       print(f"IMAGE: {child.get('src')}")
                       if child.parent.name == 'a':
                            print(f"  -> Wrapped in A: {child.parent.get('href')}")
        else:
             print("Container css-1vs468q not found in ancestry.")
    else:
        print("Target text not found.")

if __name__ == "__main__":
    inspect()
