"""
Basic error handling tests that don't require credentials.
These tests verify that the SDK properly validates inputs and raises appropriate errors.
"""
import os
import pytest
from httpayer import HTTPayerClient


def test_invalid_response_mode():
    """Test that invalid response_mode raises error"""
    with pytest.raises(ValueError, match="response_mode must be"):
        HTTPayerClient(response_mode="invalid")


def test_invalid_private_key():
    """Test that invalid private key raises error"""
    with pytest.raises(ValueError, match="Invalid private key"):
        HTTPayerClient(private_key="not-a-valid-key-12345")


def test_missing_api_key_proxy_mode():
    """Test that proxy mode requires API key when no private key provided"""
    # Temporarily remove API key from environment
    old_key = os.environ.pop("HTTPAYER_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="Missing HTTPAYER_API_KEY"):
            HTTPayerClient()
    finally:
        # Restore API key if it existed
        if old_key:
            os.environ["HTTPAYER_API_KEY"] = old_key


def test_balance_only_in_proxy_mode():
    """Test that get_balance() only works in proxy mode"""
    import os
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    if not evm_key:
        pytest.skip("EVM_PRIVATE_KEY not set")

    relay_client = HTTPayerClient(private_key=evm_key, network="base")

    with pytest.raises(RuntimeError, match="Balance endpoint only available in proxy mode"):
        relay_client.get_balance()


def test_relay_limits_only_in_relay_mode():
    """Test that get_relay_limits() only works in relay mode"""
    import os
    api_key = os.getenv("HTTPAYER_API_KEY")
    if not api_key:
        pytest.skip("HTTPAYER_API_KEY not set")

    proxy_client = HTTPayerClient(api_key=api_key)

    with pytest.raises(RuntimeError, match="Relay limits only available in relay mode"):
        proxy_client.get_relay_limits()
