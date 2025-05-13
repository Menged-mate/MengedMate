import requests
import sys

def test_api_connection(base_url):
    """Test the API connection by making requests to various endpoints."""
    endpoints = [
        '/health/',
        '/api/health/',
        '/api/test/',
    ]
    
    print(f"Testing API connection to {base_url}")
    print("-" * 50)
    
    for endpoint in endpoints:
        url = f"{base_url.rstrip('/')}{endpoint}"
        print(f"Testing endpoint: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text[:100]}")
            print(f"Headers: {dict(response.headers)}")
        except Exception as e:
            print(f"Error: {str(e)}")
        
        print("-" * 50)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://mengedmate-backend.onrender.com"
    
    test_api_connection(base_url)
