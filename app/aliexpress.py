import json
import math
import random
import asyncio
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import httpx
from bs4 import BeautifulSoup
import logging
import re
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_headers() -> Dict[str, str]:
    """Get request headers with random user agent"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Cookie": "aep_usuc_f=site=glo&c_tp=USD&region=US&b_locale=en_US"
    }

async def fetch_with_retry(client: httpx.AsyncClient, url: str, max_retries: int = 3) -> Optional[str]:
    """Fetch URL content with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempting to fetch URL: {url} (attempt {attempt + 1}/{max_retries})")
            
            # Add random delay between attempts
            if attempt > 0:
                delay = random.uniform(2 ** attempt, 2 ** (attempt + 1))
                logger.debug(f"Waiting {delay:.2f} seconds before retry")
                await asyncio.sleep(delay)
            
            response = await client.get(
                url,
                headers=get_headers(),
                follow_redirects=True,
                timeout=httpx.Timeout(30.0, connect=10.0, read=20.0, write=20.0)
            )
            response.raise_for_status()
            
            # Log response info
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            content = response.text
            logger.debug(f"Response content length: {len(content)} characters")
            
            # Save response to file for debugging
            with open("last_response.html", "w", encoding="utf-8") as f:
                f.write(content)
            logger.debug("Saved response content to last_response.html")
            
            return content
            
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout on attempt {attempt + 1}: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} on attempt {attempt + 1}")
        except httpx.RequestError as e:
            logger.warning(f"Request error on attempt {attempt + 1}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
        
        if attempt == max_retries - 1:
            logger.error(f"All {max_retries} attempts failed for URL: {url}")
            raise
    
    return None

def extract_search_data(html: str) -> Dict:
    """Extract product data from search page HTML"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        logger.debug("Created BeautifulSoup object")
        
        # Look for product cards in the new layout
        products = []
        product_cards = soup.select('div.search-item-card-wrapper-gallery')
        
        if product_cards:
            logger.debug(f"Found {len(product_cards)} product cards")
            
            for card in product_cards:
                try:
                    # Find the product link
                    link = card.select_one('a.search-card-item')
                    if not link:
                        continue
                        
                    # Extract product ID from URL
                    product_id = link.get('href', '').split('item/')[-1].split('.html')[0]
                    
                    # Extract product title
                    title_elem = card.select_one('h3.lq_jl')
                    title = title_elem.text.strip() if title_elem else None
                    
                    # Extract price
                    price_spans = card.select('div.lq_j3 span')
                    price = ''
                    for span in price_spans:
                        price += span.text.strip()
                    price = price.replace('$', '')
                    
                    # Extract image URL
                    img = card.select_one('img.l9_be')
                    image_url = img.get('src') if img else None
                    
                    # Extract store name
                    store_elem = card.select_one('span.io_ip')
                    store_name = store_elem.text.strip() if store_elem else None
                    
                    # Extract sales count
                    sales_elem = card.select_one('span.lq_jg')
                    sales = sales_elem.text.strip() if sales_elem else None
                    
                    product_data = {
                        "productId": product_id,
                        "title": title,
                        "price": price,
                        "image": image_url,
                        "store": store_name,
                        "sales": sales,
                        "url": f"https://www.aliexpress.com/item/{product_id}.html"
                    }
                    
                    if product_data["productId"] and product_data["title"]:
                        products.append(product_data)
                        logger.debug(f"Extracted product: {product_data}")
                        
                except Exception as e:
                    logger.error(f"Error parsing product card: {str(e)}")
            
            logger.debug(f"Successfully extracted {len(products)} products")
            return {"mods": {"itemList": {"content": products}}}
            
        logger.warning("Could not find any product cards")
        return {"mods": {"itemList": {"content": []}}}
        
    except Exception as e:
        logger.error(f"Error extracting search data: {str(e)}")
        return {"mods": {"itemList": {"content": []}}}

def parse_product(data: Dict) -> Optional[Dict]:
    """Parse individual product data"""
    try:
        product = {
            "id": data.get("productId"),
            "title": data.get("title"),
            "price": float(data.get("price", "0").replace(",", "")),
            "currency": "USD",
            "url": data.get("url"),
            "image": data.get("image"),
            "store": data.get("store"),
            "sales": data.get("sales")
        }
        
        # Clean up the data
        if product["image"] and not product["image"].startswith(("http:", "https:")):
            product["image"] = f"https:{product['image']}"
            
        logger.debug(f"Parsed product: {product}")
        return product
    except Exception as e:
        logger.error(f"Error parsing product: {str(e)}")
        return None

def add_or_replace_url_parameters(url: str, **params) -> str:
    """Add or replace URL parameters"""
    try:
        parsed_url = urlparse(url)
        query_params = dict(parse_qsl(parsed_url.query))
        query_params.update(params)
        return urlunparse(parsed_url._replace(query=urlencode(query_params)))
    except Exception as e:
        logger.error(f"Error modifying URL parameters: {str(e)}")
        return url

async def scrape_search(url: str, max_pages: int = 1) -> List[Dict]:
    """Scrape AliExpress search results"""
    logger.info(f"Starting search scrape for URL: {url}")
    products = []
    
    try:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        timeout = httpx.Timeout(30.0, connect=10.0)
        
        async with httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            verify=True,
            http2=True
        ) as client:
            # Fetch first page
            html = await fetch_with_retry(client, url)
            if not html:
                return []
                
            data = extract_search_data(html)
            product_list = data.get("mods", {}).get("itemList", {}).get("content", [])
            
            logger.debug(f"Raw product list: {json.dumps(product_list[:1], indent=2)}")
            
            for product in product_list:
                parsed_product = parse_product(product)
                if parsed_product:
                    products.append(parsed_product)
            
            logger.info(f"Found {len(products)} products on first page")
            
            # Handle pagination if needed
            if max_pages > 1:
                for page in range(2, max_pages + 1):
                    try:
                        page_url = add_or_replace_url_parameters(url, page=page)
                        page_html = await fetch_with_retry(client, page_url)
                        if page_html:
                            page_data = extract_search_data(page_html)
                            page_products = page_data.get("mods", {}).get("itemList", {}).get("content", [])
                            
                            for product in page_products:
                                parsed_product = parse_product(product)
                                if parsed_product:
                                    products.append(parsed_product)
                            
                            logger.info(f"Added {len(page_products)} products from page {page}")
                    except Exception as e:
                        logger.error(f"Error fetching page {page}: {str(e)}")
                        continue
                    
                    # Add delay between pages
                    await asyncio.sleep(random.uniform(2, 4))
    
    except Exception as e:
        logger.error(f"Error in scrape_search: {str(e)}")
    
    return products

async def run():
    """Test function"""
    try:
        url = "https://www.aliexpress.com/w/wholesale-iphone-12.html?g=y&SearchText=iphone+12"
        logger.info(f"Starting test run with URL: {url}")
        
        data = await scrape_search(url, max_pages=1)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        logger.info(f"Test run completed. Found {len(data)} products")
    except Exception as e:
        logger.error(f"Error in test run: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run())