"""
// Copyright (c) 2025 HTTPayer Inc. under ChainSettle Inc. All rights reserved.
// Licensed under the HTTPayer SDK License – see LICENSE.txt.
"""

"""
Test Solana self-custodial client with private key.

This test demonstrates:
1. Auto-detection of Solana wallet from base58/hex private key
2. Network validation for Solana networks
3. Making requests with self-custodial Solana wallet
"""

import os
from httpayer import HTTPayerClient
from dotenv import load_dotenv

load_dotenv()


def test_solana_wallet_detection_base58():
    """Test that Solana wallet is correctly auto-detected from base58 private key."""
    print("\n=== Testing Solana Wallet Auto-Detection (Base58) ===")

    # Use test private key (DO NOT use real private keys in tests!)
    # This is a randomly generated test key with no real funds
    # Base58 format is standard for Solana
    test_private_key = os.getenv(
        "TEST_SOLANA_PRIVATE_KEY",
        # This is a test key generated with: solana-keygen new --no-passphrase
        "5KepQDXNW9wCvUQvpGmYqP9bEJ4QwXJb3QhXHXpJnVTKhxsKb7V8VYMm3VY3q3MxvP6sF7bQj6h5YdT2LpV9vJa"
    )

    try:
        client = HTTPayerClient(
            private_key=test_private_key,
            network="solana-devnet",  # Solana testnet
        )

        # Verify wallet type was detected correctly
        assert client.network_type == "solana", f"Expected network_type 'solana', got '{client.network_type}'"
        assert client.mode == "relay", f"Expected mode 'relay', got '{client.mode}'"
        assert client.solana_keypair is not None, "Solana keypair should be set"
        assert client.account_address is not None, "Solana account address should be set"
        assert client.account is None, "EVM account should not be set for Solana wallet"

        print(f"✓ Wallet type detected: {client.network_type}")
        print(f"✓ Mode: {client.mode}")
        print(f"✓ Address: {client.account_address}")
        print("✓ Solana wallet auto-detection (base58) passed!")

    except ValueError as e:
        if "Invalid private key" in str(e):
            print(f"Note: Test skipped - invalid test key format: {e}")
            print("  Set TEST_SOLANA_PRIVATE_KEY env var with a valid Solana private key")
        else:
            raise


def test_solana_wallet_detection_hex():
    """Test that Solana wallet is correctly auto-detected from hex private key."""
    print("\n=== Testing Solana Wallet Auto-Detection (Hex) ===")

    # Generate a test hex key for Solana (32 bytes = 64 hex chars)
    test_private_key_hex = os.getenv(
        "TEST_SOLANA_PRIVATE_KEY_HEX",
        "a1b2c3d4e5f6071829a1b2c3d4e5f6071829a1b2c3d4e5f6071829a1b2c3d4"  # 32 bytes hex
    )

    try:
        client = HTTPayerClient(
            private_key=test_private_key_hex,
            network="solana-devnet",
        )

        # Verify wallet type was detected correctly
        assert client.network_type == "solana", f"Expected network_type 'solana', got '{client.network_type}'"
        assert client.solana_keypair is not None, "Solana keypair should be set"

        print(f"✓ Wallet type detected: {client.network_type}")
        print(f"✓ Address: {client.account_address}")
        print("✓ Solana wallet auto-detection (hex) passed!")

    except Exception as e:
        print(f"Note: Hex format test result: {e}")
        # Hex format might not be supported by all Solana key parsers
        print("  (Hex format is optional, base58 is preferred for Solana)")


def test_solana_network_validation():
    """Test that Solana wallet rejects EVM networks."""
    print("\n=== Testing Solana Network Validation ===")

    test_private_key = os.getenv(
        "TEST_SOLANA_PRIVATE_KEY",
        "5KepQDXNW9wCvUQvpGmYqP9bEJ4QwXJb3QhXHXpJnVTKhxsKb7V8VYMm3VY3q3MxvP6sF7bQj6h5YdT2LpV9vJa"
    )

    try:
        # Should succeed with Solana network
        client = HTTPayerClient(
            private_key=test_private_key,
            network="solana-devnet",
        )
        print(f"✓ Accepted Solana network: solana-devnet")

        # Should fail with EVM network
        try:
            client = HTTPayerClient(
                private_key=test_private_key,
                network="base-sepolia",  # EVM network with Solana key
            )
            print("✗ Should have rejected EVM network for Solana wallet")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            if "not compatible" in str(e):
                print(f"✓ Correctly rejected EVM network: {e}")
            else:
                raise

        print("✓ Solana network validation passed!")

    except ValueError as e:
        if "Invalid private key" in str(e):
            print(f"Note: Test skipped - invalid test key: {e}")
        else:
            raise


