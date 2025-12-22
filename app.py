import streamlit as st
import pandas as pd
from curl_cffi import requests
import extruct
from bs4 import BeautifulSoup
import time
import json
import io
import re
from urllib.parse import quote, urlparse
import google.generativeai as genai
import concurrent.futures
import os

# --- Configuration & Constants ---
DEFAULT_DOMAINS = [
    "amazon.com",
    "nykaa.com",
    "flipkart.com",
    "ebay.com"
]

CONFIG_FILE = "domain_config.json"

def load_domains():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_domains(domains):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(domains, f)
    except:
        pass

ST_PAGE_CONFIG = {
    "page_title": "Brand Presence Monitor",
    "page_icon": "🔍",
    "layout": "wide"
}

# --- AI Extraction Logic ---
def extract_with_gemini(text_content, domain, brand_name):
    """
    Uses Google Gemini 1.5 Flash to intelligently extract product data from raw text.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are a product extraction expert. Analyze the following text content from a search result page on {domain} for the brand "{brand_name}".
        
        Extract a list of products that match the brand "{brand_name}".
        Ignore "Sponsored" or "Recommended" items if they are clearly for other brands.
        
        For each product, extract:
        - name: The full product title.
        - price: The price with currency symbol.
        - seller: The name of the seller or store (e.g. "Sold by XYZ", "Visit the ABC Store"). If implied to be the brand itself, use "{brand_name}".
        - url: The product URL (relative or absolute). If not found, use "".
        
        Return ONLY valid JSON in the following format:
        [
            {{
                "name": "Product Name",
                "price": "$100",
                "seller": "Seller Name",
                "url": "/link/to/product"
            }}
        ]
        
        If no products found, return [].
        
        search_result_page_content_start:
        {text_content[:30000]} 
        search_result_page_content_end
        """
        
        response = model.generate_content(prompt)
        text_resp = response.text.strip()
        
        # Clean markdown
        if text_resp.startswith("```json"):
            text_resp = text_resp.replace("```json", "").replace("```", "")
            
        data = json.loads(text_resp)
        normalized = []
        for item in data:
            # Post-process URL
            u = item.get('url', '')
            if u and not u.startswith('http'):
                if u.startswith('/'):
                    u = f"https://{domain}{u}"
                else:
                    u = f"https://{domain}/{u}"
            
            normalized.append(normalize_product_data({
                "name": item.get('name'),
                "price": item.get('price'),
                "seller": item.get('seller', 'N/A'),
                "url": u or f"https://{domain}",
                "method": "AI Vision (Text)"
            }, domain))
            
        return normalized
        
    except Exception as e:
        print(f"Gemini Extraction Error: {e}")
        return []

# --- Helper Functions ---

def construct_search_url(domain, brand_name):
    """
    Dynamically generates the search URL based on the domain.
    """
    brand_encoded = quote(brand_name)
    
    # Ensure protocol
    if not domain.startswith("http"):
        base_url = f"https://{domain}"
    else:
        base_url = domain
    
    # Clean domain for matching
    domain_clean = urlparse(base_url).netloc.lower()
    
    # Domain specific logic
    if "amazon" in domain_clean:
         # Force www for Amazon to reduce redirects/bot checks
        if "www." not in base_url:
            base_url = base_url.replace("://", "://www.")
        return f"{base_url}/s?k={brand_encoded}"
    elif "nykaa" in domain_clean:
        return f"https://www.nykaa.com/search/result/?q={brand_encoded}"
    elif "flipkart" in domain_clean:
         return f"{base_url}/search?q={brand_encoded}"
    elif "ebay" in domain_clean:
        return f"https://www.ebay.com/sch/i.html?_nkw={brand_encoded}"
    else:
        # Default fallback
        return f"{base_url}/search?q={brand_encoded}"

def normalize_product_data(item, source_domain):
    """ Standardize product dict from various sources """
    return {
        "Platform": source_domain,
        "Product Name": item.get("name", "Unknown Product"),
        "Price": item.get("price", "N/A"),
        "Currency": item.get("priceCurrency", ""),
        "Seller": item.get("seller", "N/A"), # Often hard to get on search pages
        "Availability": item.get("availability", "Unknown"), # e.g. InStock
        "Product URL": item.get("url", "N/A"),
        "Detection Method": item.get("method", "Generic")
    }

