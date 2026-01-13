"""
Check relay usage limits and quotas (relay mode only).
"""
import os
from httpayer import HTTPayerClient

# EVM example
client = HTTPayerClient(
    private_key=os.getenv("EVM_PRIVATE_KEY"),
    network="base"
)

limits = client.get_relay_limits()
print(f"Relay limits: {limits}")



