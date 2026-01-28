"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest
from httpayer import HTTPayerClient


@pytest.mark.proxy
@pytest.mark.expensive
def test_response_mode_json(test_api_url):
    """Test response_mode='json' returns wrapped responses"""
    client = HTTPayerClient(response_mode="json")
    response = client.request("GET", test_api_url)
    assert response.status_code == 200


@pytest.mark.proxy
@pytest.mark.expensive
def test_response_mode_text(test_api_url):
    """Test response_mode='text' returns unwrapped responses (default)"""
    client = HTTPayerClient(response_mode="text")
    response = client.request("GET", test_api_url)
    assert response.status_code == 200
