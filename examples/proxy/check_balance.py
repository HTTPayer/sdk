"""
Check your HTTPayer account balance (proxy mode only).
"""
from httpayer import HTTPayerClient

client = HTTPayerClient()  # Uses HTTPAYER_API_KEY from environment

balance = client.get_balance()
print(f"Balance: {balance}")