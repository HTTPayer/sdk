"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import os
import pytest
from httpayer import HTTPayerClient


@pytest.mark.relay
@pytest.mark.evm
@pytest.mark.expensive
def test_direct_x402_payment_no_privacy(test_evm_api_url):
    """Test direct x402 payment with privacy_mode=False"""
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    if not evm_key:
        pytest.skip("EVM_PRIVATE_KEY not set")

    client = HTTPayerClient(
        private_key=evm_key,
        privacy_mode=False  # Pay directly via x402, not through HTTPayer relay
    )

    response = client.request("GET", test_evm_api_url)
    assert response.status_code == 200

@pytest.mark.relay
@pytest.mark.solana
@pytest.mark.expensive
def test_direct_x402_solana_payment_no_privacy(test_solana_api_url):
    """Test direct x402 payment with privacy_mode=False"""
    solana_key = os.getenv("SOLANA_PRIVATE_KEY") or os.getenv("SOLANA_KEYPAIR")
    if not solana_key:
        pytest.skip("SOLANA_PRIVATE_KEY or SOLANA_KEYPAIR not set")

    client = HTTPayerClient(
        private_key=solana_key,
        privacy_mode=False  # Pay directly via x402, not through HTTPayer relay
    )

    response = client.request("GET", test_solana_api_url)
    assert response.status_code == 200