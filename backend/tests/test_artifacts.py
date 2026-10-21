import pytest

from skill_chat.artifacts.service import validate_html
from skill_chat.contracts import InvalidInput


@pytest.mark.parametrize(
    "html",
    [
        "<script>alert(1)</script>",
        '<img src="https://example.com/tracker">',
        '<a href="javascript:alert(1)">Open</a>',
        "<style>@import 'https://example.com/a';</style>",
        '<div onclick="bad()">x</div>',
        '<iframe srcdoc="x"></iframe>',
        "<style>div { background: u\\72l(https://example.com); }</style>",
    ],
)
def test_active_html_is_rejected(html):
    with pytest.raises(InvalidInput):
        validate_html(html)


def test_passive_slides_preserve_text():
    result = validate_html(
        "<!doctype html><html><head><style>.slide { color: #123; }</style></head>"
        "<body><section class='slide'><h1>Needs confirmation</h1>"
        "<p>RFP.pdf, page 1</p></section></body></html>"
    )
    assert "Needs confirmation" in result
    assert "RFP.pdf, page 1" in result
