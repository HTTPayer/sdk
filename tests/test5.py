import os
from httpayer import HTTPayerClient

# Read from environment
router = os.getenv("X402_ROUTER")
auth = os.getenv("HTTPAYER_AUTH")

# Initialize client with router URL and auth token
client = HTTPayerClient(router, auth)

# Prepare and send request to Helius API to get Solana block height
url = "https://helius.api.corbits.dev"
method = "POST"
data = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getBlockHeight"
}

# Perform request
response = client.request(method, url, json=data)
result = response.json().get('result')

print("Solana Block Height:", f"{result:,}")


