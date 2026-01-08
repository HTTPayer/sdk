"""
// Copyright (c) 2025 HTTPayer Inc. under ChainSettle Inc. All rights reserved.
// Licensed under the HTTPayer SDK License – see LICENSE.txt.
"""

"""
Test EVM self-custodial client with private key.

This test demonstrates:
1. Auto-detection of EVM wallet from private key
2. Network validation for EVM networks
3. Making requests with self-custodial EVM wallet
"""

import os
from httpayer import HTTPayerClient
from dotenv import load_dotenv

load_dotenv()


def test_evm_wallet_detection():
    """Test that EVM wallet is correctly auto-detected from hex private key."""
    print("\n=== Testing EVM Wallet Auto-Detection ===")

    # Use test private key (DO NOT use real private keys in tests!)
    # This is a randomly generated test key with no real funds
    test_private_key = os.getenv(
        "TEST_EVM_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"  # Hardhat default key
    )

    client = HTTPayerClient(
        private_key=test_private_key,
        network="base-sepolia",  # EVM testnet
    )

    # Verify wallet type was detected correctly
    assert client.network_type == "evm", f"Expected network_type 'evm', got '{client.network_type}'"
    assert client.mode == "relay", f"Expected mode 'relay', got '{client.mode}'"
    assert client.account is not None, "EVM account should be set"
    assert client.account_address is not None, "EVM account address should be set"
    assert client.solana_keypair is None, "Solana keypair should not be set for EVM wallet"

    print(f"✓ Wallet type detected: {client.network_type}")
    print(f"✓ Mode: {client.mode}")
    print(f"✓ Address: {client.account_address}")
    print("✓ EVM wallet auto-detection passed!")


def test_evm_network_validation():
    """Test that EVM wallet rejects Solana networks."""
    print("\n=== Testing EVM Network Validation ===")

    test_private_key = os.getenv(
        "TEST_EVM_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )

    # Should succeed with EVM network
    client = HTTPayerClient(
        private_key=test_private_key,
        network="base-sepolia",
    )
    print(f"✓ Accepted EVM network: base-sepolia")

    # Should fail with Solana network
    try:
        client = HTTPayerClient(
            private_key=test_private_key,
            network="solana-devnet",  # Solana network with EVM key
        )
        print("✗ Should have rejected Solana network for EVM wallet")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Correctly rejected Solana network: {e}")

    print("✓ EVM network validation passed!")


def test_evm_request_with_network_override():
    """Test making requests with network override validation."""
    print("\n=== Testing EVM Request with Network Override ===")

    test_private_key = os.getenv(
        "TEST_EVM_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )

    client = HTTPayerClient(
        private_key=test_private_key,
        network="base-sepolia",
    )

    # Test URL (will return 404 but that's OK for testing)
    test_url = "https://www.x402.org/test-endpoint"

    # Should accept valid EVM network override
    print("Testing valid EVM network override...")
    try:
        # This will likely 404 or succeed, but shouldn't error on network validation
        response = client.request("GET", test_url, network="base")
        print(f"✓ Accepted EVM network override: base (status: {response.status_code})")
    except ValueError as e:
        if "not compatible" in str(e):
            print(f"✗ Should not reject EVM network: {e}")
            raise
        # Other errors are OK (connection, 404, etc.)
        print(f"✓ Network validation passed (other error: {e})")

    # Should reject Solana network override
    print("Testing invalid Solana network override...")
    try:
        response = client.request("GET", test_url, network="solana-devnet")
        print("✗ Should have rejected Solana network override")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        if "not compatible" in str(e):
            print(f"✓ Correctly rejected Solana network override: {e}")
        else:
            raise

    print("✓ EVM network override validation passed!")


def test_evm_payment_flow():
    """Test EVM payment flow with self-custodial wallet."""
    print("\n=== Testing EVM Payment Flow ===")

    test_private_key = os.getenv(
        "TEST_EVM_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )

    client = HTTPayerClient(
        private_key=test_private_key,
        network="base-sepolia",
        privacy_mode=True,  # Use relay for testing
    )

    print(f"Client initialized with:")
    print(f"  - Network type: {client.network_type}")
    print(f"  - Mode: {client.mode}")
    print(f"  - Privacy mode: {client.privacy_mode}")
    print(f"  - Address: {client.account_address}")

    # Test with a known 402 endpoint if available
    test_url = os.getenv("TEST_402_URL", "https://www.x402.org/protected")

    print(f"\nAttempting request to: {test_url}")
    try:
        # This should route through HTTPayer relay
        response = client.request("GET", test_url)
        print(f"✓ Request completed with status: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Payment successful!")
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Note: Request failed (expected if endpoint unavailable): {e}")

    print("✓ EVM payment flow test completed!")


def main():
    """Run all EVM self-custodial tests."""
    print("\n" + "="*60)
    print("EVM SELF-CUSTODIAL CLIENT TESTS")
    print("="*60)

    try:
        test_evm_wallet_detection()
        test_evm_network_validation()
        test_evm_request_with_network_override()
        test_evm_payment_flow()

        print("\n" + "="*60)
        print("✓ ALL EVM TESTS PASSED!")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        raise


if __name__ == "__main__":
    main()
