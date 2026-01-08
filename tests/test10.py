import os
from httpayer import HTTPayerClient
from dotenv import load_dotenv

load_dotenv()

client = HTTPayerClient(
    private_key=os.getenv("SOLANA_PRIVATE_KEY"),
    network="solana-mainnet-beta" # Network to pay on
)

TARGET_API = "https://api.itsgloria.ai/news?feed_categories=ai,crypto"

response = client.request(
    method="GET",
    url=TARGET_API,
    headers={"Accept": "application/json"}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
response.raise_for_status()
print(response.json())