def extract_from_json_ld(json_ld, domain, brand_name=None):
    """
    Extracts product list from Schema.org ItemList or Product definitions.
    """
    products = []
    
    def parse_single_product(node):
        # Flatten Schema.org product object
        name = node.get("name")
        image = node.get("image")
        url = node.get("url")

        # Brand Filter
        if name and brand_name:
             if brand_name.lower() not in name.lower():
                  brand_parts = [b for b in brand_name.lower().split() if len(b) > 2]
                  if brand_parts and not any(part in name.lower() for part in brand_parts):
                       return # Skip this product

        # Offers (Price/Availability)
        offers = node.get("offers", {})
        # Offers can be a list or dict
        if isinstance(offers, list) and offers:
            offers = offers[0] # Take first offer
        
        price = offers.get("price")
        currency = offers.get("priceCurrency")
        availability = offers.get("availability", "").replace("http://schema.org/", "")
        
        seller = offers.get("seller", {}).get("name") if isinstance(offers.get("seller"), dict) else "N/A"
        
        # Fallback seller from brand name if explicit seller missing
        if seller == "N/A" and brand_name and name and brand_name.lower() in name.lower():
             seller = brand_name.title()
        
        if name:
             products.append(normalize_product_data({
                "name": name,
                "price": price,
                "priceCurrency": currency,
                "availability": availability,
                "seller": seller,
                "url": url,
                "method": "JSON-LD"
             }, domain))

    # Search for ItemList or Direct Products
    # Recursive search helper could be useful but we look for specific types
    def recursive_find_products(node):
        if isinstance(node, dict):
            if node.get("@type") in ["Product", "Offer"]:
                parse_single_product(node)
            # Handle ItemList
            elif node.get("@type") == "ItemList" and "itemListElement" in node:
                for item in node["itemListElement"]:
                    recursive_find_products(item)
                    # Sometimes item is just a wrapper like ListItem with 'item' property
                    if isinstance(item, dict) and "item" in item:
                         recursive_find_products(item["item"])
            else:
                for k, v in node.items():
                    recursive_find_products(v)
        elif isinstance(node, list):
            for item in node:
                recursive_find_products(item)

    recursive_find_products(json_ld)
    return products


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

