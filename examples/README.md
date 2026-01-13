# HTTPayer SDK Examples

Simple, copy-paste ready examples for using the HTTPayer SDK.

## Setup

1. Copy `.env.sample` to `.env` in the project root
2. Add your credentials:
   ```env
   HTTPAYER_API_KEY=your-api-key        # For proxy examples
   EVM_PRIVATE_KEY=0x...                # For EVM relay examples
   SOLANA_PRIVATE_KEY=base58-key        # For Solana relay examples
   ```

## Proxy Mode Examples (API Key)

Custodial payments through HTTPayer router.

- **`proxy/basic_request.py`** - Simple GET request with auto-payment
- **`proxy/simulate_then_pay.py`** - Preview cost before payment
- **`proxy/check_balance.py`** - Check your account balance

Run:

```bash
python examples/proxy/basic_request.py
```

## Relay Mode Examples (Private Key)

Self-custodial payments using your wallet.

- **`relay/evm_payment.py`** - Payment with EVM wallet
- **`relay/solana_payment.py`** - Payment with Solana wallet
- **`relay/check_limits.py`** - Check relay usage limits

Run:

```bash
python examples/relay/evm_payment.py
```

## Quick Copy-Paste

### Proxy Mode (Simplest)

```python
from httpayer import HTTPayerClient

client = HTTPayerClient()  # Uses HTTPAYER_API_KEY from env
response = client.request("GET", "https://api.example.com/protected")
print(response.json())
```

### Relay Mode (EVM)

```python
import os
from httpayer import HTTPayerClient

client = HTTPayerClient(
    private_key=os.getenv("EVM_PRIVATE_KEY"),
    network="base"
)
response = client.request("GET", "https://api.example.com/protected")
print(response.json())
```

### Relay Mode (Solana)

```python
import os
from httpayer import HTTPayerClient

client = HTTPayerClient(
    private_key=os.getenv("SOLANA_PRIVATE_KEY"),
    network="solana-mainnet-beta"
)
response = client.request("GET", "https://api.example.com/protected")
print(response.json())
```
