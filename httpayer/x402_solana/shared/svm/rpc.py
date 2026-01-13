"""
RPC client utilities for connecting to Solana networks
"""

from typing import Optional, Literal
import httpx
import base58


# Solana RPC endpoints
MAINNET_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
]

DEVNET_ENDPOINTS = [
    "https://api.devnet.solana.com",
]


def create_rpc_client(
    network: Literal["solana", "solana-devnet", "solana-mainnet-beta"],
    custom_url: Optional[str] = None
) -> str:
    """
    Create an RPC URL for the specified Solana network.
    
    Args:
        network: Network identifier ("solana", "solana-devnet", or "solana-mainnet-beta")
        custom_url: Optional custom RPC URL
        
    Returns:
        RPC URL as string
    """
    if custom_url:
        return custom_url
    
    if network in ("solana", "solana-mainnet-beta"):
        return MAINNET_ENDPOINTS[0]
    elif network == "solana-devnet":
        return DEVNET_ENDPOINTS[0]
    else:
        raise ValueError(f"Unsupported network: {network}")


async def get_slot(rpc_url: str) -> int:
    """
    Get the current slot from the network.

    Args:
        rpc_url: RPC URL

    Returns:
        Current slot number
    """
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSlot",
            "params": [{"commitment": "confirmed"}]
        }

        response = await client.post(rpc_url, json=payload, timeout=30.0)
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            raise ValueError(f"RPC error: {result['error']}")

        return result["result"]


async def get_block_height(rpc_url: str) -> int:
    """
    Get the current block height from the network.

    Args:
        rpc_url: RPC URL

    Returns:
        Current block height
    """
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBlockHeight",
            "params": [{"commitment": "confirmed"}]
        }

        response = await client.post(rpc_url, json=payload, timeout=30.0)
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            raise ValueError(f"RPC error: {result['error']}")

        return result["result"]


async def get_account_info(rpc_url: str, pubkey: str) -> dict:
    """
    Get account info from the network.

    Args:
        rpc_url: RPC URL
        pubkey: Public key as base58 string

    Returns:
        Account info dict or None if account doesn't exist
    """
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                pubkey,
                {"encoding": "base64", "commitment": "confirmed"}
            ]
        }

        response = await client.post(rpc_url, json=payload, timeout=30.0)
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            raise ValueError(f"RPC error: {result['error']}")

        return result["result"]["value"]  # None if account doesn't exist


async def get_latest_blockhash(rpc_url: str) -> tuple[bytes, int]:
    """
    Get the latest blockhash from the network.

    Args:
        rpc_url: RPC URL

    Returns:
        Tuple of (blockhash_bytes, last_valid_block_height)
    """
    import httpx
    import json

    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getLatestBlockhash",
            "params": [{"commitment": "confirmed"}]
        }

        response = await client.post(rpc_url, json=payload, timeout=30.0)
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            raise ValueError(f"RPC error: {result['error']}")

        blockhash_str = result["result"]["value"]["blockhash"]
        last_valid_slot = result["result"]["value"]["lastValidBlockHeight"]

        # Decode base58 blockhash
        blockhash_bytes = base58.b58decode(blockhash_str)

        return blockhash_bytes, last_valid_slot