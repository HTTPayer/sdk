"""
// Copyright (c) 2025 HTTPayer Inc. under ChainSettle Inc. All rights reserved.
// Licensed under the HTTPayer SDK License – see LICENSE.txt.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from eth_utils import to_checksum_address, keccak, to_bytes
from web3 import Web3
from web3.contract import Contract

# ─────────────────────────────────────────────────────────────
# 1.  Dataclasses / types
# ─────────────────────────────────────────────────────────────
@dataclass
class PaymentRequirements:
    scheme:              str
    network:             str
    maxAmountRequired:   int          # (atomic units)
    resource:            str
    payTo:               str
    asset:               str          # token contract
    maxTimeoutSeconds:   int
    extra:               Dict[str, str]   # { name, version }

@dataclass
class VerifyResponse:
    isValid:        bool
    invalidReason:  Optional[str]
    payer:          str               # from-address (checksummed)

@dataclass
class SettleResponse:
    success:        bool
    transaction:    str               # tx hash hex
    network:        str
    payer:          str
    errorReason:    Optional[str] = None

# ─────────────────────────────────────────────────────────────
# 2.  Helpers – EIP-712 + signature
# ─────────────────────────────────────────────────────────────
EIP712_DOMAIN_TYPEHASH = keccak(
    text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
)
AUTH_TYPEHASH = keccak(
    text="TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
)

def _domain_separator(name: str, version: str, chain_id: int, token: str) -> bytes:
    return keccak(
        b"".join((
            EIP712_DOMAIN_TYPEHASH,
            keccak(text=name).rjust(32, b"\0"),
            keccak(text=version).rjust(32, b"\0"),
            chain_id.to_bytes(32, "big"),
            int(token, 16).to_bytes(32, "big"),
        ))
    )

def _struct_hash(auth: Dict[str, Any]) -> bytes:
    return keccak(
        b"".join((
            AUTH_TYPEHASH,
            int(auth["from"], 16).to_bytes(32, "big"),
            int(auth["to"],   16).to_bytes(32, "big"),
            int(auth["value"]).to_bytes(32, "big"),
            int(auth["validAfter"]).to_bytes(32, "big"),
            int(auth["validBefore"]).to_bytes(32, "big"),
            to_bytes(hexstr=auth["nonce"]).rjust(32, b"\0"),
        ))
    )

def _hash_transfer(auth: Dict[str, Any], chain_id: int, token: str,
                   name: str, version: str) -> bytes:
    ds = _domain_separator(name, version, chain_id, token)
    sh = _struct_hash(auth)
    return keccak(b"\x19\x01" + ds + sh)

def _split_sig(sig_hex: str) -> Dict[str, Any]:
    """0x-prefixed 65-byte sig → dict with v, r, s."""
    if sig_hex.startswith("0x"):
        sig_hex = sig_hex[2:]
    b = bytes.fromhex(sig_hex)
    if len(b) != 65:
        raise ValueError("bad_signature_length")
    r = "0x" + b[0:32].hex()
    s = "0x" + b[32:64].hex()
    v = b[64]
    if v < 27:
        v += 27
    return {"v": v, "r": r, "s": s}

# ─────────────────────────────────────────────────────────────
# 3.  VERIFY
# ─────────────────────────────────────────────────────────────
def verify_exact(
    w3: Web3,
    payment_payload: Dict[str, Any],
    req: PaymentRequirements,
) -> VerifyResponse:
    auth = payment_payload["authorization"]
    sig  = payment_payload["signature"]
    payer_addr = to_checksum_address(auth["from"])
    now = int(datetime.now(tz=timezone.utc).timestamp())

    if int(auth["value"]) > req.maxAmountRequired:
        return VerifyResponse(False, "amount_too_high", payer_addr)

    if to_checksum_address(req.payTo) != to_checksum_address(auth["to"]):
        return VerifyResponse(False, "wrong_payee", payer_addr)

    if now < int(auth["validAfter"]):
        return VerifyResponse(False, "not_yet_valid", payer_addr)

    if now > int(auth["validBefore"]):
        return VerifyResponse(False, "authorization_expired", payer_addr)

    digest = _hash_transfer(
        auth=auth,
        chain_id=w3.eth.chain_id,
        token=req.asset,
        name=req.extra["name"],
        version=req.extra["version"],
    )

    sig_obj = sig if isinstance(sig, dict) else _split_sig(sig)

    try:
        signer = w3.eth.account.recover_hash(
            hexstr=digest.hex(),
            vrs=(sig_obj["v"], sig_obj["r"], sig_obj["s"]),
        )
    except Exception as exc:
        return VerifyResponse(False, f"bad_signature:{exc}", payer_addr)

    if to_checksum_address(signer) != payer_addr:
        return VerifyResponse(False, "signer_mismatch", signer)

    return VerifyResponse(True, None, payer_addr)

# ─────────────────────────────────────────────────────────────
# 4.  SETTLE
# ─────────────────────────────────────────────────────────────
ERC20_AUTH_ABI = [
    {
        "name": "transferWithAuthorization",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "from",        "type": "address"},
            {"name": "to",          "type": "address"},
            {"name": "value",       "type": "uint256"},
            {"name": "validAfter",  "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce",       "type": "bytes32"},
            {"name": "v",           "type": "uint8"},
            {"name": "r",           "type": "bytes32"},
            {"name": "s",           "type": "bytes32"},
        ],
    }
]

def settle_exact(
    w3: Web3,
    signer,  # eth_account.signers.local.LocalAccount
    payment_payload: Dict[str, Any],
    req: PaymentRequirements,
) -> SettleResponse:
    auth = payment_payload["authorization"]
    sig  = payment_payload["signature"]
    sig_obj = sig if isinstance(sig, dict) else _split_sig(sig)
    payer_addr = to_checksum_address(auth["from"])

    try:
        token: Contract = w3.eth.contract(address=req.asset, abi=ERC20_AUTH_ABI)

        fn = token.functions.transferWithAuthorization(
            auth["from"],
            auth["to"],
            int(auth["value"]),
            int(auth["validAfter"]),
            int(auth["validBefore"]),
            auth["nonce"],
            sig_obj["v"],
            sig_obj["r"],
            sig_obj["s"],
        )

        tx = fn.build_transaction({
            "from": signer.address,
            "nonce": w3.eth.get_transaction_count(signer.address),
            "gasPrice": w3.eth.gas_price,
        })

        signed = signer.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        return SettleResponse(True, tx_hash.hex(), req.network, payer_addr)

    except Exception as exc:
        return SettleResponse(False, "", req.network, payer_addr, str(exc))
