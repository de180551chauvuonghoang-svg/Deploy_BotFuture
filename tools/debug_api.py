import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('CRYPTOPANIC_API_KEY')

urls = [
    "https://cryptopanic.com/api/v1/posts/",
    "https://cryptopanic.com/api/v2/posts/",
    "https://cryptopanic.com/api/developer/v2/posts/",
]

for url in urls:
    print(f"Testing {url}...")
    try:
        r = requests.get(url, params={'auth_token': api_key, 'public': 'true'}, timeout=5)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Successfully connected!")
            data = r.json()
            if 'results' in data:
                print(f"Sample news: {data['results'][0]['title']}")
            break
    except Exception as e:
        print(f"Error: {e}")
