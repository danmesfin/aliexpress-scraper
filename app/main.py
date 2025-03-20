from fastapi import FastAPI, HTTPException, Depends
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, HttpUrl
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse, parse_qsl
from app.aliexpress import scrape_search

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AliExpress Scraper API",
    description="API for scraping product data from AliExpress",
    version="1.0.0"
)

class SearchRequest(BaseModel):
    """
    Search request parameters.
    Accepts both old-style URLs (?SearchText=query) and new-style URLs (/wholesale-query.html)
    """
    url: HttpUrl
    max_pages: Optional[int] = 1

class StoreResponse(BaseModel):
    """Store information from AliExpress"""
    url: str
    name: str
    id: str
    ali_id: str

class ProductResponse(BaseModel):
    """
    Standardized product information from AliExpress.
    Includes essential details about the product and its seller.
    """
    id: str
    url: str
    type: str
    title: str
    price: float
    currency: str
    trade: Optional[str]
    thumbnail: str
    store: StoreResponse

class SearchResponse(BaseModel):
    """API response containing search results"""
    products: List[ProductResponse]
    total: int

class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    Tracks requests within a time window and rejects if limit is exceeded.
    """
    def __init__(self, requests_per_minute: int = 20, window_size: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size
        self.requests = []
        logger.debug(f"Initialized RateLimiter with {requests_per_minute} requests per {window_size} seconds")
    
    def _clean_old_requests(self):
        """Remove requests older than the window size"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_size)
        self.requests = [req_time for req_time in self.requests if req_time > window_start]
        logger.debug(f"Cleaned old requests. Current count: {len(self.requests)}")
    
    async def check_rate_limit(self):
        """
        Check if the current request exceeds the rate limit.
        Raises HTTPException if limit is exceeded.
        """
        now = datetime.now()
        self._clean_old_requests()
        
        if len(self.requests) >= self.requests_per_minute:
            window_start = now - timedelta(seconds=self.window_size)
            oldest_request = min(self.requests)
            wait_time = (window_start - oldest_request).total_seconds()
            
            logger.warning(f"Rate limit exceeded. Current requests: {len(self.requests)}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "current_requests": len(self.requests),
                    "limit": self.requests_per_minute,
                    "window_size": self.window_size,
                    "retry_after": max(0, int(wait_time))
                }
            )
        
        self.requests.append(now)
        logger.debug(f"Request allowed. Current count: {len(self.requests)}")

rate_limiter = RateLimiter(requests_per_minute=20, window_size=60)

@app.get("/")
async def root():
    """API information endpoint"""
    return {
        "name": "AliExpress Scraper API",
        "version": "1.0.0",
        "description": "API for scraping product data from AliExpress",
        "endpoints": {
            "/search": {
                "description": "Search for products using a URL",
                "parameters": {
                    "url": "AliExpress search URL (required)",
                    "max_pages": "Maximum number of pages to scrape (1-10, default: 1)"
                }
            }
        }
    }

@app.post("/search", response_model=SearchResponse)
async def search_products(
    request: SearchRequest,
    _=Depends(rate_limiter.check_rate_limit)
) -> SearchResponse:
    """
    Search for products on AliExpress.
    
    Accepts both URL formats:
    1. Old style: ?SearchText=query
    2. New style: /wholesale-query.html
    
    Args:
        request: SearchRequest containing URL and optional max_pages
        
    Returns:
        SearchResponse with product list and total count
        
    Raises:
        HTTPException: For invalid input, rate limiting, or scraping failures
    """
    try:
        # Validate search query in URL
        parsed_url = urlparse(str(request.url))
        query_params = dict(parse_qsl(parsed_url.query))
        
        has_search = False
        if query_params.get('SearchText', '').strip():
            has_search = True
        elif 'wholesale-' in parsed_url.path:
            query = parsed_url.path.split('wholesale-')[-1].split('.html')[0]
            if query.strip('-'):
                has_search = True
                
        if not has_search:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid search URL",
                    "message": "URL must either contain a SearchText parameter or be in format /wholesale-query.html"
                }
            )

        # Validate pagination
        if request.max_pages < 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid max_pages",
                    "message": "max_pages must be greater than 0"
                }
            )
        if request.max_pages > 10:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid max_pages",
                    "message": "max_pages cannot exceed 10 to prevent abuse"
                }
            )

        # Execute search
        results = await scrape_search(str(request.url), max_pages=request.max_pages)
        
        if "error" in results:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Scraping failed",
                    "message": results["error"]
                }
            )
            
        return SearchResponse(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_products: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e)
            }
        )
