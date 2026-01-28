"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.relay
@pytest.mark.evm
@pytest.mark.expensive
def test_relay_explicit_simulate_invoice(evm_relay_client, test_evm_api_url):
    """Test explicit simulate_invoice() in relay mode"""
    response = evm_relay_client.simulate_invoice("GET", test_evm_api_url)
    assert response.status_code == 200


@pytest.mark.relay
@pytest.mark.evm
@pytest.mark.expensive
def test_relay_explicit_pay_invoice(evm_relay_client, test_evm_api_url):
    """Test explicit pay_invoice() in relay mode"""
    response = evm_relay_client.pay_invoice("GET", test_evm_api_url)
    assert response.status_code == 200
