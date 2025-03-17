from fastapi import FastAPI, HTTPException, Depends
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, HttpUrl
from datetime import datetime, timedelta
import logging
from app.aliexpress import scrape_search

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="AliExpress Scraper API",
             description="API for scraping product data from AliExpress",
             version="1.0.0")

class SearchRequest(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = 1

class ProductResponse(BaseModel):
    id: Optional[str]
    title: str
    url: Optional[str]
    price: Optional[float]
    currency: Optional[str] = "USD"
    image: Optional[str]
    store: Optional[str]
    sales: Optional[str]

class SearchResponse(BaseModel):
    products: List[ProductResponse]
    total_products: int

# Rate limiting implementation
class RateLimiter:
    def __init__(self, requests_per_minute: int = 20, window_size: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size  # in seconds
        self.requests = []
        logger.debug(f"Initialized RateLimiter with {requests_per_minute} requests per {window_size} seconds")
    
    def _clean_old_requests(self):
        """Remove requests older than the window size"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_size)
        self.requests = [req_time for req_time in self.requests if req_time > window_start]
        logger.debug(f"Cleaned old requests. Current count: {len(self.requests)}")
    
    async def check_rate_limit(self):
        """Check if the current request exceeds the rate limit"""
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
                    "error": "Rate limit exceeded. Please try again later.",
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
    """Root endpoint that returns API information"""
    return {
        "name": "AliExpress Scraper API",
        "version": "1.0.0",
        "description": "API for scraping product data from AliExpress",
        "endpoints": {
            "/search": {
                "description": "Search for products using a URL",
                "parameters": {
                    "url": "AliExpress search URL (required)",
                    "max_pages": "Maximum number of pages to scrape (optional, default: 1)"
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
    Search for products on AliExpress
    
    Args:
        request: SearchRequest object containing:
            - url: AliExpress search URL
            - max_pages: Maximum number of pages to scrape (default: 1)
    
    Returns:
        SearchResponse object containing:
            - products: List of product data
            - total_products: Total number of products found
    """
    try:
        # Validate max_pages
        if request.max_pages < 1:
            raise HTTPException(
                status_code=400,
                detail="max_pages must be greater than 0"
            )
        if request.max_pages > 10:
            raise HTTPException(
                status_code=400,
                detail="max_pages cannot exceed 10 to prevent abuse"
            )
            
        # Use our scraper module to get products
        raw_products = await scrape_search(
            url=str(request.url),
            max_pages=request.max_pages
        )
        
        # Convert raw products to ProductResponse objects
        products = []
        for product in raw_products:
            try:
                products.append(ProductResponse(
                    id=product.get("id"),
                    title=product.get("title", ""),
                    url=product.get("url"),
                    price=product.get("price"),
                    currency=product.get("currency", "USD"),
                    image=product.get("image"),
                    store=product.get("store"),
                    sales=product.get("sales")
                ))
            except Exception as e:
                logger.error(f"Error converting product data: {str(e)}")
                continue
        
        return SearchResponse(
            products=products,
            total_products=len(products)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_products: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape products: {str(e)}"
        )
