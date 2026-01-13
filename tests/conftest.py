"""
Shared pytest fixtures for HTTPayer SDK tests.
These fixtures provide common test resources and skip tests when credentials are missing.
"""
import os
import pytest
from httpayer import HTTPayerClient
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Test URLs
# ============================================================================

@pytest.fixture
def test_api_url():
    """Standard test API URL that returns 402 Payment Required"""
    return "https://api.itsgloria.ai/news?feed_categories=ai,crypto"


# ============================================================================
# Skip Conditions (for missing credentials)
# ============================================================================

requires_api_key = pytest.mark.skipif(
    not os.getenv("HTTPAYER_API_KEY"),
    reason="HTTPAYER_API_KEY not set - proxy tests require valid API key"
)

requires_evm_key = pytest.mark.skipif(
    not os.getenv("EVM_PRIVATE_KEY"),
    reason="EVM_PRIVATE_KEY not set - EVM relay tests require private key"
)

requires_solana_key = pytest.mark.skipif(
    not os.getenv("SOLANA_PRIVATE_KEY") and not os.getenv("SOLANA_KEYPAIR"),
    reason="SOLANA_PRIVATE_KEY or SOLANA_KEYPAIR not set - Solana relay tests require private key"
)


# ============================================================================
# Client Fixtures
# ============================================================================

@pytest.fixture
def proxy_client():
    """HTTPayerClient in proxy mode (API key-based)"""
    api_key = os.getenv("HTTPAYER_API_KEY")
    if not api_key:
        pytest.skip("HTTPAYER_API_KEY not set")
    return HTTPayerClient(api_key=api_key)


@pytest.fixture
def evm_relay_client():
    """HTTPayerClient in relay mode with EVM wallet"""
    private_key = os.getenv("EVM_PRIVATE_KEY")
    if not private_key:
        pytest.skip("EVM_PRIVATE_KEY not set")
    return HTTPayerClient(
        private_key=private_key,
        network="skale-base"
    )


@pytest.fixture
def solana_relay_client():
    """HTTPayerClient in relay mode with Solana wallet"""
    private_key = os.getenv("SOLANA_PRIVATE_KEY") or os.getenv("SOLANA_KEYPAIR")
    if not private_key:
        pytest.skip("SOLANA_PRIVATE_KEY or SOLANA_KEYPAIR not set")
    return HTTPayerClient(
        private_key=private_key,
        network="solana-mainnet-beta"
    )

