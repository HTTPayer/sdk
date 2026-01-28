"""
Solana relay mode payment example.
Uses your Solana private key for self-custodial payments.
Network auto-detects to "solana" for Solana wallets.
"""
import os
from httpayer import HTTPayerClient

# Initialize with Solana private key (uses SOLANA_PRIVATE_KEY from environment)
# Network auto-detects to "solana" for Solana wallets
client = HTTPayerClient(
    private_key=os.getenv("SOLANA_PRIVATE_KEY")
)

response = client.request("GET", "https://api.itsgloria.ai/news?feed_categories=ai,crypto")

print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")