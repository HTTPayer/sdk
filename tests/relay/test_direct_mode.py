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
def test_direct_x402_payment_no_privacy(test_api_url):
    """Test direct x402 payment with privacy_mode=False"""
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    if not evm_key:
        pytest.skip("EVM_PRIVATE_KEY not set")

    client = HTTPayerClient(
        private_key=evm_key,
        network="skale-base",
        privacy_mode=False  # Pay directly via x402, not through HTTPayer relay
    )

    response = client.request("GET", test_api_url)
    assert response.status_code == 200