def identify_seller_from_card(card, domain, brand_name):
    """
    Advanced Logic to identify the Transacting Entity (Seller).
    Priorities:
    1. Text nodes following 'Sold by', 'Merchant', etc.
    2. Hyperlinks to Storefronts/Profiles.
    3. Proximity to Price (implied by card structure).
    """
    seller_candidates = []
    text_nodes = list(card.stripped_strings)
    
    # Regex Extraction (Priority 1 - Visual Scanning)
    # "See through" the page text for common patterns
    full_text = " ".join(text_nodes)
    regex_patterns = [
        # Priority 1: Stop before "and Fulfilled" or similar common separators
        r"(?i)(?:sold by|seller|courtesy of|merchant|importer|marketed by)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+?)(?=\s+(?:and|is|ships|fulfilled|payment)|$)",
        # Priority 2: Standard greedy match (fallback)
        r"(?i)(?:sold by|seller|courtesy of|merchant|importer|marketed by)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)",
        r"(?i)(?:brand)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)"
    ]
    
    for pattern in regex_patterns:
        match = re.search(pattern, full_text)
        if match:
            candidate = match.group(1).strip()
            # Validation: Seller name shouldn't be too long or garbage
            if 2 < len(candidate) < 60:
                 # Clean up common garbage at the end of strings
                 candidate = re.sub(r"(?i)(\d+(\.\d+)?\s?(stars?|ratings?|reviews?))", "", candidate).strip()
                 # Clean up colors in parentheses (e.g. "(Black)", "(Grey)")
                 candidate = re.sub(r"(?i)\s*\((black|grey|gray|white|blue|red|green|silver|gold)\)", "", candidate).strip()
                 
                 candidate_lower = candidate.lower()
                 
                 # --- FIX for "Seller Name Seller Name Sold by..." and "Name Name" ---
                 # 1. Internal Keyword Cleanup
                 for kw in ["sold by", "ships from", "distributed by"]:
                      if kw in candidate_lower:
                           idx = candidate_lower.find(kw)
                           if idx > 2: # Ignore if it's at the very start
                                candidate = candidate[:idx].strip()
                                candidate_lower = candidate.lower()
                                
                 # 2. Deduplication check (e.g. "Cocoblu Retail Cocoblu Retail")
                 words = candidate.split()
                 if len(words) >= 4 and len(words) % 2 == 0:
                      mid = len(words) // 2
                      first_half = " ".join(words[:mid])
                      second_half = " ".join(words[mid:])
                      if first_half.lower() == second_half.lower():
                           candidate = first_half
                           candidate_lower = candidate.lower() # update
                 
                 # 0. WORD COUNT CHECK (Sellers are rarely > 6 words, Titles are long)
                 if len(candidate.split()) > 6:
                      continue

                 # 1. START-OF-STRING BLOCKERS (Garbage text phrases)
                 if candidate_lower.startswith(("who offers", "that you chose", "items that", "customers who", "ozone")):
                      # Blocking "Ozone" starting match IF it's long (likely a title), but allow if short (official seller)
                      if "ozone" in candidate_lower and len(candidate.split()) > 3:
                           continue
                      if candidate_lower.startswith(("who offers", "that you chose", "items that", "customers who")):
                           continue

                 # 2. SUBSTRING BLOCKERS (Common non-seller keywords)
                 # Note: "plan" matching "Plantex" and "protection" matching generally. "protection plan" is safer.
                 block_list_substrings = [
                     "amazon", "available", "more buying", "details", 
                     "installation", "add to cart", "warranty",
                     "protection plan", "service", "get it", "tomorrow",
                     "free delivery", "days", "replacement", "dispatched",
                     "customer service", "that you chose", "often"
                 ]
                 
                 if any(w in candidate_lower for w in block_list_substrings):
                      continue
                      
                 # 3. EXACT WORD BLOCKERS (Strict blocking for short common words)
                 block_list_exact = ["cart", "plan", "here", "brand", "unknown"]
                 if candidate_lower in block_list_exact:
                      continue

                 return candidate.title()
    
    # Text Analysis (Priority 2)
    seller_triggers = [
        "sold by", "merchant", "importer", "vendor", "shop name", 
        "fulfilled by", "distributed by", "dispatcher", "by "
    ]
    
    # text_nodes already defined above
    
    for i, text in enumerate(text_nodes):
        text_lower = text.lower()
        
        # 0. Direct Brand Match (DTC/Brand Check)
        # If the brand name appears in a short text node (likely a label), assume Brand is Seller
        if brand_name and len(text) < 50:
             # Check for "By [Brand]" or just "[Brand]"
             if text_lower == brand_name.lower() or text_lower == f"by {brand_name.lower()}":
                 return brand_name.title()
             # If brand name is in the text but not exact match, check if it looks like a brand label
             if brand_name.lower() in text_lower:
                  # Avoid catching the Title as the Seller
                  # Heuristic: If text is short and contains brand, it might be "Visit the Chanel Store" or "Brand: Chanel" being split
                  if "brand" in text_lower:
                       return brand_name.title()

        for trigger in seller_triggers:
            if trigger in text_lower:
                # Case A: "Sold by: SellerName"
                if len(text) > len(trigger) + 2:
                    candidate = text_lower.split(trigger)[-1].strip(": -").title()
                # Case B: "Sold by" ...next node... "SellerName" (handled in next iteration effectively)
                elif i + 1 < len(text_nodes):
                    candidate = text_nodes[i+1].strip()
                else:
                    candidate = None
                
                if candidate:
                    # Clean garbage again
                    candidate = re.sub(r"(?i)(\d+(\.\d+)?\s?(stars?|ratings?|reviews?))", "", candidate).strip()
                    if len(candidate) > 60: continue 
                    # Filter out platform names UNLESS they are explicitly the seller (e.g. "Sold by Amazon")
                    # If text says "Sold by Amazon", we KEEP it.
                    # The previous logic excluded them. User wants "Transacting Entity".
                    # If valid name, return it.
                    return candidate


    # Link Analysis (Priority 3)
    links = card.find_all("a", href=True)
    main_link_href = None
    if links: main_link_href = links[0]['href']
        
    for link in links:
        href = link['href']
        text = link.get_text(strip=True)
        if not text: continue
        
        if href == main_link_href: continue
        
        # Heuristics for seller links (Generic + Specific Platforms)
        href_lower = href.lower()
        
        # eBay users/stores
        if "ebay" in domain and ("/usr/" in href_lower or "/str/" in href_lower):
             return text
             
        # Amazon stores
        if "amazon" in domain and ("/ws/" in href_lower or "/stores/" in href_lower):
             return text
             
        # Generic "Store" links
        if "store" in text.lower() or "seller" in href_lower or "profile" in href_lower or "shop" in href_lower:
            clean_text = text.replace("Visit the", "").replace("Store", "").strip()
            return clean_text
            
    # Final Fallback: If we assume DTC (Direct to Consumer) site structure
    # The domain itself might be the seller if no other info found
    # But for marketplaces (Amazon/eBay), we return N/A if we can't find a 3rd party
    # Final Fallback: If we assume DTC (Direct to Consumer) site structure
    if brand_name and brand_name.lower() in domain:
        return brand_name.title()

    # User Request: Explicitly attribute to Brand if brand name appears in text
    # This acts as a catch-all to prevent "N/A" when the brand is mentioned.
    if brand_name:
         # Check if brand name is in the full text of the card
         full_text = " ".join(text_nodes).lower()
         if brand_name.lower() in full_text:
              return brand_name.title()

    return "N/A"

