"""The one mail sender, and its two branches (APRAS-71 D10, D11).

`app/core/mail.py` is the extraction of the inline Resend block that used to
live in `auth.forgot_password`. It reads `RESEND_API_KEY` with `os.getenv`
**at call time**, so a test needs no settings surgery, and it never raises:
with the key absent, or on any exception from Resend, it reports failure and
lets its caller print instead.

The suite runs with `RESEND_API_KEY` unset, so the print branch is the tested
one everywhere else; here both branches are exercised, and the no-key branch
is proven to make **no** HTTP call by patching `httpx.AsyncClient.post` to
fail the test.
"""

import asyncio

import httpx
import pytest

from app.core import mail


def _run(coro):
    """Run one coroutine. The suite has no async plugin, and needs none."""
    return asyncio.run(coro)


@pytest.fixture(name="forbid_post")
def forbid_post_fixture(monkeypatch):
    """Any HTTP POST at all fails the test that installed this."""

    async def _boom(*_args, **_kwargs):
        raise AssertionError("send_email made an HTTP request")

    monkeypatch.setattr(httpx.AsyncClient, "post", _boom)


class _Response:
    """The slice of `httpx.Response` the sender touches."""

    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises

    def raise_for_status(self) -> None:
        if self.raises:
            raise httpx.HTTPError("502 from Resend")


def test_without_an_api_key_it_prints_and_makes_no_request(
    monkeypatch, capsys, forbid_post
):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    sent = _run(mail.send_email("alguem@example.com", "Assunto", "<p>oi</p>"))

    assert sent is False
    assert "Failed to send email via Resend" not in capsys.readouterr().out


def test_with_an_api_key_it_posts_to_resend_with_the_bearer_header(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_FROM", "remetente@apras.test")
    calls = []

    async def _post(_self, url, *, json, headers):
        calls.append((url, json, headers))
        return _Response()

    monkeypatch.setattr(httpx.AsyncClient, "post", _post)

    sent = _run(mail.send_email("alguem@example.com", "Assunto", "<p>oi</p>"))

    assert sent is True
    assert len(calls) == 1
    url, payload, headers = calls[0]
    assert url == "https://api.resend.com/emails"
    assert headers["Authorization"] == "Bearer re_test_key"
    assert headers["Content-Type"] == "application/json"
    assert payload == {
        "from": "remetente@apras.test",
        "to": "alguem@example.com",
        "subject": "Assunto",
        "html": "<p>oi</p>",
    }


def test_a_raising_post_is_swallowed_and_falls_back_to_printing(monkeypatch, capsys):
    """A mail failure is a best-effort side effect and never fails a request."""
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    async def _post(_self, _url, **_kwargs):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(httpx.AsyncClient, "post", _post)

    sent = _run(mail.send_email("alguem@example.com", "Assunto", "<p>oi</p>"))

    assert sent is False
    assert "Failed to send email via Resend" in capsys.readouterr().out


def test_a_non_2xx_response_is_swallowed_too(monkeypatch, capsys):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    async def _post(_self, _url, **_kwargs):
        return _Response(raises=True)

    monkeypatch.setattr(httpx.AsyncClient, "post", _post)

    sent = _run(mail.send_email("alguem@example.com", "Assunto", "<p>oi</p>"))

    assert sent is False
    assert "Failed to send email via Resend" in capsys.readouterr().out


def test_the_two_templates_carry_their_url_and_no_raw_credential_elsewhere():
    """Both templates are ordinary HTML strings with the link in them."""
    reset = mail.password_reset_html("Fulana", "https://app.test/reset?token=abc")
    invitation = mail.invitation_html(
        "Condomínio Beta", "https://app.test/invite?token=xyz"
    )

    assert "https://app.test/reset?token=abc" in reset
    assert "Fulana" in reset
    assert "https://app.test/invite?token=xyz" in invitation
    assert "Condomínio Beta" in invitation
    # The invited person is the condominium's administrator in the system,
    # never one of the condominium's own elected offices; the pt-BR name of
    # that office must not appear in the copy.
    assert "índico" not in invitation
    assert "administrador" in invitation.lower()


def test_the_templates_escape_every_value_they_interpolate():
    """A forged mail body is costliest in exactly this message.

    Both values reaching `invitation_html` are attacker-influenced in the
    general case -- `accept_url` is built from the caller's `Origin` header
    -- and `password_reset_html` renders a `full_name` that is
    self-service-settable at signup into a mail sent by the
    *unauthenticated* `/auth/forgot-password`. The mail asks its reader to
    click a link and set a password, so an injected anchor is a credible
    phishing primitive.
    """
    invitation = mail.invitation_html(
        "<script>alert(1)</script>",
        'https://app.test/invite?token=x"><a href="https://evil.test">clique',
    )
    reset = mail.password_reset_html(
        'Fulana"><img src=x onerror=alert(1)>',
        'https://app.test/reset?token=y"><a href="https://evil.test">clique',
    )

    for rendered in (invitation, reset):
        assert "<script>" not in rendered
        # The payload survives as inert text; what it must not do is become
        # a second anchor or escape the `href` attribute it landed in.
        assert 'href="https://evil.test"' not in rendered
        assert "<img" not in rendered
        assert rendered.count("<a ") == 1
        assert rendered.count('href="') == 1
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in invitation
    assert "&quot;&gt;&lt;a href=" in invitation
    assert "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;" in reset


def test_escaping_leaves_ordinary_values_readable():
    """The escape is not allowed to disfigure the normal case."""
    rendered = mail.invitation_html(
        "Condomínio Beta & Cia", "https://app.test/invite?token=abc&x=1"
    )

    assert "Condomínio Beta &amp; Cia" in rendered
    assert 'href="https://app.test/invite?token=abc&amp;x=1"' in rendered
