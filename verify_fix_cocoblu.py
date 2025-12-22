import re

def identify_seller_mock(text, brand_name="Chanel"):
    print(f"\n--- Processing: '{text[:100]}...' ---")
    
    regex_patterns = [
        r"(?i)(?:sold by|seller|courtesy of|merchant|importer|marketed by)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+?)(?=\s+(?:and|is|ships|fulfilled|payment)|$)",
        r"(?i)(?:sold by|seller|courtesy of|merchant|importer|marketed by)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)",
        r"(?i)(?:brand)[\s:-]+([A-Za-z0-9\s&'\.\-\(\),_]+)"
    ]
    
    candidates = []
    
    # regex check
    for p in regex_patterns:
        matches = re.finditer(p, text)
        for m in matches:
            cand = m.group(1).strip()
            print(f"Captured Candidate: '{cand}'")
            candidates.append(cand)
            
    # Trigger check
    triggers = ["sold by", "by "]
    text_lower = text.lower()
    for t in triggers:
         if t in text_lower:
              idx = text_lower.find(t)
              start = idx + len(t)
              # Simulate taking rest of string or next node
              # roughly 20 chars
              cand = text[start:start+30].strip()
              print(f"Trigger '{t}' Candidate: '{cand}'")
              candidates.append(cand)

    final = "N/A"
    for candidate in candidates:
        print(f"Validating: '{candidate}'")
        
        # 0.5. Internal Keyword Cleanup (Fix for "Name Name Sold by...")
        # If the candidate contains "sold by" or "by " inside it (not at start), cut it off.
        lower_c = candidate.lower()
        for kw in ["sold by", "ships from", "dictributed by"]:
             if kw in lower_c:
                  idx = lower_c.find(kw)
                  if idx > 2: # Ignore if it's at the very start
                       candidate = candidate[:idx].strip()
                       
        # 0.6. Deduplication (Fix for "Cocoblu Retail Cocoblu Retail")
        # Check if the string consists of the same substring repeated
        words = candidate.split()
        if len(words) >= 4 and len(words) % 2 == 0:
             mid = len(words) // 2
             first_half = " ".join(words[:mid])
             second_half = " ".join(words[mid:])
             if first_half.lower() == second_half.lower():
                  candidate = first_half

        # Recalculate length after cleanup
        if not (2 < len(candidate) < 60):
            print("-> REJECT: Length")
            continue
            
        # 1. Cleanup
        candidate = re.sub(r"(?i)(\d+(\.\d+)?\s?(stars?|ratings?|reviews?))", "", candidate).strip()
        candidate = re.sub(r"(?i)\s*\((black|grey|gray|white|blue|red|green|silver|gold)\)", "", candidate).strip()
        
        candidate_lower = candidate.lower()
        
        # 2. Word Count
        if len(candidate.split()) > 6:
             print("-> REJECT: Word Count > 6")
             continue
             
        # 3. StartsWith Blockers
        if candidate_lower.startswith(("who offers", "that you chose", "items that", "customers who", "ozone")):
             print("-> REJECT: StartsWith Blocker")
             continue
             
        # 4. Substring Blockers
        block_list_substrings = [
             "amazon", "available", "more buying", "details", 
             "installation", "add to cart", "warranty",
             "protection plan", "service", "get it", "tomorrow",
             "free delivery", "days", "replacement", "dispatched",
             "customer service"
        ]
        if any(w in candidate_lower for w in block_list_substrings):
             print(f"-> REJECT: Substring Blocker ('{next(w for w in block_list_substrings if w in candidate_lower)}')")
             continue
             
        print("-> ACCEPTED")
        final = candidate.title()
        break
        
    return final

if __name__ == "__main__":
    cases = [
        "Sold by Cocoblu Retail and fulfilled by Amazon",
        "Sold by Cocoblu Retail",
        "Items That You Chose",
        "Customers who viewed this item also viewed",
        "Sold by Cocoblu Retail Cocoblu Retail Sold by", # Garbage case
    ]
    
    for c in cases:
        print(f"Result: {identify_seller_mock(c)}")
