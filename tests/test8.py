import os
from httpayer import HTTPayerClient
from dotenv import load_dotenv

load_dotenv()

client = HTTPayerClient(
    private_key=os.getenv("EVM_PRIVATE_KEY"),
    network="avalanche" # Network to pay on
)

TARGET_API = "https://api.itsgloria.ai/news?feed_categories=ai,crypto"

response = client.request(
    method="GET",
    url=TARGET_API,
    headers={"Accept": "application/json"}
)

response.raise_for_status()
print(response.json())