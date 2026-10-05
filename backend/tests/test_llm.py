import json

import httpx
import pytest

from app.llm import LLMUnavailable, OpenAICompatibleClient

MESSAGES = [{"role": "user", "content": "Hi"}]


def client_with(handler, api_key="test-key"):
    return OpenAICompatibleClient("https://llm.example/v1", api_key, "test-model",
                                  transport=httpx.MockTransport(handler))


def test_sends_openai_style_request_and_reads_answer():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "  Hello [1]. "}}]})

    assert client_with(handler).complete(MESSAGES) == "Hello [1]."
    assert seen["url"] == "https://llm.example/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "test-model" and seen["body"]["messages"] == MESSAGES


def test_missing_api_key():
    with pytest.raises(LLMUnavailable, match="No LLM API key"):
        client_with(lambda r: httpx.Response(200), api_key="").complete(MESSAGES)


@pytest.mark.parametrize("status, message", [(429, "quota"), (500, "LLM error 500")])
def test_http_errors_become_llm_unavailable(status, message):
    with pytest.raises(LLMUnavailable, match=message):
        client_with(lambda r: httpx.Response(status, text="nope")).complete(MESSAGES)


def test_network_failure():
    def handler(request):
        raise httpx.ConnectError("no route to host")

    with pytest.raises(LLMUnavailable, match="Could not reach"):
        client_with(handler).complete(MESSAGES)


def test_unexpected_response_shape():
    with pytest.raises(LLMUnavailable, match="couldn't read"):
        client_with(lambda r: httpx.Response(200, json={"weird": True})).complete(MESSAGES)
