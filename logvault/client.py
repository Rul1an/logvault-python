import os
import json
import logging
import asyncio
import random
import re
from typing import Optional, Dict, Any, Tuple, Union
from datetime import datetime

# 3rd party
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import aiohttp

# Internal
from .exceptions import APIError, AuthenticationError, ValidationError, RateLimitError

# Try to get version dynamically, fallback to dev
try:
    from importlib.metadata import version
    __version__ = version("logvault")
except ImportError:
    __version__ = "0.2.5-dev"

# Regex for "domain.event" format
ACTION_REGEX = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$", re.IGNORECASE)

class Client:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.logvault.eu",
        timeout: Tuple[float, float] = (5.0, 10.0), # Connect, Read
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Pre-validate Key format
        if not self.api_key.startswith(("lv_live_", "lv_test_")):
             # We log a warning but don't crash, in case key formats change later
             logging.warning("[LogVault] API key does not start with expected prefix.")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"logvault-python/{__version__}",
            "X-Client-Version": __version__
        }

        # Setup Robust Session with Retries (Sync)
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Retry Strategy: 429, 500, 502, 503, 504
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1, # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "info",
        message: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:

        # 1. Validation
        if not ACTION_REGEX.match(action):
            raise ValidationError(f"Invalid action format '{action}'. Expected 'domain.event'")

        payload = {
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "metadata": metadata or {},
            "level": level,
            "message": message,
            "timestamp": timestamp.isoformat() if timestamp else datetime.utcnow().isoformat()
        }

        # 2. Fail-Safe Serialization
        try:
            json_payload = json.dumps(payload)
            if len(json_payload) > 1024 * 1024: # 1MB Limit
                raise ValidationError("Payload size exceeds 1MB")
        except (TypeError, ValueError) as e:
            if isinstance(e, ValidationError): raise e
            # Fail silently to avoid crashing app
            logging.error(f"[LogVault] Serialization failed: {e}")
            return None

        # 3. Request (Retries handled by Adapter)
        try:
            response = self.session.post(
                f"{self.base_url}/v1/events",
                data=json_payload, # Use pre-dumped string
                timeout=self.timeout
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")

            if response.status_code == 422:
                raise ValidationError(f"Validation failed: {response.text}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            # Clean Error Message
            raise APIError(f"LogVault Connection Error: {type(e).__name__}") from e

    def list_events(
        self,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[str] = None,
        action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List audit events with optional filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Number of events per page (max 100)
            user_id: Filter by user ID
            action: Filter by action (supports wildcards with *)

        Returns:
            Dict with 'events', 'total', 'page', 'page_size', 'has_next'
        """
        params = {
            "page": page,
            "page_size": min(page_size, 100)
        }
        if user_id:
            params["user_id"] = user_id
        if action:
            params["action"] = action

        try:
            response = self.session.get(
                f"{self.base_url}/v1/events",
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise APIError(f"LogVault Connection Error: {type(e).__name__}") from e

    def get_event(self, event_id: str) -> Dict[str, Any]:
        """
        Get a single audit event by ID.

        Args:
            event_id: The UUID of the event

        Returns:
            Dict with event details
        """
        try:
            response = self.session.get(
                f"{self.base_url}/v1/events/{event_id}",
                timeout=self.timeout
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            if response.status_code == 404:
                raise APIError(f"Event not found: {event_id}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise APIError(f"LogVault Connection Error: {type(e).__name__}") from e

    def verify_event(self, event_id: str) -> Dict[str, Any]:
        """
        Verify the cryptographic signature of an audit event.

        Args:
            event_id: The UUID of the event to verify

        Returns:
            Dict with 'valid' (bool) and verification details
        """
        try:
            response = self.session.get(
                f"{self.base_url}/v1/events/{event_id}/verify",
                timeout=self.timeout
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            if response.status_code == 404:
                raise APIError(f"Event not found: {event_id}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise APIError(f"LogVault Connection Error: {type(e).__name__}") from e

    def search_events(
        self,
        query: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search audit events using semantic search.

        Args:
            query: Natural language search query (e.g., "failed login attempts")
            limit: Maximum number of results (default 20)

        Returns:
            Dict with 'results', 'count', 'has_embeddings'
        """
        if len(query) < 2:
            raise ValidationError("Query must be at least 2 characters")

        try:
            response = self.session.get(
                f"{self.base_url}/v1/events/search",
                params={"q": query, "limit": limit},
                timeout=self.timeout
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise APIError(f"LogVault Connection Error: {type(e).__name__}") from e

class AsyncClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.logvault.eu",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"logvault-python-async/{__version__}",
            "X-Client-Version": __version__
        }
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(headers=self.headers, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def log(self, action: str, **kwargs):
        if not self._session:
            # Auto-create session if not using context manager (but warn user)
            self._session = aiohttp.ClientSession(headers=self.headers, timeout=self.timeout)

        # Validation & Serialization logic (Same as Sync)
        if not ACTION_REGEX.match(action):
             raise ValidationError(f"Invalid action format '{action}'")

        payload = {"action": action, **kwargs}
        if "metadata" not in payload: payload["metadata"] = {}

        try:
            json_data = payload # aiohttp handles serialization, but we check size?
            # Ideally verify serializability first:
            json.dumps(payload)
        except Exception as e:
             logging.error(f"[LogVault] Serialization failed: {e}")
             return None

        url = f"{self.base_url}/v1/events"
        attempt = 0

        # Async Retry Loop
        while True:
            try:
                async with self._session.post(url, json=payload) as response:
                    if response.status == 200 or response.status == 201:
                        return await response.json()

                    if response.status == 401:
                        raise AuthenticationError("Invalid API key")
                    if response.status == 422:
                        txt = await response.text()
                        raise ValidationError(f"Validation failed: {txt}")

                    # Retry on 429 or 5xx
                    if attempt < self.max_retries and (response.status == 429 or response.status >= 500):
                        raise aiohttp.ClientError(f"Server error {response.status}")

                    # Permanent fail
                    raise APIError(f"HTTP {response.status}")

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                attempt += 1
                if attempt > self.max_retries:
                    raise APIError(f"Connection failed after {self.max_retries} retries: {type(e).__name__}") from e

                # Exponential Backoff + Jitter
                delay = (2 ** attempt) + (random.randint(0, 1000) / 1000)
                await asyncio.sleep(delay)

    async def list_events(
        self,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[str] = None,
        action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List audit events with optional filtering (async).
        """
        if not self._session:
            self._session = aiohttp.ClientSession(headers=self.headers, timeout=self.timeout)

        params = {"page": page, "page_size": min(page_size, 100)}
        if user_id:
            params["user_id"] = user_id
        if action:
            params["action"] = action

        async with self._session.get(f"{self.base_url}/v1/events", params=params) as response:
            if response.status == 401:
                raise AuthenticationError("Invalid API key")
            if response.status != 200:
                raise APIError(f"HTTP {response.status}")
            return await response.json()

    async def search_events(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search audit events using semantic search (async).
        """
        if not self._session:
            self._session = aiohttp.ClientSession(headers=self.headers, timeout=self.timeout)

        if len(query) < 2:
            raise ValidationError("Query must be at least 2 characters")

        async with self._session.get(
            f"{self.base_url}/v1/events/search",
            params={"q": query, "limit": limit}
        ) as response:
            if response.status == 401:
                raise AuthenticationError("Invalid API key")
            if response.status != 200:
                raise APIError(f"HTTP {response.status}")
            return await response.json()
