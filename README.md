# HTTPayer – Python SDK

[![Documentation](https://img.shields.io/badge/docs-httpayer.com-0D9373)](https://docs.httpayer.com)

**HTTPayer** is a lightweight Python SDK for accessing APIs protected by [`402 Payment Required`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402) responses using the [x402 protocol](https://github.com/coinbase/x402).

The SDK supports two access patterns for handling 402-protected resources:

## Access Patterns

### Proxy Mode (`/proxy`) – Account-Based Abstraction

- Uses API keys for authentication
- Abstracts on-chain payments from the client
- Credits deducted only if HTTPayer is charged by the API
- Ideal for Web2 and server-side integrations
- No wallet or private key management required

### Relay Mode (`/relay`) – x402-Native Access

- Directly implements the x402 Protocol
- Uses payment headers for authorization
- No API key required – self-custodial payments
- Supports cross-chain access (pay on Base, access Solana APIs)
- Privacy-preserving routing via HTTPayer relay (when `privacy_mode=True`)
- Direct x402 payments to API providers (when `privacy_mode=False`)
- Automatic refunds if payment is not executed by target API

---

## Features

- Auto-handles 402 payment flows
- Dual access patterns: Proxy (API key) or Relay (private key)
- Cross-chain payments between EVM and Solana
- Privacy mode for anonymized payments via HTTPayer relay
- Dry-run simulation (`simulate=True`)
- Compatible with Base, Base Sepolia, SKALE Base, SKALE Base Sepolia, Solana, and Solana Devnet
- Response modes: `"text"` (unwrapped) or `"json"` (wrapped)

---

## Installation

```bash
pip install httpayer
```

For complete API reference and guides, visit **[docs.httpayer.com](https://docs.httpayer.com)**

---

## Environment Setup

Copy `.env.sample` → `.env` and configure your API key and/or Private Key:

```env
HTTPAYER_API_KEY=your-api-key
EVM_PRIVATE_KEY=your-private-key
SOLANA_PRIVATE_KEY=your-private-key
SOLANA_KEYPAIR=your-keypair
```

---

## Quick Start

### Proxy Mode (API Key)

```python
from httpayer import HTTPayerClient

# Initialize with API key (from HTTPAYER_API_KEY env var)
client = HTTPayerClient()

# Auto-handles 402 Payment Required - credits deducted on success
response = client.request("GET", "https://api.example.com/protected")

print(response.status_code)  # 200
print(response.json())       # resource data
```

### Relay Mode (Private Key)

```python
import os
from httpayer import HTTPayerClient

# Initialize with EVM private key
client = HTTPayerClient(
    private_key=os.getenv("EVM_PRIVATE_KEY"),
    network="base"  # Payment network
)

# Auto-handles 402 - self-custodial payment from your wallet
response = client.request("GET", "https://api.example.com/protected")

print(response.status_code)  # 200
print(response.json())       # resource data
```

### Cross-Chain Example

```python
# Pay on Solana, access API requiring Base payments
client = HTTPayerClient(
    private_key=os.getenv("SOLANA_PRIVATE_KEY"),
    network="solana-mainnet-beta"
)

# HTTPayer relay handles cross-chain conversion
response = client.request("GET", "https://base-api.example.com/data")
```

### Simulation (Dry-Run)

```python
# Preview payment cost without executing
sim = client.request("GET", "https://api.example.com/protected", simulate=True)
print(sim.json())  # Shows payment requirements and cost

# Then execute actual payment
response = client.request("GET", "https://api.example.com/protected")
```

## Examples

See the [`examples/`](./examples) directory for copy-paste ready code:

### Proxy Mode

- `examples/proxy/basic_request.py` - Simple GET request with auto-payment
- `examples/proxy/simulate_then_pay.py` - Preview cost before payment
- `examples/proxy/check_balance.py` - Check account balance

### Relay Mode

- `examples/relay/evm_payment.py` - Self-custodial payment with EVM wallet
- `examples/relay/solana_payment.py` - Self-custodial payment with Solana wallet
- `examples/relay/check_limits.py` - Check relay usage limits

Run any example:

```bash
python examples/proxy/basic_request.py
python examples/relay/evm_payment.py
```

> **Note:** Local endpoints cannot be paid through the hosted router.
> For local testing, use the [Coinbase x402 SDKs](https://github.com/coinbase/x402).

---

## Project Layout

```
httpayer/
├── client.py              # HTTPayerClient – main SDK client
├── x402_solana/           # Solana x402 implementation
examples/
├── proxy/                 # Proxy mode examples (API key)
│   ├── basic_request.py
│   ├── simulate_then_pay.py
│   └── check_balance.py
├── relay/                 # Relay mode examples (private key)
│   ├── evm_payment.py
│   ├── solana_payment.py
│   └── check_limits.py
tests/
├── proxy/                 # Proxy mode tests
├── relay/                 # Relay mode tests
├── unit/                  # Unit tests (no credentials needed)
└── conftest.py            # Shared pytest fixtures
.env.sample                # Environment template
```

---

## Author

**HTTPayer Team**

- [general@httpayer.com](mailto:general@httpayer.com)
- [httpayer.com](https://www.httpayer.com/)

---

## Attribution

This SDK builds upon and includes modified versions of open source software:

- **[x402 Protocol by Coinbase](https://github.com/coinbase/x402)** - Apache-2.0 License
  Core x402 protocol implementation vendored in `httpayer/_vendor/x402/`

- **[x402python by OrbytLabz](https://github.com/OrbytLabz/x402python)** - Apache-2.0 License
  Referenced implementation for Solana x402 protocol support

HTTPayer provides its own Solana x402 implementation (`httpayer/x402_solana/`) compatible with the x402 protocol specification.

For detailed attribution information, see [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).

---

## License

This SDK is proprietary and licensed under the HTTPayer SDK License.
Cloning, redistribution, or republishing is strictly prohibited.
See the [LICENSE.md](./LICENSE.md) file for details.

**Third-party dependencies** are licensed under their respective open source licenses (Apache-2.0).
