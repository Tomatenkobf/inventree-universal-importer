import pytest
import requests
from inventree_universal_importer.core.http import Transport, ProviderError


class Response:
    def __init__(self, status=200, body=b"{}", headers=None):
        self.status_code = status
        self.body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_content(self, size):
        yield self.body


class Session:
    trust_env = True

    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def request(self, *args, **kwargs):
        assert kwargs["allow_redirects"] is False and kwargs["stream"] is True
        assert not self.trust_env
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.mark.parametrize(
    "response,code",
    [
        (Response(401), "authentication_or_access_denied"),
        (Response(429, headers={"Retry-After": "600"}), "rate_limited"),
        (Response(302), "upstream_http_error"),
        (Response(body=b"no json"), "invalid_response_or_network_error"),
        (Response(body=b"x" * 2000001), "response_too_large"),
        (requests.Timeout(), "timeout"),
    ],
)
def test_transport_failure(monkeypatch, response, code):
    monkeypatch.setattr(requests, "Session", lambda: Session(response))
    with pytest.raises(ProviderError, match=code):
        Transport().json("GET", "https://example.com")


def test_404(monkeypatch):
    monkeypatch.setattr(requests, "Session", lambda: Session(Response(404)))
    assert Transport().json("GET", "https://example.com") == {}
