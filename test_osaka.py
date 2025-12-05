"""Test Osaka scraper"""
import sys
sys.path.insert(0, '/Users/keitoyamakawa/iiba/iiba-kosodate-passport-scraper')

from src.features.scraping.scrapers.prefectures.osaka import OsakaScraper
from src.shared.http.client import HTTPClient

# Create HTTP client
http_client = HTTPClient(timeout=10)

# Create scraper
scraper = OsakaScraper(http_client=http_client)

print(f"Scraper initialized: {scraper.prefecture_name}")
print(f"Base URL: {scraper.base_url}")

# Test API call directly
import requests
response = requests.get("https://api.osaka-pass.jp/shop/list/?GROUP=1&START=0")
data = response.json()

print(f"\nAPI Response:")
print(f"Status: {data.get('STATUS')}")
print(f"Count: {data.get('COUNT')}")
print(f"Data list length: {len(data.get('DATALIST', []))}")

# Test parser
if data.get('DATALIST'):
    first_shop_data = data['DATALIST'][0]
    print(f"\nFirst shop data keys: {list(first_shop_data.keys())}")
    
    shop = scraper.parser.parse(first_shop_data)
    if shop:
        print(f"\nParsed shop:")
        print(f"  ID: {shop.shop_id}")
        print(f"  Name: {shop.name}")
        print(f"  Address: {shop.address}")
        print(f"  Phone: {shop.phone}")
        print(f"  Benefits: {shop.benefits[:100] if shop.benefits else None}...")
    else:
        print("\nFailed to parse shop")

print("\nTest completed successfully!")
