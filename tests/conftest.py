from typing import Any

import httpx2
import pytest

from semble import AsyncSemble, Semble


class Recorder:
    """captures requests and replays a canned json response."""

    def __init__(self, response_json: Any = None, status_code: int = 200) -> None:
        self.requests: list[httpx2.Request] = []
        self.response_json = response_json if response_json is not None else {}
        self.status_code = status_code

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return httpx2.Response(self.status_code, json=self.response_json)

    @property
    def last(self) -> httpx2.Request:
        return self.requests[-1]


@pytest.fixture
def sync_client():
    def make(response_json: Any = None, status_code: int = 200, **kwargs: Any):
        recorder = Recorder(response_json, status_code)
        http = httpx2.Client(transport=httpx2.MockTransport(recorder.handler))
        kwargs.setdefault("api_key", "sk_test")
        return Semble(http_client=http, **kwargs), recorder

    return make


@pytest.fixture
def async_client():
    def make(response_json: Any = None, status_code: int = 200, **kwargs: Any):
        recorder = Recorder(response_json, status_code)
        http = httpx2.AsyncClient(transport=httpx2.MockTransport(recorder.handler))
        kwargs.setdefault("api_key", "sk_test")
        return AsyncSemble(http_client=http, **kwargs), recorder

    return make
