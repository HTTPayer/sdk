import requests
from dotenv import load_dotenv
import os
from typing import Optional, Dict, Any
import time

load_dotenv()

class HTTPayerClient:
    """
    Unified HTTPayer client for managing 402 responses, x402 payments,
    and dry-run simulation calls.

    If response_mode is set to "json", responses from the httpayer router that look like:
        { "success": true, "result": <string|object> }
    Else responses will be unwrapped so .text/.json() behave as if you called the origin directly.
    """

    def __init__(
        self,
        router_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 60 * 10,
        use_session: bool = True,
        response_mode: str = "text",
    ):
        if response_mode not in ("json", "text"):
            raise ValueError(f"Invalid response_mode: {response_mode}, must be 'json' or 'text'")

        self.response_mode = response_mode

        base_url = router_url or os.getenv("X402_ROUTER_URL", "https://api.httpayer.com")
        self.base_url = base_url.rstrip("/").removesuffix("/proxy")

        suffix = "?format=json" if self.response_mode == "json" else ""
        self.pay_url = f"{self.base_url}/proxy{suffix}"
        self.sim_url = f"{self.base_url}/sim{suffix}"

        self.timeout = timeout
        self.session = requests.Session() if use_session else requests

        self.api_key = api_key or os.getenv("HTTPAYER_API_KEY")
        if not self.base_url or not self.api_key:
            missing = []
            if not self.base_url:
                missing.append("X402_ROUTER_URL")
            if not self.api_key:
                missing.append("HTTPAYER_API_KEY")
            raise ValueError(f"Missing configuration: {', '.join(missing)}")

    # -------------------------------
    # Public helpers
    # -------------------------------

    def pay_invoice(
        self,
        api_method: str,
        api_url: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Pay a 402 payment (via router service).
        
        Args:
            api_method (str): HTTP method to use for the original API call (GET, POST, etc).
            api_url (str): Full URL of the original API call that returned 402.
            api_payload (Optional[Dict[str, Any]]): Payload to include in the payment request.
            api_params (Optional[Dict[str, Any]]): Query parameters for the payment request.
            api_headers (Optional[Dict[str, str]]): Headers to include in the payment request.

        Returns:
            requests.Response: The HTTP response from the payment request.

        """
        return self._call_router(self.pay_url, api_url, api_method, api_payload, api_params, api_headers)

    def simulate_invoice(
        self,
        api_method: str,
        api_url: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Dry-run simulation call: returns payment requirements without paying."""
        resp = self._call_router(self.sim_url, api_url, api_method, api_payload, api_params, api_headers)
        return resp

    # -------------------------------
    # Unified request interface
    # -------------------------------

    def request(self, method: str, url: str, simulate: bool = False, response_mode: Optional[str] = None, **kwargs) -> requests.Response:
        """
        Perform an HTTP request that auto-handles 402 flows.

        If simulate=True, will call /sim on 402; otherwise /pay.
        Returns a requests.Response. If unwrap_proxy_result=True and the /pay proxy
        returned {success,result}, this will be unwrapped to look like the origin response.

        Args:
            method (str): HTTP method (GET, POST, etc)
            url (str): Full URL to call
            simulate (bool): If True, route 402s through /sim instead of /pay
            **kwargs: Additional args passed to requests.request()

        Returns:
            requests.Response: The HTTP response object.

        """
        effective_timeout = kwargs.pop("timeout", self.timeout)

        # First try direct
        resp = self.session.request(method, url, timeout=effective_timeout, **kwargs)

        # If 402, route through httpayer
        if resp.status_code == 402:
            api_payload = kwargs.get("json") or {}
            api_params = kwargs.get("params") or {}
            api_headers = kwargs.get("headers") or {}

            endpoint = self.sim_url if simulate else self.pay_url

            active_mode = response_mode or self.response_mode

            if active_mode == "json" and "format=json" not in endpoint:
                endpoint = f"{endpoint}?format=json"

            resp = self._call_router(endpoint, url, method, api_payload, api_params, api_headers)

        return resp

    # -------------------------------
    # Internal helpers
    # -------------------------------

    def _call_router(
        self,
        endpoint: str,
        api_url: str,
        api_method: str,
        api_payload: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        api_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Helper to POST to /pay or /sim with proper auth + body."""
        data = {
            "api_url": api_url,
            "method": api_method,
            "payload": api_payload or {},
        }
        if api_params:
            data["params"] = api_params
        if api_headers:
            data["headers"] = api_headers

        header = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        resp = self.session.post(endpoint, headers=header, json=data, timeout=self.timeout)
        
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
            if poll.status_code == 200:
                print(f"[httpayer] async task complete in {time.time() - start:.1f}s")
                return poll
            elif poll.status_code == 202:
                if time.time() - start > self.timeout:
                    raise TimeoutError(f"Webhook polling exceeded {self.timeout}s")
                time.sleep(3)
            elif poll.status_code == 500:
                try:
                    err = poll.json().get("error", poll.text)
                except Exception:
                    err = poll.text
                raise RuntimeError(f"Async task failed: {err}")
            else:
                raise RuntimeError(f"Unexpected async poll status: {poll.status_code}")
