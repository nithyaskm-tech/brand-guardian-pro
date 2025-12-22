from curl_cffi import requests
from bs4 import BeautifulSoup
import re

def debug_product_page():
    url = "https://www.amazon.in/Canon-Pixma-E470-Inkjet-Printer/dp/B01LAPARWY/ref=sr_1_1?dib=eyJ2IjoiMSJ9.9icwO7RcoixaG0yxKA0E2kdiCZWkeqtJ73uIVjv-D0GViKNf6u44gU9zjRGpK5V5peL4hCCv_G6mQ1a2QSfOleimQm-YYcTp24cuN4sFteCK6MQafNXi224cURAv5p4iwG0-sPk9b4INrEqBSf4uh3Wz0H_coxnMCwuyimOJ2nLQIQSr8cufA9kLVrHJBPn_rztnWXJMP6u3puLfFjbLmbL_7oIJ2faZrh8oSbVMibU.l5f6h69d5MIlf0lJfezJKsx3G93oqupNk1d916pnEzE&dib_tag=se&keywords=Canon%2BPIXMA%2BE470%2BAll%2Bin%2BOne%2B(Print%2C%2BScan%2C%2BCopy)%2BWiFi%2BInk%2BEfficient%2BColour%2BPrinter%2Bfor%2BHome&nsdOptOutParam=true&qid=1766138438&sr=8-1&th=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        print("Fetching product page...")
        response = requests.get(url, impersonate="chrome110", headers=headers, timeout=20)
        print(f"Status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)
        
        # 1. Search for "Clicktech" directly to see if it exists
        if "Clicktech" in text_content:
            print("FOUND 'Clicktech' in plain text!")
            
            # Find context
            index = text_content.find("Clicktech")
            print(f"Context: ...{text_content[index-50:index+50]}...")
        else:
            print("Did NOT find 'Clicktech' in plain text.")
            
        # 2. Check HTML structure for "Sold by"
        # Often in a div id="merchant-info" or inside #tabular-buybox
        merchant_info = soup.find(id="merchant-info")
        if merchant_info:
            print(f"Found #merchant-info: {merchant_info.get_text(strip=True)}")
        else:
             print("Did NOT find #merchant-info")

        # 3. Check for tabular buybox (common in new Amazon layouts)
        tabular = soup.select_one("#tabular-buybox .merchant-info-value")
        if tabular:
             print(f"Found Tabular Merchant: {tabular.get_text(strip=True)}")
             
        # 4. Dump HTML snippet around "Sold by" if found
        sold_by = soup.find(string=re.compile("Sold by", re.IGNORECASE))
        if sold_by:
            print(f"Found 'Sold by' Text Node. Parent: {sold_by.parent}")
            print(f"Parent HTML: {sold_by.parent.prettify()[:500]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_product_page()
