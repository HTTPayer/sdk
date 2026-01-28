"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.relay
@pytest.mark.evm
@pytest.mark.expensive
def test_evm_basic_request(evm_relay_client, test_evm_api_url):
    """Test basic EVM relay payment for 402-protected resource"""
    response = evm_relay_client.request("GET", test_evm_api_url)
    assert response.status_code == 200


@pytest.mark.relay
@pytest.mark.evm
@pytest.mark.expensive
def test_evm_simulate_request(evm_relay_client, test_evm_api_url):
    """Test EVM relay simulation (dry-run)"""
    response = evm_relay_client.request("GET", test_evm_api_url, simulate=True)
    assert response.status_code == 200