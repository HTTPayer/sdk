"""
Copyright (c) 2025 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.txt.
"""

# Ideas; instead of importing network constants locally,
# we call httpayer api for supported networks.

import os
import time
import requests
from typing import Optional, Dict, Any, Literal

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3
from x402.clients.requests import x402_requests

from httpayer.constants import SUPPORTED_NETWORKS

from httpayer.x402_solana.shared.svm.wallet import (
                        create_signer_from_base58,
                        create_signer_from_hex,
                    )
from httpayer.x402_solana.clients.requests import x402_solana_requests

load_dotenv()


class HTTPayerClient:
    """
    Unified HTTPayer client for managing 402 responses, x402 payments,
    proxy + relay execution, and dry-run simulation calls.

    Mode is auto-detected:
      - "relay": When account/private_key is provided (self-custodial)
      - "proxy": When only API key is provided (custodial)

    If response_mode is set to "json", responses from the httpayer router that look like:
        { "success": true, "result": <string|object> }
    Else responses will be unwrapped so .text/.json() behave as if you called the origin directly.
    """

    def __init__(
        self,
        router_url: Optional[str] = None,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
        account: Optional[Account] = None,
        network: Optional[str] = None,
        timeout: int = 60 * 10,
        use_session: bool = True,
        strict_networks: bool = True,
        response_mode: str = "text",
        privacy_mode: bool = True,
    ):
        if response_mode not in ("json", "text"):
            raise ValueError("response_mode must be 'json' or 'text'")

        self.response_mode = response_mode
        self.timeout = timeout
        self.network = network  # default relay network
        self.strict_networks = strict_networks
        self.privacy_mode = privacy_mode

        base_url = router_url or os.getenv("X402_ROUTER_URL", "https://api.httpayer.com")
        self.base_url = base_url.rstrip("/").removesuffix("/proxy")

        self.session = requests.Session() if use_session else requests

        # --------------------------------------------------
        # Wallet / relay setup (optional) - Support EVM and Solana
        # --------------------------------------------------
        self.account = None  # EVM account
        self.solana_keypair = None  # Solana keypair
        self.account_address = None
        self.x402_session = None
        self.network_type: Optional[Literal["evm", "solana"]] = None

        # Auto-detect wallet type from private key or account
        if account:
            # EVM account provided directly
            if not Web3.is_address(account.address):
                raise ValueError("Invalid EVM wallet address")
            self.account = account
            self.account_address = Web3.to_checksum_address(account.address)
            self.network_type = "evm"
            self.mode = "relay"
        elif private_key:
            print('[HTTPayer] Attempting to load wallet from private key')
            # Try to detect wallet type from private key
            wallet_detected = False

            # Try EVM first (most common)
            try:
                evm_account = Account.from_key(private_key)
                if Web3.is_address(evm_account.address):
                    self.account = evm_account
                    self.account_address = Web3.to_checksum_address(evm_account.address)
                    self.network_type = "evm"
                    wallet_detected = True
            except Exception:
                pass

            # If EVM failed, try Solana
            if not wallet_detected:
                print('[HTTPayer] Attempting to load Solana keypair')
                solana_errors = []
                
                # Try base58 first (standard Solana format)
                try:
                    self.solana_keypair = create_signer_from_base58(private_key)
                    self.account_address = str(self.solana_keypair.pubkey())
                    self.network_type = "solana"
                    wallet_detected = True
                    print(f'[HTTPayer] Successfully loaded Solana keypair from base58')
                except Exception as e:
                    solana_errors.append(f"base58: {e}")
                    
                # If base58 failed, try hex format
                if not wallet_detected:
                    try:
                        self.solana_keypair = create_signer_from_hex(private_key)
                        self.account_address = str(self.solana_keypair.pubkey())
                        self.network_type = "solana"
                        wallet_detected = True
                        print(f'[HTTPayer] Successfully loaded Solana keypair from hex')
                    except Exception as e:
                        solana_errors.append(f"hex: {e}")
                
                if not wallet_detected and solana_errors:
                    print(f"[HTTPayer] Solana key detection failed:")
                    for err in solana_errors:
                        print(f"  - {err}")


            if not wallet_detected:
                raise ValueError(
                    "Invalid private key: not a valid EVM (hex) or Solana (base58/hex) private key"
                )

            self.mode = "relay"
        else:
            # No wallet - proxy mode
            self.mode = "proxy"

        # Create x402 session for EVM wallets
        if self.network_type == "evm" and self.account:
            self.x402_session = x402_requests(self.account)
        # Create x402 session for Solana wallets
        elif self.network_type == "solana" and self.solana_keypair:
            self.x402_session = x402_solana_requests(self.solana_keypair)
        else:
            self.x402_session = None

        # --------------------------------------------------
        # Proxy auth (required if no wallet)
        # --------------------------------------------------
        self.api_key = api_key or os.getenv("HTTPAYER_API_KEY")

        if self.mode == "proxy" and not self.api_key:
            raise ValueError("Missing HTTPAYER_API_KEY for proxy mode")

        suffix = "?format=json" if self.response_mode == "json" else ""

        # ------------------
        # Proxy endpoints
        # ------------------
        self.pay_url = f"{self.base_url}/proxy{suffix}"
        self.sim_url = f"{self.base_url}/proxy/sim"
        self.balance_url = f"{self.base_url}/balance"

        # ------------------
        # Relay endpoints
        # ------------------
        self.relay_url = f"{self.base_url}/relay{suffix}"
        self.relay_sim_url = f"{self.base_url}/relay/sim"

        self.relay_limits_url = (
            f"{self.base_url}/relay/limits/{self.account_address}"
            if self.account_address
            else None
        )

        self.config = None
        self.supported_networks = SUPPORTED_NETWORKS
        self.network_chain_types = {}  # Maps network -> chainType (evm/solana)

        self._load_config()

        # Validate network type compatibility
        if self.network and self.network_type:
            self._validate_network_type_compatibility(self.network, "initialization")
        
        print(f'[HTTPayer] calling _validate_network with network={self.network}')

        self._validate_network(self.network, context="default network (pre-config)")


    # ------------------------------------------------------------------
    # Public helpers (proxy-compatible)
    # ------------------------------------------------------------------

    def pay_invoice(
        self,
        api_method: str,
        api_url: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        return self._call_router(
            self.pay_url,
            api_url,
            api_method,
            api_payload,
            api_params,
            api_headers,
        )

    def simulate_invoice(
        self,
        api_method: str,
        api_url: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        return self._call_router(
            self.sim_url,
            api_url,
            api_method,
            api_payload,
            api_params,
            api_headers,
        )

    def get_balance(self, api_key: Optional[str] = None) -> requests.Response:
        if self.mode != "proxy":
            raise RuntimeError("Balance endpoint only available in proxy mode")

        headers = {"x-api-key": api_key or self.api_key}
        return self.session.get(
            self.balance_url,
            headers=headers,
            timeout=self.timeout,
        ).json()

    def get_relay_limits(self) -> requests.Response:
        if self.mode != "relay":
            raise RuntimeError("Relay limits only available in relay mode")

        return self.session.get(
            self.relay_limits_url,
            timeout=self.timeout,
        ).json()
    
    def refresh_config(self) -> None:
        self._load_config()

    # ------------------------------------------------------------------
    # Unified request interface
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        simulate: bool = False,
        response_mode: Optional[str] = None,
        network: Optional[str] = None,
        **kwargs,
    ) -> requests.Response:
        # Validate network override compatibility with wallet type
        if network and self.network_type:
            self._validate_network_type_compatibility(network, "request override")

        self._validate_network(network, context="request override")

        effective_timeout = kwargs.pop("timeout", self.timeout)

        # First attempt direct call
        resp = self.session.request(
            method,
            url,
            timeout=effective_timeout,
            **kwargs,
        )

        if resp.status_code != 402:
            return resp

        # Solana direct x402 payment path
        if (
            self.mode == "relay"
            and not self.privacy_mode
            and self.network_type == "solana"
            and self.solana_keypair
        ):
            print('[HTTPayer] Detected Solana wallet for direct payment path')
            effective_network = network if network is not None else self.network
            if effective_network:
                # Check if target API accepts our Solana network
                accept = self._select_accept_for_network(resp, effective_network)

                # Verify the accepted network is Solana type
                accept_network = accept.get("network") if accept else None
                accept_chain_type = self.network_chain_types.get(accept_network)

                if accept and accept_chain_type == "solana":
                    return self._pay_direct_solana(
                        method,
                        url,
                        resp,
                        effective_network,
                        effective_timeout,
                        **kwargs,
                    )

        # EVM direct x402 payment path: only check if relay mode + privacy disabled + preferred network exists
        if self.mode == "relay" and not self.privacy_mode and self.network_type == "evm":
            effective_network = network if network is not None else self.network

            if effective_network:
                # Check if target API accepts our preferred network
                accept = self._select_accept_for_network(resp, effective_network)

                if accept:
                    self._validate_network(
                        accept.get("network"),
                        context="402 response",
                    )

                    return self._pay_direct_x402(
                        method,
                        url,
                        accept=accept,
                        effective_network=effective_network,
                        **kwargs,
                    )

        # Fallback: route through HTTPayer relay or proxy
        api_payload = kwargs.get("json") or {}
        api_params = kwargs.get("params") or {}
        api_headers = kwargs.get("headers") or {}

        active_mode = response_mode or self.response_mode

        # Relay path
        if self.mode == "relay":
            endpoint = self.relay_sim_url if simulate else self.relay_url

            if active_mode == "json" and "format=json" not in endpoint:
                endpoint = f"{endpoint}?format=json"

            return self._call_relay(
                endpoint,
                url,
                method,
                api_payload,
                api_params,
                api_headers,
                effective_timeout,
                network if network is not None else self.network,
            )

        # Proxy path
        endpoint = self.sim_url if simulate else self.pay_url

        if active_mode == "json" and "format=json" not in endpoint:
            endpoint = f"{endpoint}?format=json"

        return self._call_router(
            endpoint,
            url,
            method,
            api_payload,
            api_params,
            api_headers,
            effective_timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_router(
        self,
        endpoint: str,
        api_url: str,
        api_method: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
        effective_timeout: Optional[int] = None,
    ) -> requests.Response:
        data = {
            "api_url": api_url,
            "method": api_method,
            "payload": api_payload or {},
            "timeout": effective_timeout,
        }
        if api_params:
            data["params"] = api_params
        if api_headers:
            data["headers"] = api_headers

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        resp = self.session.post(
            endpoint,
            headers=headers,
            json=data,
            timeout=effective_timeout,
        )

        if resp.status_code == 202:
            webhook = resp.json().get("webhook_url")
            if not webhook:
                raise RuntimeError("202 response missing webhook_url")
            return self._poll_webhook(webhook)

        return resp

    def _call_relay(
        self,
        endpoint: str,
        api_url: str,
        api_method: str,
        api_payload: Dict[str, Any],
        api_params: Dict[str, Any],
        api_headers: Dict[str, str],
        effective_timeout: int,
        network: Optional[str],
    ) -> requests.Response:
        data = {
            "api_url": api_url,
            "method": api_method,
            "payload": api_payload,
            "params": api_params,
            "headers": api_headers,
        }

        if network:
            data["network"] = network

        # Use x402_session for both EVM and Solana
        resp = self.x402_session.post(
            endpoint,
            json=data,
            timeout=effective_timeout,
        )

        if resp.status_code == 202:
            webhook = resp.json().get("webhook_url")
            if not webhook:
                raise RuntimeError("202 response missing webhook_url")
            return self._poll_webhook(webhook)

        return resp

    def _poll_webhook(self, url: str) -> requests.Response:
        start = time.time()

        while True:
            poll = self.session.get(url, timeout=self.timeout)
            code = poll.status_code

            if code == 200:
                return poll

            if code == 202:
                if time.time() - start > self.timeout:
                    raise TimeoutError("Webhook polling exceeded timeout")
                time.sleep(3)
                continue

            if code == 500:
                try:
                    err = poll.json().get("error", poll.text)
                except Exception:
                    err = poll.text
                raise RuntimeError(f"Async task failed: {err}")

            raise RuntimeError(
                f"Async task returned unexpected status {code}: {poll.text[:200]}"
            )
    
    def _load_config(self) -> None:
        """
        Fetch HTTPayer config once and cache supported networks.
        Non-fatal if request fails.
        """
        try:
            resp = self.session.get(
                f"{self.base_url}/config",
                timeout=10,
            )
            if resp.status_code != 200:
                return

            self.config = resp.json()
            import json
            print(f'[HTTPayer] Loaded config: {json.dumps(self.config, indent=2)}')
            networks = (
                self.config
                .get("networks", {})
                .get("v1", [])
            )

            self.supported_networks = set(networks)

            # Build network -> chainType mapping from config
            network_configs = self.config.get("networks", {}).get("configs", {})
            for network_name, network_config in network_configs.items():
                chain_type = network_config.get("chainType")
                if chain_type:
                    self.network_chain_types[network_name] = chain_type

            self._validate_network(self.network, context="default network")

        except Exception:
            # Silent failure — config is optional
            self.config = None
    
    def _validate_network_type_compatibility(
        self,
        network: str,
        context: str = ""
    ) -> None:
        """
        Validate that network is compatible with wallet type.

        Args:
            network: Network identifier
            context: Context for error messages

        Raises:
            ValueError: If network doesn't match wallet type
        """
        if not network or not self.network_type:
            return
        
        print(f"[HTTPayer] Validating network '{network}' for wallet type '{self.network_type}'")

        # Get chainType from config
        network_chain_type = self.network_chain_types.get(network)

        print(f"[HTTPayer] Network chainType: {network_chain_type}")

        # If we don't have config yet, skip validation (will validate after config loads)
        if not network_chain_type:
            return

        # Validate wallet type matches network chainType
        if self.network_type == "evm" and network_chain_type != "evm":
            evm_networks = [
                net for net, chain_type in self.network_chain_types.items()
                if chain_type == "evm"
            ]
            raise ValueError(
                f"Network '{network}' (chainType: {network_chain_type}) is not compatible with EVM wallet. "
                f"EVM networks: {', '.join(evm_networks)}"
                + (f" ({context})" if context else "")
            )

        if self.network_type == "solana" and network_chain_type != "solana":
            solana_networks = [
                net for net, chain_type in self.network_chain_types.items()
                if chain_type == "solana"
            ]
            raise ValueError(
                f"Network '{network}' (chainType: {network_chain_type}) is not compatible with Solana wallet. "
                f"Solana networks: {', '.join(solana_networks)}"
                + (f" ({context})" if context else "")
            )

    def _validate_network(self, network: Optional[str], context: str = "") -> None:
        print(f'[HTTPayer] _validate_network called with network={network} context={context} supported_networks={self.supported_networks}')
        if not network or not self.supported_networks:
            return
        
        print(f'[HTTPayer] Validating network: {network}')
        print(f'[HTTPayer] Supported networks: {self.supported_networks}')

        if network not in self.supported_networks:
            msg = (
                f"Network '{network}' not in supported_networks"
                + (f" ({context})" if context else "")
            )
            if self.strict_networks:
                raise ValueError(msg)
            else:
                print(f"[HTTPayer] Warning: {msg}")

    # def _extract_accept_networks(self, resp) -> list[str]:
    #     try:
    #         if "application/json" not in resp.headers.get("Content-Type", ""):
    #             return []
    #         body = resp.json()
    #         return [
    #             a.get("network")
    #             for a in body.get("accepts", [])
    #             if a.get("network")
    #         ]
    #     except Exception:
    #         return []
        
    def _select_accept_for_network(
        self,
        resp: requests.Response,
        network: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the accept entry matching self.network, if any.
        """
        try:
            if "application/json" not in resp.headers.get("Content-Type", ""):
                return None

            body = resp.json()
            accepts = body.get("accepts", [])

            for a in accepts:
                if a.get("network") == network:
                    return a

            return None
        except Exception:
            return None
        
    def _pay_direct_solana(
        self,
        method: str,
        url: str,
        initial_response: requests.Response,
        effective_network: str,
        timeout: int,
        **kwargs,
    ) -> requests.Response:
        """
        Execute a direct Solana x402 payment against the origin server.

        Args:
            method: HTTP method
            url: Target URL
            initial_response: Initial 402 response with payment requirements
            effective_network: Solana network to use
            timeout: Request timeout
            **kwargs: Additional request parameters

        Returns:
            Response from server after payment
        """
        import asyncio
        from x402_solana.types import PaymentRequirements
        from x402_solana.schemes.exact_svm.client import create_payment_header

        try:
            # Parse payment requirements from 402 response
            payment_data = initial_response.json()

            # Extract accept entry for our network
            accept = None
            for a in payment_data.get("accepts", []):
                if a.get("network") == effective_network:
                    accept = a
                    break

            if not accept:
                raise RuntimeError(
                    f"No payment accept found for network '{effective_network}'"
                )

            # Create PaymentRequirements object
            requirements = PaymentRequirements(**accept)

            # Create payment header (async operation)
            async def _create_header():
                return await create_payment_header(
                    signer=self.solana_keypair,
                    x402_version=1,
                    payment_requirements=requirements,
                    custom_rpc_url=None,  # Use default RPC
                )

            # Run async operation
            payment_header = asyncio.run(_create_header())

            # Make request with payment header
            headers = kwargs.get("headers", {}).copy()
            headers["X-PAYMENT"] = payment_header

            kwargs["headers"] = headers

            # Execute payment request
            return self.session.request(
                method,
                url,
                timeout=timeout,
                **kwargs,
            )

        except Exception as e:
            raise RuntimeError(f"Solana x402 payment failed: {e}") from e

    def _pay_direct_x402(
        self,
        method: str,
        url: str,
        accept: Dict[str, Any],
        effective_network: Optional[str] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Execute a direct EVM x402 payment against the origin server.
        Assumes accept has already been selected + validated for effective_network.
        """
        if self.mode != "relay":
            raise RuntimeError("Direct x402 payment requires relay mode")

        # Validate accept matches the effective network
        if effective_network and accept.get("network") != effective_network:
            raise RuntimeError(
                f"Accept network '{accept.get('network')}' doesn't match "
                f"effective network '{effective_network}'"
            )

        # Delegate to x402 client — it will re-read the accepts internally
        return self.x402_session.request(
            method=method,
            url=url,
            **kwargs,
        )





