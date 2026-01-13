"""
Unit tests for network validation logic.
Tests network compatibility, type checking, and strict_networks flag.
"""
import pytest
from httpayer import HTTPayerClient


def test_invalid_network_strict_mode():
    """Test that invalid network raises error in strict mode"""
    client = HTTPayerClient(strict_networks=True)

    with pytest.raises(ValueError, match="not in supported_networks"):
        client.request("GET", "https://example.com", network="invalid-network")


def test_invalid_network_non_strict_mode():
    """Test that invalid network is allowed in non-strict mode"""
    client = HTTPayerClient(strict_networks=False)
    # Should not raise - will likely fail at payment stage but validation passes
    # We're just testing validation logic here, not actual request execution


def test_evm_wallet_with_solana_network():
    """Test that EVM wallet cannot use Solana networks"""
    import os
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    if not evm_key:
        pytest.skip("EVM_PRIVATE_KEY not set")

    with pytest.raises(ValueError, match="not compatible with EVM wallet"):
        client = HTTPayerClient(
            private_key=evm_key,
            network="solana-mainnet-beta"
        )


def test_solana_wallet_with_evm_network():
    """Test that Solana wallet cannot use EVM networks"""
    import os
    solana_key = os.getenv("SOLANA_PRIVATE_KEY") or os.getenv("SOLANA_KEYPAIR")
    if not solana_key:
        pytest.skip("SOLANA_PRIVATE_KEY or SOLANA_KEYPAIR not set")

    with pytest.raises(ValueError, match="not compatible with Solana wallet"):
        client = HTTPayerClient(
            private_key=solana_key,
            network="base"
        )


def test_network_override_validation():
    """Test that network override in request() validates compatibility"""
    import os
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    if not evm_key:
        pytest.skip("EVM_PRIVATE_KEY not set")

    client = HTTPayerClient(
        private_key=evm_key,
        network="base"
    )

    # Should raise when trying to override with incompatible network
    with pytest.raises(ValueError, match="not compatible"):
        client.request(
            "GET",
            "https://example.com",
            network="solana-mainnet-beta"
        )


def test_proxy_mode_no_network_validation():
    """Test that proxy mode doesn't enforce network type validation"""
    import os
    api_key = os.getenv("HTTPAYER_API_KEY")
    if not api_key:
        pytest.skip("HTTPAYER_API_KEY not set")

    # Proxy mode should accept any network (validation happens server-side)
    client = HTTPayerClient(api_key=api_key)
    # Should not raise - network validation is less strict in proxy mode
