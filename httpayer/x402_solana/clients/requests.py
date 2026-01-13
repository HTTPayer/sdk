"""
Solana x402 HTTP client with automatic request signing for relay mode
"""

import json
import time
from typing import Optional, Any, Dict
from requests import Session, Response
from solders.keypair import Keypair
import base64


class X402SolanaSession:
    """
    Wrapper around requests.Session that automatically signs relay requests
    with Solana keypair for authentication.
    """

    def __init__(self, keypair: Keypair):
        """
        Initialize a Solana x402 session.

        Args:
            keypair: Solana keypair for signing authentication
        """
        self.keypair = keypair
        self.session = Session()
        self.pubkey = str(keypair.pubkey())

    def _create_auth_signature(self, method: str, url: str, timestamp: int, body: Optional[str] = None) -> str:
        """
        Create authentication signature for relay request.

        Args:
            method: HTTP method
            url: Request URL
            timestamp: Unix timestamp in milliseconds
            body: Request body JSON string (optional)

        Returns:
            Base64-encoded signature
        """
        # Create message to sign: METHOD:URL:TIMESTAMP:BODY_HASH
        message_parts = [
            method.upper(),
            url,
            str(timestamp),
        ]
        
        if body:
            # Hash the body for integrity
            import hashlib
            body_hash = hashlib.sha256(body.encode()).hexdigest()
            message_parts.append(body_hash)
        
        message = ":".join(message_parts)
        message_bytes = message.encode()
        
        # Sign the message
        signature = self.keypair.sign_message(message_bytes)
        
        # Return base64-encoded signature
        return base64.b64encode(bytes(signature)).decode()

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """
        Make a POST request with automatic Solana authentication signing
        and automatic 402 payment handling.

        Args:
            url: Request URL
            json: JSON payload
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object
        """
        # Prepare headers
        headers = kwargs.get("headers", {}).copy()
        
        # Add timestamp
        timestamp = int(time.time() * 1000)
        
        # Serialize body
        body = None
        if json is not None:
            import json as json_module
            body = json if isinstance(json, str) else json_module.dumps(json)
            headers["Content-Type"] = "application/json"
        
        # Create signature
        signature = self._create_auth_signature("POST", url, timestamp, body)
        
        # Add auth headers
        headers["X-Wallet-Address"] = self.pubkey
        headers["X-Timestamp"] = str(timestamp)
        headers["X-Signature"] = signature
        
        kwargs["headers"] = headers
        
        # Make the request
        resp = self.session.post(url, json=json, **kwargs)
        
        # Handle 402 Payment Required
        if resp.status_code == 402:
            resp = self._handle_402_payment(resp, "POST", url, json, kwargs)
        
        return resp
    
    def _handle_402_payment(
        self,
        initial_response: Response,
        method: str,
        url: str,
        json_payload: Optional[Dict[str, Any]],
        kwargs: Dict[str, Any]
    ) -> Response:
        """
        Handle 402 Payment Required response by creating and sending x402 payment.

        Args:
            initial_response: Initial 402 response
            method: HTTP method
            url: Request URL
            json_payload: JSON payload (for retry)
            kwargs: Additional request arguments

        Returns:
            Response after payment
        """
        import asyncio
        from ..types import PaymentRequirements
        from ..schemes.exact_svm.client import create_payment_header
        
        try:
            # Parse payment requirements
            payment_data = initial_response.json()
            accepts = payment_data.get("accepts", [])
            
            if not accepts:
                return initial_response
            
            # Use first accept (could be enhanced to select best one)
            accept = accepts[0]
            
            # Create PaymentRequirements object
            requirements = PaymentRequirements(**accept)
            
            # Create payment header (async operation)
            async def _create_header():
                return await create_payment_header(
                    signer=self.keypair,
                    x402_version=1,
                    payment_requirements=requirements,
                    custom_rpc_url=None,
                )

            # Run async operation - handle both Jupyter notebooks and regular Python
            try:
                # Check if there's already a running event loop (e.g., in Jupyter)
                loop = asyncio.get_running_loop()
                # If we get here, there's a running loop, so we need to run in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _create_header())
                    payment_header = future.result()
            except RuntimeError:
                # No running loop, safe to use asyncio.run()
                payment_header = asyncio.run(_create_header())
            
            # Retry request with payment header
            headers = kwargs.get("headers", {}).copy()
            headers["X-PAYMENT"] = payment_header
            kwargs["headers"] = headers
            
            # Retry the request
            if method.upper() == "POST":
                return self.session.post(url, json=json_payload, **kwargs)
            elif method.upper() == "GET":
                return self.session.get(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
        except Exception as e:
            print(f"[x402_solana] Payment handling failed: {e}")
            return initial_response

    def get(self, url: str, **kwargs) -> Response:
        """
        Make a GET request with automatic Solana authentication signing.

        Args:
            url: Request URL
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object
        """
        # Prepare headers
        headers = kwargs.get("headers", {}).copy()
        
        # Add timestamp
        timestamp = int(time.time() * 1000)
        
        # Create signature
        signature = self._create_auth_signature("GET", url, timestamp)
        
        # Add auth headers
        headers["X-Wallet-Address"] = self.pubkey
        headers["X-Timestamp"] = str(timestamp)
        headers["X-Signature"] = signature
        
        kwargs["headers"] = headers
        
        return self.session.get(url, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> Response:
        """
        Make a request with automatic Solana authentication signing.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object
        """
        if method.upper() == "POST":
            return self.post(url, **kwargs)
        elif method.upper() == "GET":
            return self.get(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")


def x402_solana_requests(keypair: Keypair) -> X402SolanaSession:
    """
    Create a Solana x402 session for making authenticated relay requests.

    Args:
        keypair: Solana keypair for signing

    Returns:
        X402SolanaSession instance
    """
    return X402SolanaSession(keypair)
