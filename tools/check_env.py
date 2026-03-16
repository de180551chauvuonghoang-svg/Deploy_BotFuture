from dotenv import load_dotenv
import os
load_dotenv()
key = os.getenv('CRYPTOPANIC_API_KEY')
print(f"KEY_FOUND: {key is not None}")
if key:
    print(f"KEY_START: {key[:5]}...")
