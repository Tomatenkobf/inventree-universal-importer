"""Bounded transport; fixed API destinations and DNS-pinned media requests."""

import ipaddress
import json
import socket
import time
from urllib.parse import urlsplit
import requests
import urllib3
from .normalization import safe_link


class ProviderError(Exception):
    def __init__(self, code, retry_after=0):
        super().__init__(code)
        self.code, self.retry_after = code, retry_after


def read_limited(response, limit, deadline):
    data = bytearray()
    for chunk in response.iter_content(65536):
        if time.monotonic() > deadline:
            raise ProviderError("timeout")
        data.extend(chunk)
        if len(data) > limit:
            raise ProviderError("response_too_large")
    return bytes(data)


class Transport:
    def __init__(self, timeout=8, user_agent="InvenTree-Universal-Importer/0.1"):
        self.timeout = max(1, min(float(timeout), 20))
        self.user_agent = user_agent

    def json(self, method, url, **kwargs):
        # URLs are hardcoded by adapters, never taken from search input.
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        headers.update(kwargs.pop("headers", {}))
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=(self.timeout, self.timeout),
                    stream=True,
                    allow_redirects=False,
                    **kwargs,
                ) as r:
                    if r.status_code == 404:
                        return {}
                    if r.status_code == 429:
                        retry = r.headers.get("Retry-After", "60")
                        raise ProviderError(
                            "rate_limited",
                            min(int(retry) if retry.isdigit() else 60, 3600),
                        )
                    if r.status_code in (401, 403):
                        raise ProviderError("authentication_or_access_denied")
                    if r.status_code != 200:
                        raise ProviderError("upstream_http_error")
                    return json.loads(
                        read_limited(r, 2_000_000, time.monotonic() + self.timeout)
                    )
        except ProviderError:
            raise
        except requests.Timeout:
            raise ProviderError("timeout") from None
        except (requests.RequestException, ValueError):
            raise ProviderError("invalid_response_or_network_error") from None


def media_bytes(url, allowed_hosts, limit=5_000_000):
    if not safe_link(url):
        raise ValueError("Media URL must use HTTPS without credentials")
    parsed = urlsplit(url)
    host = parsed.hostname.lower().rstrip(".")
    if host not in {h.lower().strip() for h in allowed_hosts if h.strip()}:
        raise ValueError("Media host is not on the administrator allowlist")
    addresses = {
        info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    }
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("Media host resolved to a non-public address")
    # Connect to the validated IP while retaining certificate hostname and SNI.
    # No redirects, proxy environment, or second DNS resolution is allowed.
    pool = urllib3.HTTPSConnectionPool(
        sorted(addresses)[0],
        port=443,
        server_hostname=host,
        assert_hostname=host,
        cert_reqs="CERT_REQUIRED",
        timeout=urllib3.Timeout(connect=5, read=5),
        retries=False,
    )
    response = None
    try:
        response = pool.urlopen(
            "GET",
            parsed.path + ("?" + parsed.query if parsed.query else ""),
            headers={"Host": host, "User-Agent": "InvenTree-Universal-Importer/0.1"},
            redirect=False,
            preload_content=False,
        )
        if response.status != 200:
            raise ValueError("Media download failed or redirected")
        chunks = bytearray()
        deadline = time.monotonic() + 15
        for chunk in response.stream(65536, decode_content=True):
            chunks.extend(chunk)
            if len(chunks) > limit or time.monotonic() > deadline:
                raise ValueError("Media exceeds download limits")
        return bytes(chunks)
    finally:
        if response:
            response.close()
        pool.close()
