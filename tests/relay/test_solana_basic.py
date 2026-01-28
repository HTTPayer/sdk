"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.relay
@pytest.mark.solana
@pytest.mark.expensive
def test_solana_basic_request(solana_relay_client, test_evm_api_url):
    """Test basic Solana relay payment for 402-protected resource"""
    response = solana_relay_client.request("GET", test_evm_api_url)
    assert response.status_code == 200


@pytest.mark.relay
@pytest.mark.solana
@pytest.mark.expensive
def test_solana_simulate_request(solana_relay_client, test_evm_api_url):
    """Test Solana relay simulation (dry-run)"""
    response = solana_relay_client.request("GET", test_evm_api_url, simulate=True)
    assert response.status_code == 200