def extract_from_generic_dom(soup, domain, brand_name):
    """
    Universal Extractor
    """
    products = []
    seen_urls = set()
    
    # Currency symbols to look for
    symbols = ['₹', '$', '€', '£', 'Rs', 'USD', 'INR', 'MRP']
    
    # Secure Text Node Finding: Ignore Scripts/Styles
    all_text_nodes = soup.find_all(string=True)
    price_nodes = []
    
    for t in all_text_nodes:
         if t.parent.name in ['script', 'style', 'noscript', 'head', 'meta', 'link', 'title']: continue
         if any(s in str(t) for s in symbols):
              clean_t = t.strip()
              # Heuristic: Price text shouldn't be too long or look like code
              if len(clean_t) > 40: continue 
              if any(bad in clean_t for bad in ['{', '}', ';', 'var ', 'function', '=']): continue
              price_nodes.append(t)
    
    for node in price_nodes:
        try:
            # Walk up to find a container with a link
            parent = node.parent
            card = None
            for _ in range(7): # Reduced range to avoid grabbing too big containers
                if parent is None or parent.name in ['body', 'html', 'header', 'footer', 'nav', 'aside']: break
                # Check if this container looks like a header or extraneous section
                cls = " ".join(parent.get("class", [])).lower()
                if "header" in cls or "menu" in cls or "search-summary" in cls or "filter" in cls:
                    break
                    
                if parent.find("a", href=True):
                    card = parent
                    break
                parent = parent.parent
            
            if not card: continue
            
            # Validation: Product Name Validation
            raw_title = link_node.get_text(separator=" ", strip=True)
            
            # --- Robust Title Cleaning ---
            # 1. Check for Search Header patterns in Title
            # e.g. "adidas (537K results)", "50 items found"
            clean_title_lower = raw_title.lower()
            if "results" in clean_title_lower or "items found" in clean_title_lower:
                  continue
                  
            # Filter out generic link texts
            if len(raw_title) < 4 or raw_title.lower() in ["view", "details", "shop now", "click here", "buy now"]:
                 # Try to find a better title in the card (e.g. h2, h3 or img alt)
                 title_tag = card.find(['h2', 'h3', 'h4'])
                 if title_tag:
                      candidate_title = title_tag.get_text(strip=True)
                      # Validate candidate title too
                      if "results" not in candidate_title.lower():
                           raw_title = candidate_title
                 else:
                      img = card.find('img', alt=True)
                      if img: raw_title = img['alt']

            # Double check title after fallback
            if "results" in raw_title.lower() or "items found" in raw_title.lower():
                 continue

            # 2. Container Safety Check
            # If the 'card' text contains "Sort By", "Filter", "Refine", it's likely the whole page wrapper, NOT a product card.
            card_text = card.get_text(separator=" ", strip=True).lower()
            if any(x in card_text for x in ["sort by:", "filter by", "refine search", "relevant matches"]):
                 # Use a stricter heuristic: The card text shouldn't be HUGE
                 if len(card_text) > 2000: 
                      continue
            
            href = link_node['href']
            
            href = link_node['href']
            if href.startswith(("javascript:", "#")): continue
            url = f"https://{domain}{href}" if href.startswith("/") else href
            
            if url in seen_urls: continue
            
            name = link_node.get_text(strip=True)
            if len(name) < 3:
                    h_tag = card.find(['h1','h2','h3','h4'])
                    if h_tag: name = h_tag.get_text(strip=True)
            if len(name) < 3: continue

            # Quality Check: Name matches Brand
            # This prevents capturing "Recommended" or "Ad" items inconsistent with search
            if brand_name and brand_name.lower() not in name.lower():
                 # Fuzzy fallback: If multi-word brand (e.g. "Hugo Boss"), check if at least one main part exists
                 brand_parts = [b for b in brand_name.lower().split() if len(b) > 2]
                 if brand_parts and not any(part in name.lower() for part in brand_parts):
                      continue


            price = node.strip()
            
            # Identify Seller with Domain+Brand context
            seller = identify_seller_from_card(card, domain, brand_name)
            availability = identify_availability(card)
            
            products.append(normalize_product_data({
                "name": name,
                "price": price,
                "seller": seller,
                "availability": availability,
                "url": url,
                "method": "Generic Bottom-Up"
            }, domain))
            seen_urls.add(url)
        except: continue

    return products

