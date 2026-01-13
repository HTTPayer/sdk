# HTTPayer SDK Tests

## Quick Start

```bash
# Install dev dependencies (including pytest)
uv sync --group dev

# Run all tests
uv run pytest

# Run specific test directory
uv run pytest tests/proxy/
uv run pytest tests/relay/
uv run pytest tests/unit/

# Run with coverage report
uv run pytest --cov=httpayer --cov-report=term-missing

# Run tests matching a pattern
uv run pytest -k "test_network"

# Run only unit tests (no credentials needed)
uv run pytest tests/unit/
```

## Environment Setup

Copy `.env.sample` to `.env` and configure:

```env
HTTPAYER_API_KEY=your-api-key-here       # Required for proxy tests
EVM_PRIVATE_KEY=0x...                    # Required for EVM relay tests
SOLANA_PRIVATE_KEY=base58-key            # Required for Solana relay tests
SOLANA_KEYPAIR=[64,bytes,array,...]      # Alternative Solana format
```

## Test Categories

### `proxy/` - Proxy Mode Tests

API key-based tests for custodial payment flow through HTTPayer router.

**Requires:** `HTTPAYER_API_KEY`

- `test_basic_requests.py` - Basic request with simulate and pay
- `test_direct_pay.py` - Direct `pay_invoice()` and `simulate_invoice()` calls
- `test_balance.py` - Account balance check
- `test_response_modes.py` - JSON vs text response modes
- `test_simulate.py` - Simulation-only tests

### `relay/` - Relay Mode Tests

Private key-based tests for self-custodial payments using x402 protocol.

**Requires:** `EVM_PRIVATE_KEY` or `SOLANA_PRIVATE_KEY`/`SOLANA_KEYPAIR`

- `test_evm_basic.py` - EVM wallet relay payments
- `test_solana_basic.py` - Solana wallet relay payments
- `test_relay_limits.py` - Relay usage limits check
- `test_direct_mode.py` - Direct payment with x402 client; does not use HTTPayer proxy for privacy
- `test_pay_helpers` - Direct `pay_invoice()` and `simulate_invoice()` calls
- `test_response_modes.py` - JSON vs text response modes

### `unit/` - Unit Tests

Tests for validation logic and error handling. **No credentials required.**

- `test_network_validation.py` - Network compatibility validation

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and skip conditions
├── README.md                # This file
├── proxy/                   # Proxy mode tests (API key)
│   ├── test_basic_requests.py
│   ├── test_balance.py
│   └── ...
├── relay/                   # Relay mode tests (private key)
│   ├── test_evm_relay.py
│   ├── test_solana_relay.py
│   └── ...
└── unit/                    # Unit tests (no credentials)
    └── test_network_validation.py
```

## Running Specific Test Types

```bash
# Unit tests only (no credentials needed)
uv run pytest tests/unit/

# Proxy tests only (requires API key)
uv run pytest tests/proxy/

# EVM relay tests only (requires EVM private key)
uv run pytest tests/relay/test_evm_relay.py

# Solana relay tests only (requires Solana private key)
uv run pytest tests/relay/test_solana_relay.py
```

## Skipped Tests

Tests automatically skip if required credentials are missing:

```bash
$ uv run pytest tests/proxy/
...
SKIPPED [1] tests/proxy/test_balance.py: HTTPAYER_API_KEY not set
```

This is expected behavior when credentials are not configured.
