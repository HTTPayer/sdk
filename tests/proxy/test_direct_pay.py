"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.proxy
@pytest.mark.expensive
def test_explicit_simulate_invoice(proxy_client, test_api_url):
    """Test explicit simulate_invoice() method"""
    response = proxy_client.simulate_invoice("GET", test_api_url)
    assert response.status_code == 200 


@pytest.mark.proxy
@pytest.mark.expensive
def test_explicit_pay_invoice(proxy_client, test_api_url):
    """Test explicit pay_invoice() method"""
    response = proxy_client.pay_invoice("GET", test_api_url)
    assert response.status_code == 200
