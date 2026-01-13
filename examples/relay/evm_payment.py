"""
EVM relay mode payment example.
Uses your private key for self-custodial payments.
"""
import os
from httpayer import HTTPayerClient

# Initialize with EVM private key (uses EVM_PRIVATE_KEY from environment)
client = HTTPayerClient(
    private_key=os.getenv("EVM_PRIVATE_KEY"),
    network="base"
)

response = client.request("GET", "https://api.itsgloria.ai/news?feed_categories=ai,crypto")

print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")