# LogVault Python SDK

[![PyPI version](https://img.shields.io/pypi/v/logvault.svg)](https://pypi.org/project/logvault/)
[![Python versions](https://img.shields.io/pypi/pyversions/logvault.svg)](https://pypi.org/project/logvault/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Official Python client for [LogVault](https://logvault.eu) — Audit-Log-as-a-Service for B2B SaaS. SOC 2, GDPR, and ISO 27001 compliant. Hosted in the EU.

## Installation

```bash
pip install logvault
```

## Quick Start

```python
from logvault import Client

client = Client("your-api-key")

# Log an audit event
event = client.log(
    action="user.login",
    user_id="user_123",
    resource="auth",
    metadata={"ip": "192.168.1.1", "method": "password"}
)

print(f"Logged: {event['id']}")
```

## Features

- **Sync & Async** — Both `Client` and `AsyncClient` available
- **Automatic Retries** — Exponential backoff with jitter
- **Input Validation** — Action format and payload size checks
- **Error Handling** — Typed exceptions for auth, rate limits, validation
- **Replay Protection** — Optional nonce support

## Usage

### Async Client

```python
import asyncio
from logvault import AsyncClient

async def main():
    async with AsyncClient("your-api-key") as client:
        event = await client.log(
            action="document.create",
            user_id="user_456",
            resource="document:789",
            metadata={"title": "Q4 Report"}
        )

asyncio.run(main())
```

### List Events

```python
# Get recent events
response = client.list_events(page=1, page_size=50)

for event in response['events']:
    print(f"{event['timestamp']} - {event['action']}")

# Filter by user or action
user_events = client.list_events(user_id="user_123")
login_events = client.list_events(action="user.login")
```

### Error Handling

```python
from logvault import Client, AuthenticationError, RateLimitError, APIError

client = Client("your-api-key")

try:
    event = client.log(action="user.login", user_id="user_123")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except APIError as e:
    print(f"API error: {e.status_code}")
```

### Configuration Options

```python
client = Client(
    api_key="your-api-key",
    base_url="https://api.logvault.eu",  # Default
    timeout=30,                           # Request timeout (seconds)
    enable_nonce=True,                    # Replay protection
    max_retries=3                         # Retry attempts
)
```

## Action Format

Actions follow the pattern `entity.verb`:

| Category    | Examples                                               |
| ----------- | ------------------------------------------------------ |
| Auth        | `user.login`, `user.logout`, `user.password_reset`     |
| Documents   | `document.create`, `document.read`, `document.delete`  |
| Permissions | `permission.grant`, `permission.revoke`, `role.assign` |
| Data        | `data.export`, `data.delete`                           |

## Requirements

- Python 3.8+
- `requests` (sync client)
- `aiohttp` (async client)

## Links

- [Documentation](https://logvault.eu/docs)
- [API Reference](https://logvault.eu/docs/api)
- [GitHub](https://github.com/Rul1an/logvault-python)
- [PyPI](https://pypi.org/project/logvault/)

## License

MIT — see [LICENSE](LICENSE) for details.
