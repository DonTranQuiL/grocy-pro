"""Connection parsing and other helpers."""

from __future__ import annotations

import pytest

from custom_components.grocy_pro.helpers import (
    _RequestsWithTimeout,
    connection_from_data,
    ensure_request_timeout,
    extract_base_url_and_path,
    picture_path,
)


@pytest.mark.parametrize(
    ("data", "root"),
    [
        ({"url": "http://grocy.local", "port": 9192}, "http://grocy.local:9192"),
        ({"url": "grocy.local"}, "http://grocy.local:9192"),
        # 2.x doubled the port when it was also typed into the URL
        ({"url": "http://192.168.1.5:9192", "port": 9192}, "http://192.168.1.5:9192"),
        (
            {"url": "https://h.example.com:8443", "port": 443},
            "https://h.example.com:8443",
        ),
        (
            {"url": "https://h.example.com/grocy/", "port": 443},
            "https://h.example.com:443/grocy",
        ),
        ({"url": "http://[fd00::5]:9192"}, "http://[fd00::5]:9192"),
        ({"url": " http://grocy.local ", "port": "80"}, "http://grocy.local:80"),
    ],
)
def test_connection_from_data(data, root) -> None:
    """URLs are normalised into one root URL."""
    connection = connection_from_data({"api_key": " k ", **data})
    assert connection.root_url == root
    assert connection.api_url == f"{root}/api"
    assert connection.api_key == "k"
    assert connection.headers["GROCY-API-KEY"] == "k"
    assert connection.verify_ssl is False


def test_extract_base_url_and_path() -> None:
    """Scheme, host and path are split; the port is dropped."""
    assert extract_base_url_and_path("https://a.b:1/x/y/") == ("https://a.b", "x/y")
    assert extract_base_url_and_path("a.b") == ("http://a.b", "")


def test_picture_path() -> None:
    """Picture names are base64 encoded into the proxy URL."""
    assert picture_path("productpictures", None) is None
    assert picture_path("productpictures", "") is None
    assert (
        picture_path("recipepictures", "pizza.jpg")
        == "/api/grocy_pro/recipepictures/cGl6emEuanBn"
    )


def test_request_timeout_wrapper() -> None:
    """The requests wrapper adds a timeout but keeps explicit ones."""
    calls = []

    class FakeRequests:
        RequestException = RuntimeError

        @staticmethod
        def get(url, **kwargs):
            calls.append(kwargs)

    wrapped = _RequestsWithTimeout(FakeRequests, 7)
    wrapped.get("u")
    wrapped.get("u", timeout=1)
    assert calls == [{"timeout": 7}, {"timeout": 1}]
    assert wrapped.RequestException is RuntimeError

    from custom_components.grocy_pro.vendor.grocy import grocy_api_client

    ensure_request_timeout()
    ensure_request_timeout()
    assert isinstance(grocy_api_client.requests, _RequestsWithTimeout)
    assert not isinstance(grocy_api_client.requests._module, _RequestsWithTimeout)
