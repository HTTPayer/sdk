"""
// Copyright (c) 2025 HTTPayer Inc. under ChainSettle Inc. All rights reserved.
// Licensed under the HTTPayer SDK License – see LICENSE.txt.
"""

from functools import wraps
from flask import request, jsonify, make_response
import requests
from web3 import Web3
import base64, json

def decode_x_payment(header: str) -> dict:
    """
    Decode a base64-encoded X-PAYMENT header back into its structured JSON form.

    :param header: Base64-encoded X-PAYMENT string
    :return: Parsed Python dictionary of the payment payload
    """
    try:
        decoded_bytes = base64.b64decode(header)
        decoded_json = json.loads(decoded_bytes)
        if not isinstance(decoded_json, dict):
            raise ValueError("Decoded X-PAYMENT is not a JSON object")
        return decoded_json
    except (ValueError, json.JSONDecodeError, base64.binascii.Error) as e:
        raise ValueError(f"Invalid X-PAYMENT header: {e}")

def _encode_settle_header(settle_json: dict) -> str:
    """
    Deterministically compact-encode the settle JSON and base64-encode it,
    matching x402-js `settleResponseHeader(...)`.
    """
    compact = json.dumps(settle_json, separators=(",", ":"))
    return base64.b64encode(compact.encode()).decode()

class X402Gate:
    def __init__(self, *, pay_to, network, asset_address,
                 max_amount, asset_name, asset_version,
                 facilitator_url):
        self.pay_to          = Web3.to_checksum_address(pay_to)
        self.network         = network            
        self.asset_address   = Web3.to_checksum_address(asset_address)
        self.max_amount      = int(max_amount)              # keep atomic units
        base                 = facilitator_url.rstrip('/')
        self.verify_url      = f"{base}/facilitator/verify"
        self.settle_url      = f"{base}/facilitator/settle"
        self.asset_name      = asset_name
        self.asset_version   = asset_version

    def _verify(self, hdr: str, reqs: dict):
        payload = decode_x_payment(hdr)
        r = requests.post(
            self.verify_url,
            json={
                "x402Version": 1,
                "paymentPayload": payload,
                "paymentRequirements": reqs,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def _settle(self, hdr: str, reqs: dict):
        payload = decode_x_payment(hdr)
        r = requests.post(
            self.settle_url,
            json={
                "x402Version": 1,
                "paymentPayload": payload,
                "paymentRequirements": reqs,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json()          

    def gate(self, view_fn):
        @wraps(view_fn)
        def wrapper(*args, **kwargs):
            
            req_json = {
                "scheme": "exact",
                "network": self.network,  
                "maxAmountRequired": str(self.max_amount),
                "resource":  request.base_url,    
                "description": "",
                "mimeType":  "",
                "payTo":      self.pay_to,
                "maxTimeoutSeconds": 60,
                "asset":      self.asset_address,
                "extra": { "name": self.asset_name, "version": self.asset_version }
            }

            # 1. 402 if header missing
            pay_header = request.headers.get("X-Payment")
            if not pay_header:
                return make_response(jsonify({
                    "x402Version": 1,
                    "error": "X-PAYMENT header is required",
                    "accepts": [req_json],
                }), 402)

            # 2. verify
            try:
                self._verify(pay_header, req_json)
            except Exception as exc:
                return make_response(jsonify({
                    "x402Version": 1,
                    "error": f"verification failed: {exc}",
                    "accepts": [req_json],
                }), 402)

            # 3. run protected view
            resp = view_fn(*args, **kwargs)

            # 4. settle  (stop the response if settlement fails)
            try:
                settle_json = self._settle(pay_header, req_json)
                hdr = _encode_settle_header(settle_json)
                resp.headers["X-PAYMENT-RESPONSE"] = hdr
            except Exception as exc:
                return make_response(jsonify({
                    "x402Version": 1,
                    "error": f"settlement failed: {exc}",
                    "accepts": [req_json]
                }), 402)

            return resp
        return wrapper