def detect_brand_products(url, brand_name, deep_scan=False):
    """
    Scans URL and returns a LIST of products found.
    Generic implementation for ANY website.
    """
    status_summary = "Unknown"
    found_products = []
    details = ""
    
    # Generic "Real User" Headers
    # Randomized standard user agents are handled by impersonate, but extra headers help
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }

    # Implement Retry/Rotation for robust connections
    # Use newer browser versions for better impersonation success
    impersonate_profiles = ["chrome120", "chrome110", "safari15_3", "edge101"]
    
    # Special Handling for known tough sites (Depop, etc)
    if "depop" in url:
         headers["Referer"] = "https://www.depop.com/"
         headers["Origin"] = "https://www.depop.com"

    response = None
    last_error = None

    for profile in impersonate_profiles:
        try:
            response = requests.get(
                url, 
                impersonate=profile, 
                headers=headers,
                timeout=20
            )
            if response.status_code == 200:
                break # Success
        except Exception as e:
            last_error = e
            time.sleep(1) # Brief pause before retry
            continue
    
    if not response or response.status_code != 200:
        error_details = f"HTTP {response.status_code}" if response else str(last_error)
        return {
            "status": "Blocked/Error",
            "details": f"Failed after retries: {error_details}",
            "products": [],
            "scan_url": url
        }
            
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        domain = urlparse(url).netloc
        text_content = soup.get_text(separator=' ', strip=True).lower()

        # 0. Early Negative Signal Check
        # If the page explicitly says "No results", stop immediately to avoid scraping "Recommendations"
        # Use regex to avoid false positives like "1,000 results for" matching "0 results for"
        negative_signals = [
            r"no results found", 
            r"did not match any products", 
            r"\b0 results for", 
            r"we couldn't find any results",
            r"nothing matches your search"
        ]
        
        if any(re.search(ns, text_content) for ns in negative_signals):
             return {
                "status": "Not Found",
                "details": "Page explicitly states no results found.",
                "products": [],
                "scan_url": url
            }
            
        # --- AI Simplification ---
        # If API Key is present, use AI to parse text instead of complex DOM logic
        if st.session_state.get("google_api_key"):
             ai_products = extract_with_gemini(text_content, domain, brand_name)
             if ai_products:
                  return {
                    "status": "Found (AI)",
                    "details": f"AI Extracted {len(ai_products)} products.",
                    "products": ai_products,
                    "scan_url": url
                }
             # If AI fails, fall back to standard logic below
             
        # 1. Strategy A: Structured Data (JSON-LD)
        try:
            data = extruct.extract(response.text, base_url=url, syntaxes=['json-ld'])
            json_ld_list = data.get('json-ld', [])
            found_products.extend(extract_from_json_ld(json_ld_list, domain, brand_name))
        except Exception:
            pass

        if not found_products:
             found_products.extend(extract_from_amazon_containers(soup, domain, brand_name))

        # 2. Strategy B: Generic DOM Clustering / Bottom Up (Combined)
        if not found_products:
             # Scan using generic methods, passing brand name for better context
             found_products.extend(extract_from_generic_dom(soup, domain, brand_name))

        # 3. Strategy C: Text Fallback (Status determination only)
        if not found_products:
              # For long search queries, exact match of the whole string usually fails.
              # Check for token overlap instead.
              tokens = [t for t in brand_name.lower().split() if len(t) > 2]
              token_match = False
              if tokens:
                   # If significant number of tokens are present
                   present_count = sum(1 for t in tokens if t in text_content)
                   if present_count / len(tokens) >= 0.5: # 50% match
                        token_match = True
              elif brand_name.lower() in text_content:
                   token_match = True

              if token_match:
                    status_summary = "Text Match"
                    details = "Brand name/tokens found in text, but product cards could not be identified automatically."
              else:
                  status_summary = "Not Found"
                  details = "Brand name not found in visible text."
        else:
            status_summary = "Found"
            details = f"Extracted {len(found_products)} products."
            
            # --- Deep Scan Logic (Parallelized) ---
            if deep_scan and found_products:
                 # Filter items that need scanning (N/A or Brand Name placeholders)
                 # Limit to top 50 to allow thorough checking without waiting forever
                 candidates_indices = []
                 for i, p in enumerate(found_products[:50]):
                      if p["Seller"] == "N/A" or p["Seller"] == brand_name.title():
                           if "http" in p["Product URL"]:
                                candidates_indices.append(i)
                 
                 details += f" [Deep Scan: Processing {len(candidates_indices)} items...]"
                 
                 def process_item(index):
                      try:
                           p = found_products[index]
                           new_seller = fetch_product_details(p["Product URL"], brand_name)
                           return index, new_seller
                      except:
                           return index, "N/A"

                 # Run in parallel to speed up
                 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                      future_to_index = {executor.submit(process_item, i): i for i in candidates_indices}
                      for future in concurrent.futures.as_completed(future_to_index):
                           idx, seller_result = future.result()
                           if seller_result and seller_result != "N/A":
                                found_products[idx]["Seller"] = seller_result
            
    except Exception as e:
        return {"status": "Error", "details": str(e), "products": [], "scan_url": url}

    return {
        "status": status_summary,
        "details": details,
        "products": found_products,
        "scan_url": url
    }

