import re
import os
import json
import pandas as pd
import numpy as np
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_url(url):
    """
    Validate if the URL is properly formatted and from a supported domain.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not url:
        return False
    
    try:
        # Check if URL format is valid
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # List of supported domains and their shortened versions
        supported_domains = {
            'amazon': ['amazon.com', 'amazon.co', 'amazon.', 'amzn.', 'a.co'],
            'bestbuy': ['bestbuy.com', 'bestbuy.', 'bby.'],
            'walmart': ['walmart.com', 'walmart.', 'wmt.co'],
            'target': ['target.com', 'target.', 'tgt.'],
            'ebay': ['ebay.com', 'ebay.', 'ebaystatic.'],
            'etsy': ['etsy.com', 'etsy.', 'etsy.me'],
            'homedepot': ['homedepot.com', 'homedepot.', 'thd.co'],
            'newegg': ['newegg.com', 'newegg.', 'newegg.ca']
        }
        
        # Check domain and path components
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        full_url = url.lower()
        
        # Special case for Amazon ASINs in URLs
        if re.search(r'[A-Z0-9]{10}', url, re.IGNORECASE):
            # Likely an Amazon URL with ASIN
            for domain_part in supported_domains['amazon']:
                if domain_part in domain:
                    return True
        
        # Check if domain or its parts match any supported domains
        for platform, domains in supported_domains.items():
            for domain_part in domains:
                if domain_part in domain:
                    return True
        
        # Check for common URL patterns in the full URL
        if any(pattern in full_url for pattern in ['/dp/', '/gp/product/', '/product/', 'item=', 'skuid=', '/ip/']):
            return True
        
        return False
    
    except Exception as e:
        logging.error(f"Error validating URL: {str(e)}")
        return False

def extract_product_id(url):
    """
    Extract product name or ID from URL.
    
    Args:
        url (str): Product URL
        
    Returns:
        str: Extracted product name or ID
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # Amazon
        if 'amazon' in parsed.netloc:
            # Try to extract ASIN or product name
            if '/dp/' in path:
                asin = path.split('/dp/')[1].split('/')[0]
                return f"Amazon-{asin}"
            elif '/product/' in path:
                asin = path.split('/product/')[1].split('/')[0]
                return f"Amazon-{asin}"
        
        # Best Buy
        elif 'bestbuy' in parsed.netloc:
            if '/p/' in path:
                name = path.split('/p/')[1].split('/')[0]
                return f"BestBuy-{name}"
        
        # Walmart
        elif 'walmart' in parsed.netloc:
            if '/ip/' in path:
                match = re.search(r'/ip/([^/]+)/(\d+)', path)
                if match:
                    name = match.group(1)
                    return f"Walmart-{name}"
        
        # Target
        elif 'target' in parsed.netloc:
            if '/-/A-' in path:
                pid = path.split('/-/A-')[1].split('/')[0]
                return f"Target-{pid}"
        
        # eBay
        elif 'ebay' in parsed.netloc:
            if '/itm/' in path:
                match = re.search(r'/itm/([^/]+)/(\d+)', path)
                if match:
                    name = match.group(1)
                    return f"eBay-{name}"
        
        # Etsy
        elif 'etsy' in parsed.netloc:
            if '/listing/' in path:
                listing_id = path.split('/listing/')[1].split('/')[0]
                return f"Etsy-{listing_id}"
        
        # Home Depot
        elif 'homedepot' in parsed.netloc:
            pid = path.split('/')[-1]
            if pid.isdigit():
                return f"HomeDepot-{pid}"
        
        # Newegg
        elif 'newegg' in parsed.netloc:
            if '/p/' in path:
                name = path.split('/p/')[1].split('/')[0]
                return f"Newegg-{name}"
            
            # Extract from query parameters
            if 'Item=' in url:
                item = re.search(r'Item=([A-Z0-9]+)', url)
                if item:
                    return f"Newegg-{item.group(1)}"
        
        # Default: use domain and a portion of the path
        domain = parsed.netloc.split('.')[0]
        path_part = path.strip('/').split('/')[0]
        if path_part:
            return f"{domain}-{path_part}"
        else:
            return domain
    
    except Exception as e:
        logging.error(f"Error extracting product ID: {str(e)}")
        # Return a generic name if extraction fails
        return "Product"

def save_data(data, filename, format='json'):
    """
    Save data to a file.
    
    Args:
        data: Data to save (DataFrame or dict)
        filename (str): Filename to save to
        format (str): File format ('json', 'csv', 'excel')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if format == 'json':
            # Convert DataFrame to records if needed
            if isinstance(data, pd.DataFrame):
                data_to_save = data.to_dict('records')
            else:
                data_to_save = data
                
            with open(filename, 'w') as f:
                json.dump(data_to_save, f, indent=2, default=str)
                
        elif format == 'csv':
            if isinstance(data, pd.DataFrame):
                data.to_csv(filename, index=False)
            else:
                pd.DataFrame(data).to_csv(filename, index=False)
                
        elif format == 'excel':
            if isinstance(data, pd.DataFrame):
                data.to_excel(filename, index=False)
            else:
                pd.DataFrame(data).to_excel(filename, index=False)
        
        return True
    
    except Exception as e:
        logging.error(f"Error saving data: {str(e)}")
        return False

def load_data(filename):
    """
    Load data from a file.
    
    Args:
        filename (str): Filename to load from
        
    Returns:
        Data from the file (DataFrame or dict)
    """
    try:
        ext = os.path.splitext(filename)[1].lower()
        
        if ext == '.json':
            with open(filename, 'r') as f:
                return json.load(f)
                
        elif ext == '.csv':
            return pd.read_csv(filename)
            
        elif ext in ['.xlsx', '.xls']:
            return pd.read_excel(filename)
        
        return None
    
    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")
        return None

def format_date(date):
    """
    Format date for display.
    
    Args:
        date: Date to format
        
    Returns:
        str: Formatted date string
    """
    if pd.isna(date):
        return "Unknown"
        
    try:
        if isinstance(date, str):
            date = pd.to_datetime(date)
            
        return date.strftime('%b %d, %Y')
    except Exception:
        return str(date)

def truncate_text(text, max_length=100):
    """
    Truncate text to a maximum length.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        
    Returns:
        str: Truncated text
    """
    if not isinstance(text, str):
        return ""
        
    if len(text) <= max_length:
        return text
        
    return text[:max_length] + "..."
