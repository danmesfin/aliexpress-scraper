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
    "url": "https://aliexpress.com/...",  // AliExpress search URL
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

## Contributing

Feel free to open issues or submit pull requests for any improvements.
