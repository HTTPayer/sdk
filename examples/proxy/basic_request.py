"""
Basic proxy mode request example.
Auto-handles 402 Payment Required responses using your API key.
"""
from httpayer import HTTPayerClient

# Initialize client (uses HTTPAYER_API_KEY from environment)
client = HTTPayerClient()

# Make request - automatically handles payment if 402 is returned
response = client.request("GET", "https://api.itsgloria.ai/news?feed_categories=ai,crypto")

print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")
