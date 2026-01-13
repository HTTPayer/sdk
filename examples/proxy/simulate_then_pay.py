"""
Simulate payment first (dry-run), then execute actual payment.
Useful for previewing costs before committing.
"""
from httpayer import HTTPayerClient

client = HTTPayerClient()

url = "https://api.itsgloria.ai/news?feed_categories=ai,crypto"

# Simulate first - no payment made, just get cost estimate
sim_response = client.request("GET", url, simulate=True)
print(f"Simulation: {sim_response.json()}")

# Now execute actual payment
response = client.request("GET", url)
print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")
