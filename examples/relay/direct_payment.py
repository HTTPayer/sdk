"""
EVM direct mode payment example.
Uses your private key for self-custodial payments.
Makes direct payments on EVM networks without calling the HTTPayer server.
If target API returns payment instructions on the selected network, the SDK will pay them directly.
If you want to use relay mode, see evm_payment.py example.
Network auto-detects to "base" for EVM wallets.
"""
import os
from httpayer import HTTPayerClient

# Initialize with EVM private key (uses EVM_PRIVATE_KEY from environment)
# Network auto-detects to "base" for EVM wallets
client = HTTPayerClient(
    private_key=os.getenv("EVM_PRIVATE_KEY"),
    privacy_mode=False
)

response = client.request("GET", "https://api.itsgloria.ai/news?feed_categories=ai,crypto")

print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")