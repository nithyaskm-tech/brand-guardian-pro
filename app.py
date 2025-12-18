import streamlit as st
import pandas as pd
from curl_cffi import requests
import extruct
from bs4 import BeautifulSoup
import time
import json
import io
from urllib.parse import quote, urlparse

# --- Configuration & Constants ---
DEFAULT_DOMAINS = [
    "amazon.com",
    "nykaa.com",
    "flipkart.com",
    "ebay.com"
]

ST_PAGE_CONFIG = {
    "page_title": "Brand Presence Monitor",
    "page_icon": "🔍",
    "layout": "wide"
}

# --- Helper Functions ---

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

def extract_from_json_ld(json_ld, domain):
    """
    Extracts product list from Schema.org ItemList or Product definitions.
    """
    products = []
    
    def parse_single_product(node):
        # Flatten Schema.org product object
        name = node.get("name")
        image = node.get("image")
        url = node.get("url")
        
        # Offers (Price/Availability)
        offers = node.get("offers", {})
        # Offers can be a list or dict
        if isinstance(offers, list) and offers:
            offers = offers[0] # Take first offer
        
        price = offers.get("price")
        currency = offers.get("priceCurrency")
        availability = offers.get("availability", "").replace("http://schema.org/", "")
        
        seller = offers.get("seller", {}).get("name") if isinstance(offers.get("seller"), dict) else "N/A"
        
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

def extract_from_dom_amazon(soup, domain):
    """
    Fallback: Scrapes Amazon-specific search result cards.
    """
    products = []
    items = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
    
    for item in items:
        try:
            # Title
            title_node = item.find("h2")
            name = title_node.get_text(strip=True) if title_node else "Unknown"
            
            # Link
            link_node = item.find("a", class_="a-link-normal")
            url = f"https://{domain}{link_node['href']}" if link_node and link_node.get('href', '').startswith('/') else "N/A"
            
            # Price
            price_whole = item.find("span", class_="a-price-whole")
            price_fraction = item.find("span", class_="a-price-fraction")
            price = "N/A"
            if price_whole:
                price = price_whole.get_text(strip=True) + (price_fraction.get_text(strip=True) if price_fraction else "")
            
            # Seller / Store Retrieval (Best Effort)
            # Amazon usually displays "by [Brand]" or "Visit the [Store]"
            seller = "N/A"
            
            # Case 1: "by BrandName"
            by_line = item.find("span", class_="a-size-base-plus") 
            if not by_line:
                # Look for the row with secondary color which often holds "by ..."
                rows_secondary = item.find_all(class_="a-color-secondary")
                for row in rows_secondary:
                    txt = row.get_text(strip=True)
                    if txt.lower().startswith("by ") or "store" in txt.lower():
                        seller = txt
                        break
            else:
                seller = by_line.get_text(strip=True)

            products.append(normalize_product_data({
                "name": name,
                "price": price,
                "priceCurrency": "USD", # Assumption/Fallback
                "availability": "In Stock", # Assumption if listed
                "seller": seller, # Now populated
                "url": url,
                "method": "Amazon DOM"
            }, domain))
        except Exception:
            continue
            
    return products

def detect_brand_products(url, brand_name):
    """
    Scans URL and returns a LIST of products found.
    """
    status_summary = "Unknown"
    found_products = []
    details = ""
    
    # Enhanced headers
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(
            url, 
            impersonate="chrome120", 
            headers=headers,
            timeout=20
        )
        
        if response.status_code != 200:
            return {
                "status": "Blocked" if response.status_code in [403, 503] else "Error",
                "details": f"HTTP {response.status_code}",
                "products": []
            }
            
        soup = BeautifulSoup(response.text, 'html.parser')
        domain = urlparse(url).netloc
        
        # 1. Try generic JSON-LD first
        try:
            data = extruct.extract(response.text, base_url=url, syntaxes=['json-ld'])
            json_ld_list = data.get('json-ld', [])
            found_products.extend(extract_from_json_ld(json_ld_list, domain))
        except Exception as e:
            # parsing error ignored
            pass

        # 2. If Amazon/specific, try DOM fallback if JSON-LD was empty
        if not found_products and "amazon" in domain:
            found_products.extend(extract_from_dom_amazon(soup, domain))
            
        # 3. If still empty, check simple text presence for "Not Found" status vs "Text Match" (without product details)
        if not found_products:
             text = soup.get_text(separator=' ', strip=True).lower()
             if brand_name.lower() in text:
                 # Check negative signals
                negative_signals = ["no results found", "did not match any products","0 results for"]
                is_negative = any(ns in text for ns in negative_signals)
                if is_negative:
                    status_summary = "Not Found"
                    details = "No products listed (Negative signal)"
                else:
                    # Found text but no structured products
                    status_summary = "Text Match"
                    details = "Brand name found in text, but individual products could not be parsed."
             else:
                 status_summary = "Not Found"
                 details = "Brand not found in text."
        else:
            status_summary = "Found"
            details = f"Extracted {len(found_products)} products."
            
    except Exception as e:
        return {"status": "Error", "details": str(e), "products": []}

    return {
        "status": status_summary,
        "details": details,
        "products": found_products,
        "scan_url": url
    }

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
            st.session_state.domains_list = DEFAULT_DOMAINS.copy()

        with st.expander("➕ Add Target Domain"):
            new_domain = st.text_input("Domain URL", placeholder="e.g. target.com", label_visibility="collapsed")
            if st.button("Add to List", use_container_width=True):
                if new_domain and new_domain not in st.session_state.domains_list:
                    st.session_state.domains_list.append(new_domain.strip())
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
            st.rerun()

        st.markdown("---")
        if st.button("🔄 Reset Defaults"):
            st.session_state.domains_list = DEFAULT_DOMAINS.copy()
            st.rerun()

    # Main Inputs
    col_input, col_action = st.columns([3, 1])
    with col_input:
        brand_name_input = st.text_input("Brand to Monitor", placeholder="Enter brand name...", label_visibility="collapsed")
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
        elif not st.session_state.domains_list:
            st.error("⚠️ No domains configured.")
        else:
            # Reset
            st.session_state.all_products = []
            st.session_state.scan_summary = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            target_len = len(st.session_state.domains_list)
            
            for i, domain in enumerate(st.session_state.domains_list):
                status_text.caption(f"Scanning {domain}...")
                
                search_url = construct_search_url(domain, brand_name_input)
                result = detect_brand_products(search_url, brand_name_input)
                
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
                    # If no specific products found, add a summary row so it appears in report
                    st.session_state.all_products.append(normalize_product_data({
                        "name": f"Scan Summary: {result['status']}",
                        "price": "-",
                        "seller": "-",
                        "url": result["scan_url"],
                        "method": "Summary Only"
                    }, domain))

                progress_bar.progress((i + 1) / target_len)
                time.sleep(1) # Pacing

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
