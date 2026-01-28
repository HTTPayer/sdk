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
def test_relay_response_mode_json(test_evm_api_url):
    """Test response_mode='json' in relay mode"""
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    if not evm_key:
        pytest.skip("EVM_PRIVATE_KEY not set")

    client = HTTPayerClient(
        response_mode="json",
        private_key=evm_key
    )

    response = client.request("GET", test_evm_api_url)
    assert response.status_code == 200


@pytest.mark.relay
@pytest.mark.evm
@pytest.mark.expensive
def test_relay_response_mode_text(test_evm_api_url):
    """Test response_mode='text' in relay mode (default)"""
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    if not evm_key:
        pytest.skip("EVM_PRIVATE_KEY not set")

    client = HTTPayerClient(
        response_mode="text",
        private_key=evm_key
    )

    response = client.request("GET", test_evm_api_url)
    assert response.status_code == 200
