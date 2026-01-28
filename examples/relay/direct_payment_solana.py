"""
Solana direct mode payment example.
Uses your private key for self-custodial payments.
Makes direct payments on Solana networks without calling the HTTPayer server.
If target API returns payment instructions on the selected network, the SDK will pay them directly.
If you want to use relay mode, see solana_payment.py example.
Network auto-detects to "solana" for Solana wallets.
"""
import os
from httpayer import HTTPayerClient

# Initialize with Solana private key (uses SOLANA_PRIVATE_KEY from environment)
# Network auto-detects to "solana" for Solana wallets
client = HTTPayerClient(
    private_key=os.getenv("SOLANA_PRIVATE_KEY"),
    privacy_mode=False
)

response = client.request("GET", "https://biznews.x402.bot/news")

print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")