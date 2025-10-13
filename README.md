# HTTPayer – Python SDK

**HTTPayer** is a lightweight Python SDK for accessing APIs protected by [`402 Payment Required`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402) responses using the emerging [x402 protocol](https://github.com/coinbase/x402).

It integrates with the **HTTPayer Router** to automatically fulfill off-chain payments (e.g. USDC / stablecoins via [EIP-3009](https://eips.ethereum.org/EIPS/eip-3009)), enabling pay-per-use APIs and metered endpoints.

---

## Features

- Auto-handles 402 payment flows through the hosted HTTPayer router
- Supports `response_mode="text"` (default) or `"json"` for structured proxy results
- Built-in polling for asynchronous payment completions (`202 + webhook`)
- Optional dry-run simulation (`simulate=True` or `simulate_invoice`)
- API key + router configuration via environment or arguments
- Compatible with Base Sepolia, Avalanche Fuji, and other EVM testnets
- Flask `X402Gate` decorator for securing your own 402-protected endpoints

---

## Installation

```bash
pip install httpayer
```

or with demo dependencies (Flask, CCIP examples):

```bash
pip install httpayer[demo]
```

---

## Environment Setup

Copy `.env.sample` → `.env` and configure your API key and network:

```env
HTTPAYER_API_KEY=your-api-key
```

For testing the `X402Gate` decorator or local demos:

```env
NETWORK=base
FACILITATOR_URL=https://x402.org
RPC_GATEWAY=https://your-gateway.example
PAY_TO_ADDRESS=0xYourReceivingAddress
```

---

## Usage

### 1. Programmatic Client

```python
from httpayer import HTTPayerClient

client = HTTPayerClient(response_mode="json")

# auto-handles 402 Payment Required
resp = client.request("GET", "https://x402.org/protected")

print(resp.status_code)   # 200
print(resp.json())        # resource data
```

#### Manual Payment or Simulation

```python
# simulate required payment (dry-run)
sim = client.simulate_invoice("GET", "https://x402.org/protected")

# pay actual invoice via router
paid = client.pay_invoice("GET", "https://x402.org/protected")
```

If the router returns `202 Accepted`, the client will automatically poll the provided `webhook_url` until completion.

---

### 2. Flask Authorization – `X402Gate`

Protect your own Web2 endpoints with tokenized payment headers:

```python
from httpayer.gate import X402Gate
from flask import Flask, jsonify, make_response

gate = X402Gate(
    pay_to="0xYourReceivingAddress",
    network="base-sepolia",
    asset_address="0xTokenAddress",
    max_amount=1000,
    asset_name="USD Coin",
    asset_version="2",
    facilitator_url="https://x402.org",
)

app = Flask(__name__)

@app.route("/weather")
@gate.gate
def weather():
    return make_response(jsonify({"weather": "sunny", "temp": 75}))
```

Each route can define its own `X402Gate` instance with unique token or chain parameters.

---

## Examples

| File             | Description                                       |
| ---------------- | ------------------------------------------------- |
| `tests/test1.py` | Programmatic 402 requests using `HTTPayerClient`  |
| `tests/test2.py` | Flask Weather API protected with `X402Gate`       |
| `tests/test3.py` | Explicit `simulate_invoice` / `pay_invoice` usage |
| `tests/test4.py` | Raw JSON return (`response_mode='json'`)          |

Run with:

```bash
python tests/test1.py
```

> Local endpoints cannot be paid through the hosted router —
> for local testing, use the [Coinbase x402 SDKs](https://github.com/coinbase/x402).

---

## Project Layout

```
httpayer/
├── client.py        # HTTPayerClient – main SDK client
├── gate.py          # X402Gate – Flask decorator & helpers
tests/
├── test1.py         # Programmatic example
├── test2.py         # Flask demo server
├── test3.py         # Explicit pay/simulate example
├── test4.py         # Raw JSON example
.env.sample          # Environment template
```

---

## Author

**HTTPayer Team**

- [general@httpayer.com](mailto:general@httpayer.com)
- [httpayer.com](https://www.httpayer.com/)

---

## License

This SDK is proprietary and licensed under the HTTPayer SDK License.  
Cloning, redistribution, or republishing is strictly prohibited.  
See the [LICENSE.md](./LICENSE.md) file for details.
