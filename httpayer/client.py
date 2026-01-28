"""
Copyright (c) 2026 HTTPayer, Inc. All rights reserved.
Licensed under the HTTPayer SDK License – see LICENSE.md.
"""

import os
import time
import requests
from typing import Optional, Dict, Any, Literal

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3
from httpayer._vendor.x402.clients.requests import x402_requests

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
        """
        Initialize HTTPayer client with automatic mode detection.

        Mode is auto-detected based on credentials:
        - "relay" mode: When private_key or account is provided (self-custodial)
        - "proxy" mode: When only api_key is provided (custodial)

        Args:
            router_url: HTTPayer router URL. Defaults to https://api.httpayer.com or X402_ROUTER_URL env var.
            api_key: API key for proxy mode. Defaults to HTTPAYER_API_KEY env var.
            private_key: Private key for relay mode. Supports EVM (hex), Solana (base58/hex/JSON array).
            account: Pre-configured EVM Account object for relay mode.
            network: Default network for relay payments (e.g., "base", "solana"). Auto-detects to "base" for EVM wallets and "solana" for Solana wallets if not provided.
            timeout: Request timeout in seconds. Defaults to 600 (10 minutes).
            use_session: Use requests.Session for connection pooling. Defaults to True.
            strict_networks: Raise error for unsupported networks. Defaults to True.
            response_mode: Response format - "text" (unwrapped) or "json" (wrapped). Defaults to "text".
            privacy_mode: Route through HTTPayer relay for privacy. When False, attempts direct x402 payment. Defaults to True.

        Raises:
            ValueError: If response_mode is invalid, private_key format is invalid, or network is incompatible with wallet type.
            ValueError: If proxy mode is detected but HTTPAYER_API_KEY is missing.

        Examples:
            >>> # Proxy mode (API key)
            >>> client = HTTPayerClient(api_key="your-api-key")

            >>> # Relay mode (EVM private key) - auto-detects network="base"
            >>> client = HTTPayerClient(private_key="0x...")

            >>> # Relay mode (Solana private key) - auto-detects network="solana"
            >>> client = HTTPayerClient(private_key="base58-key")

            >>> # Relay mode with explicit network override
            >>> client = HTTPayerClient(private_key="0x...", network="base-sepolia")
        """
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

            # Set default network if not provided
            if not self.network:
                self.network = "base"
        elif private_key:
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
                solana_errors = []
                
                # Try JSON array format first (solana-keygen default format)
                try:
                    import json
                    keypair_bytes = json.loads(private_key)
                    if isinstance(keypair_bytes, list) and len(keypair_bytes) == 64:
                        # Convert to hex string (first 32 bytes are the private key)
                        hex_key = bytes(keypair_bytes[:32]).hex()
                        self.solana_keypair = create_signer_from_hex(hex_key)
                        self.account_address = str(self.solana_keypair.pubkey())
                        self.network_type = "solana"
                        wallet_detected = True
                except Exception as e:
                    solana_errors.append(f"json_array: {e}")
                
                # Try base58 format (standard Solana format)
                if not wallet_detected:
                    try:
                        self.solana_keypair = create_signer_from_base58(private_key)
                        self.account_address = str(self.solana_keypair.pubkey())
                        self.network_type = "solana"
                        wallet_detected = True
                    except Exception as e:
                        solana_errors.append(f"base58: {e}")
                    
                # If base58 failed, try hex format
                if not wallet_detected:
                    try:
                        self.solana_keypair = create_signer_from_hex(private_key)
                        self.account_address = str(self.solana_keypair.pubkey())
                        self.network_type = "solana"
                        wallet_detected = True
                    except Exception as e:
                        solana_errors.append(f"hex: {e}")

            if not wallet_detected:
                raise ValueError(
                    "Invalid private key: not a valid EVM (hex) or Solana (base58/hex/JSON array) private key"
                )

            self.mode = "relay"

            # Set default network based on detected wallet type if not provided
            if not self.network:
                if self.network_type == "evm":
                    self.network = "base"
                elif self.network_type == "solana":
                    self.network = "solana"
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

        self._validate_network(self.network, context="default network (pre-config)")


    # ------------------------------------------------------------------
    # Public helpers (relay + proxy mode compatible)
    # ------------------------------------------------------------------

    def pay_invoice(
        self,
        api_method: str,
        api_url: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
        network: Optional[str] = None,
    ) -> requests.Response:
        """
        Execute payment for a 402-protected resource without attempting a direct call first.

        Directly calls the HTTPayer router (proxy mode) or relay endpoint (relay mode)
        to pay the invoice and retrieve the protected resource.

        Args:
            api_method: HTTP method (GET, POST, PUT, DELETE, etc.).
            api_url: Target API URL to access.
            api_payload: JSON payload for POST/PUT requests.
            api_params: Query parameters to include.
            api_headers: Custom headers to send with the request.
            network: Network override for relay mode payments.

        Returns:
            Response from the target API after successful payment.

        Raises:
            ValueError: If network is incompatible with wallet type or not supported.

        Examples:
            >>> client = HTTPayerClient()
            >>> response = client.pay_invoice("GET", "https://api.example.com/data")
            >>> print(response.json())
        """
        # Validate network override compatibility with wallet type
        if network and self.network_type:
            self._validate_network_type_compatibility(network, "pay_invoice network override")

        self._validate_network(network, context="pay_invoice network override")

        # Route based on mode
        if self.mode == "relay":
            return self._call_relay(
                self.relay_url,
                api_url,
                api_method,
                api_payload or {},
                api_params or {},
                api_headers or {},
                self.timeout,
                network if network is not None else self.network,
            )
        else:
            return self._call_router(
                self.pay_url,
                api_url,
                api_method,
                api_payload,
                api_params,
                api_headers,
                self.timeout,
            )

    def simulate_invoice(
        self,
        api_method: str,
        api_url: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
        network: Optional[str] = None,
    ) -> requests.Response:
        """
        Simulate payment for a 402-protected resource without executing actual payment.

        Returns payment requirements and cost estimation without spending funds.
        Useful for previewing payment details before committing.

        Args:
            api_method: HTTP method (GET, POST, PUT, DELETE, etc.).
            api_url: Target API URL to simulate access.
            api_payload: JSON payload for POST/PUT requests.
            api_params: Query parameters to include.
            api_headers: Custom headers to send with the request.
            network: Network override for relay mode simulation.

        Returns:
            Response containing payment requirements and simulation details.

        Raises:
            ValueError: If network is incompatible with wallet type or not supported.

        Examples:
            >>> client = HTTPayerClient()
            >>> sim = client.simulate_invoice("GET", "https://api.example.com/data")
            >>> print(f"Cost: {sim.json()['relayFeeBreakdown']['totalAmount']}")
        """
        # Validate network override compatibility with wallet type
        if network and self.network_type:
            self._validate_network_type_compatibility(network, "simulate_invoice network override")

        self._validate_network(network, context="simulate_invoice network override")

        # Route based on mode
        if self.mode == "relay":
            return self._call_relay(
                self.relay_sim_url,
                api_url,
                api_method,
                api_payload or {},
                api_params or {},
                api_headers or {},
                self.timeout,
                network if network is not None else self.network,
            )
        else:
            return self._call_router(
                self.sim_url,
                api_url,
                api_method,
                api_payload,
                api_params,
                api_headers,
                self.timeout,
            )

    def get_balance(self, api_key: Optional[str] = None) -> requests.Response:
        """
        Get account balance for proxy mode.

        Retrieves the current balance and usage information for the API key account.
        Only available in proxy mode.

        Args:
            api_key: Override the default API key. Uses instance api_key if not provided.

        Returns:
            Dict containing balance information (USDC amount, usage stats, etc.).

        Raises:
            RuntimeError: If called in relay mode (balance endpoint is proxy-only).

        Examples:
            >>> client = HTTPayerClient(api_key="your-key")
            >>> balance = client.get_balance()
            >>> print(f"Balance: {balance['balance']} Credits")
        """
        if self.mode != "proxy":
            raise RuntimeError("Balance endpoint only available in proxy mode")

        headers = {"x-api-key": api_key or self.api_key}
        return self.session.get(
            self.balance_url,
            headers=headers,
            timeout=self.timeout,
        ).json()

    def get_relay_limits(self) -> requests.Response:
        """
        Get usage limits and quotas for relay mode.

        Retrieves spending limits, daily/monthly quotas, and current usage
        for the wallet address in relay mode. Only available in relay mode.

        Returns:
            Dict containing relay limits (daily limit, used amount, remaining, etc.).

        Raises:
            RuntimeError: If called in proxy mode (relay limits are relay-only).

        Examples:
            >>> client = HTTPayerClient(private_key="0x...", network="base")
            >>> limits = client.get_relay_limits()
            >>> print(f"Daily limit: {limits['dailyLimit']} USDC")
        """
        if self.mode != "relay":
            raise RuntimeError("Relay limits only available in relay mode")

        return self.session.get(
            self.relay_limits_url,
            timeout=self.timeout,
        ).json()
    
    def refresh_config(self) -> None:
        """
        Refresh HTTPayer configuration from the server.

        Fetches the latest supported networks, chain types, and router configuration.
        Useful if supported networks change or you want to re-validate network settings.

        Examples:
            >>> client = HTTPayerClient()
            >>> client.refresh_config()
            >>> print(f"Supported networks: {client.supported_networks}")
        """
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
        """
        Unified request interface that handles 402 Payment Required responses automatically.

        First attempts a direct request to the target URL. If it returns 402, automatically
        handles payment through the appropriate flow (relay or proxy) and returns the resource.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            url: Target API URL to access.
            simulate: If True, only simulate payment without executing (dry-run). Defaults to False.
            response_mode: Override response format ("text" or "json"). Uses instance default if not specified.
            network: Override network for relay mode payments.
            **kwargs: Additional request arguments. Common options:
                - json: JSON payload (forwarded through HTTPayer payment flow)
                - params: Query parameters (forwarded through HTTPayer)
                - headers: Custom headers (forwarded through HTTPayer)
                - timeout: Request timeout override (forwarded through HTTPayer)
                - Other kwargs (data, files, auth, cookies, etc.) are only used for the
                  initial direct request attempt and NOT forwarded through HTTPayer payment flow.

        Returns:
            Response from the target API. If 402 is encountered, returns response after payment.

        Raises:
            ValueError: If network is incompatible with wallet type or not supported.

        Examples:
            >>> client = HTTPayerClient()

            >>> # Basic request - auto-handles 402
            >>> response = client.request("GET", "https://api.example.com/data")
            >>> print(response.json())

            >>> # Simulate first to check cost
            >>> sim = client.request("GET", "https://api.example.com/data", simulate=True)
            >>> print(f"Cost: {sim.json()['relayFeeBreakdown']['totalAmount']}")

            >>> # POST with payload
            >>> response = client.request(
            ...     "POST",
            ...     "https://api.example.com/process",
            ...     json={"input": "data"}
            ... )

            >>> # Override network for this request
            >>> response = client.request("GET", url, network="solana-devnet")
        """
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

    def _retry_payment_request(
        self,
        request_func,
        max_retries: int = 5,
        retry_delay: float = 1,
    ) -> requests.Response:
        """
        Retry a request if it gets 402 Payment Required.

        The first 402 triggers the payment, subsequent requests should succeed.

        Args:
            request_func: Callable that returns a requests.Response
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries

        Returns:
            Response from the request (may be 402 if all retries exhausted)
        """
        response = None
        for attempt in range(max_retries):
            response = request_func()

            if response.status_code == 402:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Return the 402 response instead of raising exception
                    # This allows caller to see the actual error details
                    return response

            # Success or other error
            return response

        return response

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

        # Only use retry logic for EVM networks
        if self.network_type == "evm":
            resp = self._retry_payment_request(
                lambda: self.x402_session.post(
                    endpoint,
                    json=data,
                    timeout=effective_timeout,
                )
            )
        else:
            # Solana: no retry logic
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

        # Get chainType from config
        network_chain_type = self.network_chain_types.get(network)

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
        if not network or not self.supported_networks:
            return

        if network not in self.supported_networks:
            msg = (
                f"Network '{network}' not in supported_networks"
                + (f" ({context})" if context else "")
            )
            if self.strict_networks:
                raise ValueError(msg)

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
        from httpayer.x402_solana.types import PaymentRequirements
        from httpayer.x402_solana.schemes.exact_svm.client import create_payment_header

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

            # Run async operation (handle both Jupyter and regular environments)
            try:
                # Try to get existing event loop (Jupyter notebooks)
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Jupyter/IPython environment - use nest_asyncio
                    import nest_asyncio
                    nest_asyncio.apply()
                    payment_header = asyncio.run(_create_header())
                else:
                    # Event loop exists but not running
                    payment_header = loop.run_until_complete(_create_header())
            except RuntimeError:
                # No event loop exists - create one (standard Python)
                payment_header = asyncio.run(_create_header())

            # Make request with payment header
            headers = kwargs.get("headers", {}).copy()
            headers["X-PAYMENT"] = payment_header

            kwargs["headers"] = headers

            # Execute payment request (no retry for Solana)
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

        # Delegate to x402 client with retry logic
        return self._retry_payment_request(
            lambda: self.x402_session.request(
                method=method,
                url=url,
                **kwargs,
            )
        )





