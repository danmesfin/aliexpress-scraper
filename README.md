# AliExpress Scraper API

A FastAPI-based web service that scrapes product data from AliExpress search results. The API provides rate-limited access to search results with configurable pagination.

## Features

- 🔍 Scrape product data from AliExpress search URLs
- 🚀 Fast and asynchronous scraping using httpx
- 🔄 Built-in rate limiting (20 requests per minute)
- 🛡️ Automatic retry mechanism with exponential backoff
- 🔒 Random user agent rotation for better scraping reliability
- 📝 Detailed logging for debugging
- 🐳 Dockerized deployment ready

## API Endpoints

### GET /
Root endpoint that returns API information and available endpoints.

### POST /search
Search for products on AliExpress.

**Request Body:**
```json
{
    "url": "https://www.aliexpress.com/w/wholesale-iphone-12.html?g=y&SearchText=iphone+12",  // AliExpress search URL
    "max_pages": 1                        // Number of pages to scrape (default: 1, max: 10)
}
```

**Response:**
```json
{
    "products": [
        {
            "id": "string",
            "title": "string",
            "url": "string",
            "price": 0.0,
            "currency": "USD",
            "image": "string",
            "store": "string",
            "sales": "string"
        }
    ],
    "total_products": 0
}
```

## Setup and Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd aliexpress-scraper
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Deployment

1. Make sure Docker is installed and running

2. Build the Docker image:
   ```bash
   docker build -t aliexpress-scraper .
   ```

3. Run the container:
   ```bash
   docker run -d --name aliexpress-scraper -p 8000:8000 aliexpress-scraper
   ```

The API will be available at `http://localhost:8000`. You can access the interactive API documentation at `http://localhost:8000/docs`.

## Dependencies

- Python 3.11+
- FastAPI
- Uvicorn
- BeautifulSoup4
- HTTPX
- Python-dotenv
- Pydantic
- Parsel

## Rate Limiting

The API implements rate limiting to prevent abuse:
- 20 requests per minute per client
- Maximum of 10 pages per search request
- Automatic retry mechanism with exponential backoff for failed requests

## Error Handling

The API includes comprehensive error handling for:
- Invalid URLs
- Rate limit exceeded
- Network errors
- Parsing errors
- Server errors

## Future Enhancements

Here are some potential features and improvements that could be implemented:

### Data Enhancement
- 📊 Product price history tracking
- 🌟 Product reviews and ratings scraping
- 🏷️ Product categories and tags extraction
- 📈 Sales volume trends analysis
- 🔍 Similar products recommendations
- 🌍 Multi-currency support

### API Features
- 🔐 Authentication and API key management
- 💾 Caching layer for frequently requested searches
- 📥 Bulk scraping with webhook notifications
- 📋 Custom data export formats (CSV, JSON, Excel)
- 🔄 Periodic automated scraping
- 📱 Mobile-friendly API documentation

### Performance & Scalability
- 🚀 Distributed scraping across multiple workers
- 💽 Database integration for persistent storage
- 🔄 Queue system for handling large requests
- 🌐 Proxy rotation for improved reliability
- 📊 Metrics and monitoring dashboard
- 🔧 Auto-scaling based on load

### Advanced Features
- 🤖 AI-powered product data extraction
- 📊 Price comparison across sellers
- 📈 Market analysis and trends
- 🔔 Price drop alerts
- 🎯 Competitor tracking
- 📱 Mobile app integration

Feel free to contribute to any of these enhancements or suggest new ones!

## Contributing

Feel free to open issues or submit pull requests for any improvements.
