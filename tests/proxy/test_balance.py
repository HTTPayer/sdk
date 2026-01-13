"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.proxy
def test_get_balance(proxy_client):
    """Test retrieving account balance in proxy mode"""
    balance = proxy_client.get_balance()

    # Basic check - just verify it returns something
    assert balance is not None