def fetch_product_details(product_url, brand_name):
    """
    Visits the product page to find the seller.
    """
    try:
        # Same headers/impersonation
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = requests.get(product_url, impersonate="chrome110", headers=headers, timeout=10)
        if response.status_code != 200: return "N/A"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # We can reuse the identify_seller_from_card logic, but passing the whole body
        # Since identify_seller_from_card relies on stripped_strings, it should work on body too
        # However, for efficiency, let's target common boxes
        
        domain = urlparse(product_url).netloc

        # 1. Target Specific Boxes (Amazon)
        # Check standard merchant info box
        buybox = soup.find(id="merchant-info")
        if buybox:
             seller = identify_seller_from_card(buybox, domain, brand_name)
             if seller != "N/A": return seller

        # Check Tabular Buybox (common in some layouts)
        tabular = soup.find(id="tabular-buybox")
        if tabular:
             seller = identify_seller_from_card(tabular, domain, brand_name)
             if seller != "N/A": return seller
        
        # Check "fresh-merchant-info" or similar specific IDs
        for bid in ["fresh-merchant-info", "n3_buybox", "buybox-see-all-buying-choices-announce"]:
             box = soup.find(id=bid)
             if box:
                  seller = identify_seller_from_card(box, domain, brand_name)
                  if seller != "N/A": return seller

        # 2. Generic: Scan Full Body Content (Fallback)
        # Using the ROBUST function instead of custom regex loop
        # We pass the body tag to reuse the same iterator/validation logic
        if soup.body:
             seller = identify_seller_from_card(soup.body, domain, brand_name)
             if seller != "N/A": return seller

        return "N/A"
    except:
        return "N/A"

def extract_from_amazon_containers(soup, domain, brand_name):
    """
    Dedicated strategy for Amazon search results using reliable data attributes.
    """
    products = []
    # Search for standard result containers
    cards = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
    
    for card in cards:
        try:
            # Title extraction:
            # 1. Try finding link inside h2 (standard)
            # 2. Try identifying 'a-text-normal' link (often used for titles)
            title_node = None
            link_node = None
            
            # Strategy 1: Link inside H2
            h2_candidates = card.find_all("h2")
            for h2 in h2_candidates:
                possible_link = h2.find("a", href=True)
                if possible_link:
                    link_node = possible_link
                    break
            
            # Strategy 2: Look for standard title class if H2 failed
            if not link_node:
                 link_node = card.find("a", class_=lambda x: x and "a-text-normal" in x, href=True)
            
            # Strategy 3: Look for link containing span with a-text-normal
            if not link_node:
                 span_text = card.find("span", class_=lambda x: x and "a-text-normal" in x)
                 if span_text and span_text.parent.name == "a":
                      link_node = span_text.parent

            if not link_node: continue
            
            name = link_node.get_text(strip=True)
            if len(name) < 5: continue # Too short to be a title

            href = link_node['href']
            url = f"https://{domain}{href}" if href.startswith("/") else href
            
            # Quality Check: Name matches Brand (borrowed from generic)
            if brand_name:
                 # Normalize brand name: remove hyphens/slugs to ensure tokens match
                 brand_clean = brand_name.lower().replace("-", " ").replace("_", " ")
                 name_clean = name.lower()
                 
                 if brand_clean not in name_clean:
                      brand_parts = [b for b in brand_clean.split() if len(b) > 2]
                      if brand_parts and not any(part in name_clean for part in brand_parts):
                           continue

            # Price extraction (look for a-price)
            price = "N/A"
            price_node = card.find(class_="a-price")
            if price_node:
                offscreen = price_node.find(class_="a-offscreen")
                if offscreen:
                    price = offscreen.get_text(strip=True)
                else:
                    price = price_node.get_text(separator="", strip=True) 
            
            # Seller identification
            seller = identify_seller_from_card(card, domain, brand_name)
            availability = identify_availability(card)
            
            products.append(normalize_product_data({
                "name": name,
                "price": price,
                "seller": seller,
                "availability": availability,
                "url": url,
                "method": "Amazon Structure"
            }, domain))
        except:
            continue
            
    return products

