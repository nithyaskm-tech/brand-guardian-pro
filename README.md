# Brand Guardian Pro 🔍

A real-time brand presence monitoring dashboard built with Python and Streamlit.

## Features
- **Multi-Platform Scanning**: Scans Amazon, Nykaa, Flipkart, and eBay.
- **Product Detection**: Extract individual product details (Name, Price, Seller, URL).
- **Stealth Mode**: Uses `curl_cffi` to mimic real browsers and bypass bot detection.
- **Reporting**: Export detailed audit reports in CSV and Excel formats.

## Local Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Deployment within Streamlit Community Cloud (Free)

1. Upload this codebase to a GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub account.
4. Select "New App" and choose this repository.
5. Set the "Main file path" to `app.py`.
6. Click **Deploy**!
