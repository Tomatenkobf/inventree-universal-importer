import socket
import pytest
from inventree_universal_importer.core.http import media_bytes
from inventree_universal_importer.inventree_adapter.version_detection import status


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "::1",
        "::ffff:127.0.0.1",
        "192.168.1.10",
    ],
)
def test_media_private_dns(monkeypatch, ip):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", (ip, 443))]
    )
    with pytest.raises(ValueError, match="non-public"):
        media_bytes("https://allowed.example/a", ["allowed.example"])


@pytest.mark.parametrize(
    "url",
    [
        "http://allowed.example/a",
        "https://evil.example/a",
        "https://user@allowed.example/a",
        "file:///etc/passwd",
    ],
)
def test_media_url_rejected(url):
    with pytest.raises(ValueError):
        media_bytes(url, ["allowed.example"])


def test_mixed_dns_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", (ip, 443)) for ip in ("8.8.8.8", "127.0.0.1")],
    )
    with pytest.raises(ValueError):
        media_bytes("https://allowed.example/a", ["allowed.example"])


def test_compatibility():
    assert status("1.5.6")["allowed"]
    assert status("1.7.0")["allowed"]
    assert not status("1.7.1")["allowed"]
    assert not status("1.7.0rc1")["allowed"]
    assert not status("1.6.0")["allowed"]
    assert not status("2.0.0")["tested"]
    assert not status("invalid")["allowed"]


def test_media_pins_ip_and_rejects_redirect(monkeypatch):
    import urllib3

    calls = {}
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443))]
    )

    class Response:
        status = 302

        def close(self):
            calls["closed"] = True

    class Pool:
        def __init__(self, ip, **kwargs):
            calls.update(ip=ip, options=kwargs)

        def urlopen(self, *args, **kwargs):
            calls["request"] = kwargs
            return Response()

        def close(self):
            calls["pool_closed"] = True

    monkeypatch.setattr(urllib3, "HTTPSConnectionPool", Pool)
    with pytest.raises(ValueError, match="redirected"):
        media_bytes("https://allowed.example/image", ["allowed.example"])
    assert calls["ip"] == "8.8.8.8"
    assert calls["options"]["assert_hostname"] == "allowed.example"
    assert calls["options"]["server_hostname"] == "allowed.example"
    assert calls["request"]["redirect"] is False
    assert calls["request"]["headers"]["Host"] == "allowed.example"
    assert calls["closed"] and calls["pool_closed"]