# --- Main App ---

def main():
    st.set_page_config(**ST_PAGE_CONFIG)
    
    # --- Advanced Custom CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .main-header {
            background: linear-gradient(135deg, #FF6B6B 0%, #556270 100%);
            padding: 2rem;
            border-radius: 12px; color: white; margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .main-header h1 { margin: 0; font-size: 2.2rem; font-weight: 700; }
        .result-card {
            background-color: #ffffff; border: 1px solid #e0e0e0;
            border-radius: 10px; padding: 1.5rem; margin-bottom: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .badge-found { background-color: #d1fae5; color: #065f46; border: 1px solid #34d399; padding: 4px 12px; border-radius: 20px; font-weight:600;}
        .badge-blocked { background-color: #fee2e2; color: #991b1b; border: 1px solid #f87171; padding: 4px 12px; border-radius: 20px; font-weight:600;}
        .badge-missing { background-color: #f3f4f6; color: #374151; border: 1px solid #d1d5db; padding: 4px 12px; border-radius: 20px; font-weight:600;}
        .stButton button.primary-btn { background-color: #FF4B4B; color: white; font-size: 1.1rem; padding: 0.75rem 0; }
        </style>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="main-header">
        <h1>🔍 Brand Guardian Pro</h1>
        <p>Real-time Brand Presence Scanning & Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### 🛠️ Configuration Panel")
        if "domains_list" not in st.session_state:
            saved = load_domains()
            st.session_state.domains_list = saved if saved else DEFAULT_DOMAINS.copy()

        with st.expander("➕ Add Target Domain"):
            new_domain = st.text_input("Domain URL", placeholder="e.g. target.com", label_visibility="collapsed")
            if st.button("Add to List", use_container_width=True):
                if new_domain and new_domain not in st.session_state.domains_list:
                    st.session_state.domains_list.append(new_domain.strip())
                    save_domains(st.session_state.domains_list)
                    st.rerun()

        st.markdown(f"**Active Targets ({len(st.session_state.domains_list)})**")
        domains_to_remove = []
        for domain in st.session_state.domains_list:
            c1, c2 = st.columns([0.85, 0.15])
            c1.caption(f"🌐 {domain}")
            if c2.button("×", key=f"del_{domain}"):
                domains_to_remove.append(domain)
        if domains_to_remove:
            for d in domains_to_remove:
                st.session_state.domains_list.remove(d)
            save_domains(st.session_state.domains_list)
            st.rerun()

        st.markdown("---")
        with st.expander("🤖 AI Settings (Optional)"):
             google_key = st.text_input("Gemini API Key", type="password", key="google_api_key_input")
             if google_key:
                  st.session_state.google_api_key = google_key
             st.caption("AI extraction simplifies parsing and handles complex sites better.")

        if st.button("🔄 Reset Defaults"):
            st.session_state.domains_list = DEFAULT_DOMAINS.copy()
            save_domains(st.session_state.domains_list)
            st.rerun()

    # Main Inputs
    col_input, col_action = st.columns([3, 1])
    with col_input:
        brand_name_input = st.text_input("Brand to Monitor", placeholder="Enter brand name...", label_visibility="collapsed")
        deep_scan_mode = st.checkbox("Enable Deep Scan (Slower, visits product pages)", value=False, help="Checking this will visit the top 3 product pages individually to find the 'Sold by' information, which is often hidden on the search results page.")
    with col_action:
        start_btn = st.button("🚀 Start Scan", type="primary", use_container_width=True)

    # Initialize State
    if "all_products" not in st.session_state:
        st.session_state.all_products = [] # List of all product dicts
    if "scan_summary" not in st.session_state:
        st.session_state.scan_summary = [] # High level summaries

    if start_btn:
        if not brand_name_input:
            st.warning("⚠️ Enter a brand name.")
        elif "http" in brand_name_input or "/" in brand_name_input:
             st.error("⚠️ It looks like you entered a URL. Please enter a **Brand Name** (e.g., 'Canon') to monitor.")
        elif not st.session_state.domains_list:
            st.error("⚠️ No domains configured.")
        else:
            # Reset
            st.session_state.all_products = []
            st.session_state.scan_summary = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            target_len = len(st.session_state.domains_list)
            
            status_text = st.empty()
            target_len = len(st.session_state.domains_list)
            
            # Helper for parallel execution
            def scan_domain(domain):
                # UI updates not allowed in thread
                search_url = construct_search_url(domain, brand_name_input)
                return {
                    "domain": domain, 
                    "result": detect_brand_products(search_url, brand_name_input, deep_scan=deep_scan_mode)
                }

            # Parallel Execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                completed_count = 0
                futures = {executor.submit(scan_domain, d): d for d in st.session_state.domains_list}
                
                for future in concurrent.futures.as_completed(futures):
                    data = future.result()
                    domain = data["domain"]
                    result = data["result"]
                    
                    completed_count += 1
                    status_text.caption(f"Finished {domain} ({completed_count}/{target_len})")
                    progress_bar.progress(completed_count / target_len)
                    
                    # Store Summary
                    st.session_state.scan_summary.append({
                        "Domain": domain,
                        "Status": result["status"],
                        "Details": result["details"],
                        "URL": result["scan_url"],
                        "ProductCount": len(result["products"])
                    })
                    
                    # Store Products
                    if result["products"]:
                        st.session_state.all_products.extend(result["products"])
                    else:
                        st.session_state.all_products.append(normalize_product_data({
                            "name": f"Scan Summary: {result['status']}",
                            "price": "-",
                            "seller": "-",
                            "url": result["scan_url"],
                            "method": "Summary Only"
                        }, domain))

            progress_bar.empty()
            status_text.empty()
            st.success(f"🎉 Scan Complete for **{brand_name_input}**")

    # --- Results Dashboard ---
    if st.session_state.scan_summary:
        st.markdown("### 📊 Scan Summary")
        
        # Calculate Metrics
        total_prods = len([p for p in st.session_state.all_products if p["Detection Method"] != "Summary Only"])
        blocked_cnt = len([s for s in st.session_state.scan_summary if s["Status"] == "Blocked"])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Domains Scanned", len(st.session_state.scan_summary))
        m2.metric("Total Products Found", total_prods)
        m3.metric("Blocked/Errors", blocked_cnt)
        
        st.markdown("### 🕵️ Platform Overview")
        for summary in st.session_state.scan_summary:
             badge_class = "badge-missing"
             icon = "⚪"
             if summary["Status"] == "Found": 
                 badge_class = "badge-found"
                 icon = "✅"
             elif summary["Status"] == "Blocked": 
                 badge_class = "badge-blocked"
                 icon = "⛔"
                 
             st.markdown(f"""
            <div class="result-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; font-size:1.1rem; color:#333;">{summary['Domain']}</span>
                        <br>
                        <span style="font-size:0.85rem; color:#666;">🔗 <a href="{summary['URL']}" target="_blank" style="color:#556270; text-decoration:none;">View Search Page</a></span>
                    </div>
                    <div style="text-align:right;">
                        <span class="{badge_class}">{icon} {summary['Status']}</span>
                        <div style="margin-top:5px; font-size:0.9rem; font-weight:bold; color:#555;">{summary['ProductCount']} products found</div>
                    </div>
                </div>
                <div style="margin-top:0.8rem; font-size:0.9rem; color:#555;">
                     {summary['Details']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📑 Detailed Product Report")
        
        df_products = pd.DataFrame(st.session_state.all_products)
        st.dataframe(df_products, use_container_width=True)

        col_dl1, col_dl2 = st.columns(2)
        
        # CSV
        csv = df_products.to_csv(index=False).encode('utf-8')
        col_dl1.download_button("📥 Download CSV", csv, "brand_products.csv", "text/csv", use_container_width=True, key="csv_dl")
        
        # Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_products.to_excel(writer, index=False, sheet_name='Product Data')
        
        col_dl2.download_button(
            label="📊 Download Excel Report",
            data=buffer.getvalue(),
            file_name="brand_products.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="xlsx_dl"
        )

if __name__ == "__main__":
    main()
