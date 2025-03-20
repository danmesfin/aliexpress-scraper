import json
import random
import asyncio
import math
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import httpx
from parsel import Selector
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_headers() -> Dict[str, str]:
    """
    Generate request headers with a random user agent to prevent blocking.
    Includes necessary cookies and headers for AliExpress requests.
    """
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

def extract_search(response) -> Dict:
    """
    Extract product data from AliExpress search page response.
    The data is stored in a JavaScript variable '_init_data_' within a script tag.
    
    Returns:
        Dict containing the parsed product data or empty product list if extraction fails
    """
    try:
        sel = Selector(response.text)
        script_with_data = sel.xpath('//script[contains(.,"_init_data_=")]')
        if not script_with_data:
            logger.error("No _init_data_ script found in page")
            return {"data": {"root": {"fields": {"mods": {"itemList": {"content": []}}}}}}
            
        data = json.loads(script_with_data.re(r'_init_data_\s*=\s*{\s*data:\s*({.+}) }')[0])
        return data['data']['root']['fields']
    except Exception as e:
        logger.error(f"Error in extract_search: {str(e)}")
        return {"mods": {"itemList": {"content": []}}}

def parse_search(response):
    """
    Parse AliExpress search results into a standardized format.
    Extracts key product information including ID, title, price, and store details.
    
    Returns:
        List of parsed product dictionaries with normalized data
    """
    try:
        data = extract_search(response)
        parsed = []
        
        if not data.get("mods", {}).get("itemList", {}).get("content"):
            logger.info("No products found in search results")
            return []
            
        for result in data["mods"]["itemList"]["content"]:
            try:
                parsed.append({
                    "id": result["productId"],
                    "url": f"https://www.aliexpress.com/item/{result['productId']}.html",
                    "type": result.get("productType", "natural"),
                    "title": result["title"]["displayTitle"],
                    "price": result["prices"]["salePrice"]["minPrice"],
                    "currency": result["prices"]["salePrice"]["currencyCode"],
                    "trade": result.get("trade", {}).get("tradeDesc"),
                    "thumbnail": result["image"]["imgUrl"].lstrip("/"),
                    "store": {
                        "url": result["store"]["storeUrl"],
                        "name": result["store"]["storeName"],
                        "id": str(result["store"]["storeId"]),
                        "ali_id": str(result["store"]["aliMemberId"]),
                    },
                })
            except KeyError as e:
                logger.warning(f"Missing required field in product data: {str(e)}")
                continue
                
        return parsed
    except Exception as e:
        logger.error(f"Error in parse_search: {str(e)}")
        return []

async def scrape_search(url: str, max_pages: int = 1) -> Dict:
    """
    Scrape AliExpress search results using their modern API format.
    Handles both old-style URLs (?SearchText=query) and new-style URLs (/wholesale-query.html).
    
    Args:
        url: AliExpress search URL
        max_pages: Maximum number of pages to scrape (default: 1)
    
    Returns:
        Dict containing:
        - products: List of parsed product data
        - total: Total number of products found
        - error: Error message if scraping failed (optional)
    """
    try:
        # Extract and normalize search query from URL
        parsed_url = urlparse(url)
        query_params = dict(parse_qsl(parsed_url.query))
        query = query_params.get('SearchText', '').strip()
        
        if not query and 'wholesale-' in parsed_url.path:
            query = parsed_url.path.split('wholesale-')[-1].split('.html')[0].replace('-', ' ')
        
        if not query:
            logger.error("Empty search query")
            return {"products": [], "total": 0, "error": "Search query cannot be empty"}
            
        query = query.replace(" ", "-")
        sort_type = query_params.get('SortType', query_params.get('sorttype', 'default'))

        async with httpx.AsyncClient(follow_redirects=True) as session:
            session.headers.update(get_headers())
            
            # Fetch first page
            logger.info(f"Scraping search query: {query} with sort: {sort_type}")
            first_page = await session.get(
                f"https://www.aliexpress.com/w/wholesale-{query}.html"
                f"?sorttype={sort_type}&d=y&page=1"
            )
            
            product_previews = parse_search(first_page)
            if not product_previews:
                logger.info("No products found on first page")
                return {"products": [], "total": 0}

            # Fetch additional pages if requested
            if max_pages > 1:
                try:
                    async def scrape_page(page):
                        return await session.get(
                            f"https://www.aliexpress.com/w/wholesale-{query}.html"
                            f"?sorttype={sort_type}&d=y&page={page}"
                        )

                    other_pages = await asyncio.gather(*[scrape_page(i) for i in range(2, max_pages + 1)])
                    for response in other_pages:
                        product_previews.extend(parse_search(response))
                except Exception as e:
                    logger.error(f"Error scraping additional pages: {str(e)}")

            return {"products": product_previews, "total": len(product_previews)}

    except Exception as e:
        logger.error(f"Error in scrape_search: {str(e)}")
        return {"products": [], "total": 0, "error": str(e)}

async def run():
    """Test the scraper with a sample search query"""
    url = "https://www.aliexpress.com/w/wholesale-smartphone.html"
    results = await scrape_search(url, max_pages=1)
    print(f"Found {results['total']} products")
    print(json.dumps(results['products'][:2], indent=2))

if __name__ == "__main__":
    asyncio.run(run())