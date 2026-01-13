"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.md.
"""

"""
Transaction encoding utilities for client-side payment creation
"""

import base64
from solders.transaction import Transaction


def encode_transaction_to_base64(transaction: Transaction) -> str:
    """
    Encode a Solana transaction to base64 string.

    Args:
        transaction: Solana transaction

    Returns:
        Base64-encoded transaction
    """
    tx_bytes = bytes(transaction)
    return base64.b64encode(tx_bytes).decode('utf-8')