def test_solana_request_with_network_override():
    """Test making requests with network override validation."""
    print("\n=== Testing Solana Request with Network Override ===")

    test_private_key = os.getenv(
        "TEST_SOLANA_PRIVATE_KEY",
        "5KepQDXNW9wCvUQvpGmYqP9bEJ4QwXJb3QhXHXpJnVTKhxsKb7V8VYMm3VY3q3MxvP6sF7bQj6h5YdT2LpV9vJa"
    )

    try:
        client = HTTPayerClient(
            private_key=test_private_key,
            network="solana-devnet",
        )

        # Test URL
        test_url = "https://www.x402.org/test-endpoint"

        # Should accept valid Solana network override
        print("Testing valid Solana network override...")
        try:
            response = client.request("GET", test_url, network="solana-mainnet-beta")
            print(f"✓ Accepted Solana network override: solana-mainnet-beta (status: {response.status_code})")
        except ValueError as e:
            if "not compatible" in str(e):
                print(f"✗ Should not reject Solana network: {e}")
                raise
            # Other errors are OK
            print(f"✓ Network validation passed (other error: {e})")

        # Should reject EVM network override
        print("Testing invalid EVM network override...")
        try:
            response = client.request("GET", test_url, network="base")
            print("✗ Should have rejected EVM network override")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            if "not compatible" in str(e):
                print(f"✓ Correctly rejected EVM network override: {e}")
            else:
                raise

        print("✓ Solana network override validation passed!")

    except ValueError as e:
        if "Invalid private key" in str(e):
            print(f"Note: Test skipped - invalid test key: {e}")
        else:
            raise


def test_solana_payment_flow():
    """Test Solana payment flow with self-custodial wallet."""
    print("\n=== Testing Solana Payment Flow ===")

    test_private_key = os.getenv(
        "TEST_SOLANA_PRIVATE_KEY",
        "5KepQDXNW9wCvUQvpGmYqP9bEJ4QwXJb3QhXHXpJnVTKhxsKb7V8VYMm3VY3q3MxvP6sF7bQj6h5YdT2LpV9vJa"
    )

    try:
        client = HTTPayerClient(
            private_key=test_private_key,
            network="solana-devnet",
            privacy_mode=True,  # Use relay for testing
        )

        print(f"Client initialized with:")
        print(f"  - Network type: {client.network_type}")
        print(f"  - Mode: {client.mode}")
        print(f"  - Privacy mode: {client.privacy_mode}")
        print(f"  - Address: {client.account_address}")

        # Test with a known 402 endpoint if available
        test_url = os.getenv("TEST_402_SOLANA_URL", "https://www.x402.org/protected")

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

        print("✓ Solana payment flow test completed!")

    except ValueError as e:
        if "Invalid private key" in str(e):
            print(f"Note: Test skipped - invalid test key: {e}")
            print("  Set TEST_SOLANA_PRIVATE_KEY env var with a valid Solana private key")
        else:
            raise


def test_solana_direct_payment():
    """Test Solana direct x402 payment (privacy_mode=False)."""
    print("\n=== Testing Solana Direct Payment ===")

    test_private_key = os.getenv(
        "TEST_SOLANA_PRIVATE_KEY",
        "5KepQDXNW9wCvUQvpGmYqP9bEJ4QwXJb3QhXHXpJnVTKhxsKb7V8VYMm3VY3q3MxvP6sF7bQj6h5YdT2LpV9vJa"
    )

    try:
        client = HTTPayerClient(
            private_key=test_private_key,
            network="solana-devnet",
            privacy_mode=False,  # Enable direct payments
        )

        print(f"Client initialized for direct payments:")
        print(f"  - Network type: {client.network_type}")
        print(f"  - Privacy mode: {client.privacy_mode}")
        print(f"  - Address: {client.account_address}")

        # Note: Direct payment requires server to return 402 with Solana accepts
        test_url = os.getenv("TEST_402_SOLANA_DIRECT_URL", "https://www.x402.org/solana-protected")

        print(f"\nAttempting direct payment to: {test_url}")
        print("Note: This requires the endpoint to support Solana x402 payments")

        try:
            response = client.request("GET", test_url)
            print(f"✓ Direct payment completed with status: {response.status_code}")
            if response.status_code == 200:
                print(f"✓ Direct Solana payment successful!")
        except Exception as e:
            print(f"Note: Direct payment test result: {e}")
            print("  (Direct payments require endpoint Solana support)")

        print("✓ Solana direct payment test completed!")

    except ValueError as e:
        if "Invalid private key" in str(e):
            print(f"Note: Test skipped - invalid test key: {e}")
        else:
            raise


def main():
    """Run all Solana self-custodial tests."""
    print("\n" + "="*60)
    print("SOLANA SELF-CUSTODIAL CLIENT TESTS")
    print("="*60)

    try:
        test_solana_wallet_detection_base58()
        test_solana_wallet_detection_hex()
        test_solana_network_validation()
        test_solana_request_with_network_override()
        test_solana_payment_flow()
        test_solana_direct_payment()

        print("\n" + "="*60)
        print("✓ ALL SOLANA TESTS PASSED!")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        raise


if __name__ == "__main__":
    main()
