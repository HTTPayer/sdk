"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.MD.
"""
import pytest


@pytest.mark.relay
@pytest.mark.evm
def test_evm_relay_limits(evm_relay_client):
    """Test getting relay limits for EVM wallet"""
    limits = evm_relay_client.get_relay_limits()
    assert limits is not None


@pytest.mark.relay
@pytest.mark.solana
def test_solana_relay_limits(solana_relay_client):
    """Test getting relay limits for Solana wallet"""
    limits = solana_relay_client.get_relay_limits()
    assert limits is not None



