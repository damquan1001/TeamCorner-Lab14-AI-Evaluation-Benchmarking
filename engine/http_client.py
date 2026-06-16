import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

HttpTransport = Callable[[str, Dict[str, str], Dict[str, Any], int], Dict[str, Any]]


def post_json_with_retry(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout: int,
    max_retries: int = 5,
    base_delay: float = 2.0,
) -> Dict[str, Any]:
    """POST JSON with exponential backoff on HTTP 429 and transient 5xx errors."""
    data = json.dumps(payload).encode("utf-8")
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code} from {url}: {detail}")
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= max_retries:
                raise last_error from exc
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
        except urllib.error.URLError as exc:
            last_error = RuntimeError(f"Network error calling {url}: {exc}")
            if attempt >= max_retries:
                raise last_error from exc
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)

    raise last_error or RuntimeError(f"Request failed for {url}")
