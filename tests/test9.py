import os
from httpayer import HTTPayerClient
from dotenv import load_dotenv
import json

load_dotenv()

relay_client = HTTPayerClient(
    private_key=os.getenv("EVM_PRIVATE_KEY"),
    network="skale-base" # Network to pay on
)

relay_limits = relay_client.get_relay_limits()
print("Relay limits:", json.dumps(relay_limits, indent=2))

proxy_client = HTTPayerClient(
    api_key=os.getenv("HTTPAYER_API_KEY")
)

balance = proxy_client.get_balance()
print("Proxy client balance:", json.dumps(balance, indent=2))

