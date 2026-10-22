import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from skill_chat.contracts import AgentRequest, Scope, Unavailable
from skill_chat.extensions.registry import build_registry
from skill_chat.tools.context import ToolContext


def search_tool(repository):
    return next(tool for tool in build_registry(repository).tools if tool.name == "webiq_search")


@pytest.mark.parametrize("kind,key", [("web", "webResults"), ("news", "newsResults")])
async def test_search_posts_documented_payload_and_preserves_citations(repository, monkeypatch, kind, key):
    repository.settings.webiq_api_key = SecretStr("private-test-key")
    real_client = httpx.AsyncClient

    def respond(request):
        assert str(request.url) == f"https://api.microsoft.ai/v3/search/{kind}"
        assert request.headers["x-apikey"] == "private-test-key"
        payload = json.loads(request.content)
        assert payload == {
            "query": "Cedarbridge strategy",
            "maxResults": 5,
            "language": "ko",
            "region": "KR",
            "contentFormat": "passage",
            "maxLength": 1500,
            **({"safeSearch": "strict"} if kind == "web" else {}),
        }
        return httpx.Response(
            200,
            json={
                key: [
                    {
                        "title": "Strategy announcement",
                        "url": "https://example.com/strategy",
                        "content": "New customer priorities.",
                        "source": "Example News",
                        "lastUpdatedAt": "2026-10-01T00:00:00Z",
                        "crawledAt": "2026-10-02T00:00:00Z",
                    }
                ]
            },
        )

    monkeypatch.setattr(
        "skill_chat.tools.webiq.httpx.AsyncClient",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(respond)),
    )
    tool = search_tool(repository)
    # Binding uses the same registry for a plain background chat and any installed skill.
    for skill_id in (None, "customer-research", "rfp-analysis"):
        registry = build_registry(repository)
        assert "webiq_search" in {
            item.name
            for item in registry.bind_tools(
                AgentRequest("run", Scope("owner", "chat"), "openai", (), skill_id=skill_id)
            )
        }
    result = json.loads(
        await tool.handler(
            tool.arguments.model_validate(
                {
                    "query": "Cedarbridge strategy",
                    "kind": kind,
                    "language": "ko",
                    "region": "KR",
                }
            ),
            ToolContext(Scope("owner", "chat"), "run", None),
        )
    )
    assert result["results"][0]["url"] == "https://example.com/strategy"
    assert result["results"][0]["content"] == "New customer priorities."
    assert result["results"][0]["lastUpdatedAt"] == "2026-10-01T00:00:00Z"
    assert result["results"][0]["crawledAt"] == "2026-10-02T00:00:00Z"
    assert result["results"][0]["source"] == "Example News"
    assert result["kind"] == kind and result["retrieved_at"]
    assert "private-test-key" not in json.dumps(result)


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": " "},
        {"query": "x" * 1001},
        {"query": "test", "kind": "images"},
        {"query": "test", "max_results": 11},
        {"query": "test", "max_results": 0},
        {"query": "test", "endpoint": "https://evil.example"},
        {"query": "test", "api_key": "override"},
        {"query": "test", "region": "Korea"},
    ],
)
def test_search_rejects_invalid_arguments(repository, arguments):
    with pytest.raises(ValidationError):
        search_tool(repository).arguments.model_validate(arguments)


async def test_missing_key_fails_explicitly_without_network(repository):
    tool = search_tool(repository)
    with pytest.raises(Unavailable, match="WEBIQ_API_KEY"):
        await tool.handler(
            tool.arguments.model_validate({"query": "customer"}),
            ToolContext(Scope("owner", "chat"), "run", None),
        )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, text="private-test-key"),
        httpx.Response(429, text="private-test-key"),
        httpx.Response(503, text="private-test-key"),
        httpx.Response(302, headers={"Location": "https://evil.example"}),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"unexpected": []}),
        httpx.Response(200, json={"webResults": [{"title": "Missing URL"}]}),
        httpx.Response(200, content=b"x" * 1_048_577),
    ],
)
async def test_search_errors_are_not_empty_success_or_secret_leaks(repository, monkeypatch, response, caplog):
    repository.settings.webiq_api_key = SecretStr("private-test-key")
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "skill_chat.tools.webiq.httpx.AsyncClient",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(lambda _: response)),
    )
    tool = search_tool(repository)
    with pytest.raises(Unavailable, match="Web IQ") as failure:
        await tool.handler(
            tool.arguments.model_validate({"query": "customer"}),
            ToolContext(Scope("owner", "chat"), "run", None),
        )
    assert "private-test-key" not in str(failure.value)
    assert "private-test-key" not in caplog.text
    assert "Web IQ" in caplog.text


@pytest.mark.parametrize(
    "error_type,message", [(httpx.ReadTimeout, "timed out"), (httpx.ConnectError, "could not connect")]
)
async def test_search_transport_errors_are_visible(repository, monkeypatch, error_type, message):
    repository.settings.webiq_api_key = SecretStr("private-test-key")
    real_client = httpx.AsyncClient

    def timeout(request):
        raise error_type("private-test-key", request=request)

    monkeypatch.setattr(
        "skill_chat.tools.webiq.httpx.AsyncClient",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(timeout)),
    )
    tool = search_tool(repository)
    with pytest.raises(Unavailable, match=message):
        await tool.handler(
            tool.arguments.model_validate({"query": "customer"}),
            ToolContext(Scope("owner", "chat"), "run", None),
        )


@pytest.mark.parametrize(
    "items",
    [
        [],
        [
            {
                "title": "Long page",
                "url": "https://example.com",
                "content": "x" * 9000,
            }
        ]
        * 10,
    ],
)
async def test_search_bounds_content_and_reports_empty_results(repository, monkeypatch, items):
    repository.settings.webiq_api_key = SecretStr("private-test-key")
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "skill_chat.tools.webiq.httpx.AsyncClient",
        lambda **kwargs: real_client(
            **kwargs,
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"webResults": items}),
            ),
        ),
    )
    tool = search_tool(repository)
    output = await tool.handler(
        tool.arguments.model_validate({"query": "customer", "max_results": 10}),
        ToolContext(Scope("owner", "chat"), "run", None),
    )
    result = json.loads(output)
    assert len(output) <= 20000
    assert len(result["results"]) == len(items)
    if items:
        assert len(result["results"][0]["content"]) == 1500
        assert result["results"][0]["content_truncated"] is True
    else:
        assert result["results"] == []


async def test_search_output_budget_discloses_omitted_results(repository, monkeypatch):
    repository.settings.webiq_api_key = SecretStr("private-test-key")
    real_client = httpx.AsyncClient
    items = [
        {
            "title": "t" * 500,
            "url": "https://example.com/" + "u" * 1900,
            "source": "s" * 500,
            "content": "\n" * 1500,
        }
    ] * 12
    monkeypatch.setattr(
        "skill_chat.tools.webiq.httpx.AsyncClient",
        lambda **kwargs: real_client(
            **kwargs,
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"webResults": items}),
            ),
        ),
    )
    tool = search_tool(repository)
    output = await tool.handler(
        tool.arguments.model_validate({"query": "customer", "max_results": 10}),
        ToolContext(Scope("owner", "chat"), "run", None),
    )
    result = json.loads(output)
    assert len(output) <= 20000
    assert 0 < len(result["results"]) < 10
    assert result["results_omitted"] == 12 - len(result["results"])
    assert result["results"][0]["url"] == items[0]["url"]
