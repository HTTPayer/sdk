"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.proxy
@pytest.mark.expensive
def test_simulate_then_pay(proxy_client, test_api_url):
    """Test simulating payment first, then executing actual payment"""
    # Simulate to get payment requirements
    sim_response = proxy_client.request("GET", test_api_url, simulate=True)
    assert sim_response.status_code == 200  

    # Now execute actual payment
    response = proxy_client.request("GET", test_api_url)
    assert response.status_code == 200


@pytest.mark.proxy
@pytest.mark.expensive
def test_basic_request_auto_402(proxy_client, test_api_url):
    """Test basic request that auto-handles 402 Payment Required"""
    response = proxy_client.request("GET", test_api_url)
    assert response.status_code == 200
