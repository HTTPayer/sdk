"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.proxy
def test_simulate_only(proxy_client, test_api_url):
    """Test simulation without actual payment"""
    response = proxy_client.simulate_invoice("GET", test_api_url)
    assert response.status_code == 200
