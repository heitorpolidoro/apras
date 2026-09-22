"""The one mail sender (APRAS-71 D10).

Extracted from the inline Resend block that lived in
``auth.forgot_password``, so the password-reset mail and the invitation mail
have one implementation between them instead of two that drift.

Three properties are deliberate and are what the callers depend on:

* ``RESEND_API_KEY`` and ``EMAIL_FROM`` are read with ``os.getenv`` **at call
  time**, exactly as before, so a test needs no settings surgery and a
  deployment can add the key without a code change;
* :func:`send_email` **never raises**. With the key absent, or on any
  exception from Resend, it returns ``False`` and the caller prints the link
  instead. A mail failure is a best-effort side effect and must not fail the
  request that triggered it;
* the fallback *printing* belongs to the caller, not here, because the two
  flows print different lines -- ``[AUTH]`` for a reset and ``[INVITE]`` for
  an invitation -- and ``tests/test_password_recovery.py`` passes unedited
  because the ``[AUTH]`` pair is byte-for-byte what it always was.

Every interpolated value is ``html.escape``d. ``full_name`` is
self-service-settable at signup and ``accept_url`` is built from the
caller's ``Origin`` header, and the message these land in is one that asks
its reader to click a link and set a password -- the costliest place in the
product for a forged body.

The HTML is user-facing copy and is therefore pt-BR. The invited person is
the condominium's **administrator in the system**: a system role, not one of
the condominium's own elected offices, and the templates never call them
one.
"""

import html
import os

import httpx

#: Resend's transactional-email endpoint.
RESEND_ENDPOINT = "https://api.resend.com/emails"

#: The sender used when ``EMAIL_FROM`` is unset -- Resend's own sandbox
#: address, which is what this project has always sent from.
DEFAULT_FROM = "onboarding@resend.dev"


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send one HTML mail. Return whether Resend accepted it.

    ``False`` means "nothing was sent, print the link yourself": either no
    API key is configured, or the call failed. It never raises.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return False

    payload = {
        "from": os.getenv("EMAIL_FROM", DEFAULT_FROM),
        "to": to,
        "subject": subject,
        "html": html,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(RESEND_ENDPOINT, json=payload, headers=headers)
            response.raise_for_status()
    except Exception as e:  # noqa: BLE001  # best-effort side effect; a failure here must not fail the request
        print(f"Failed to send email via Resend: {e}")
        return False
    return True


def _shell(body: str) -> str:
    """The card both templates render inside."""
    return f"""
                    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
                      <h2 style="color: #059669; margin-top: 0;">APRAS</h2>
{body}
                    </div>
                    """


def _button(url: str, label: str) -> str:
    """The call to action. The URL is escaped: it is caller-influenced.

    `_accept_url` builds it from the request's `Origin` header, so an
    `Origin` carrying `"><a href=...` would otherwise break out of the
    attribute -- in the one message whose whole purpose is to be clicked.
    """
    return (
        '<div style="margin: 24px 0;">'
        f'<a href="{html.escape(url, quote=True)}" style="background-color: #059669; color: white; '
        "padding: 10px 20px; text-decoration: none; border-radius: 6px; "
        f'font-weight: bold; display: inline-block;">{label}</a>'
        "</div>"
    )


def password_reset_html(full_name: str | None, reset_url: str) -> str:
    """The password-reset mail, unchanged in substance from the inline block."""
    return _shell(
        f"<p>Olá, {html.escape(full_name or 'usuário')}!</p>"
        "<p>Recebemos uma solicitação para redefinir sua senha. "
        "Clique no botão abaixo para escolher uma nova:</p>"
        + _button(reset_url, "Redefinir Senha")
        + '<p style="color: #6b7280; font-size: 14px;">Se você não solicitou '
        "isso, pode ignorar este e-mail com segurança.</p>"
        '<hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 20px 0;" />'
        '<p style="color: #9ca3af; font-size: 12px;">Este link irá expirar em '
        "15 minutos.</p>"
    )


def invitation_html(tenant_name: str, accept_url: str, expires_in_days: int = 7) -> str:
    """The invitation mail: one condominium, one administrator, one link."""
    return _shell(
        "<p>Olá!</p>"
        f"<p>Você foi convidado para ser o <strong>administrador</strong> do "
        f"condomínio <strong>{html.escape(tenant_name)}</strong> no APRAS. "
        "Clique no botão abaixo para criar seu acesso:</p>"
        + _button(accept_url, "Aceitar convite")
        + '<p style="color: #6b7280; font-size: 14px;">Se você não esperava '
        "este convite, pode ignorar este e-mail com segurança.</p>"
        '<hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 20px 0;" />'
        '<p style="color: #9ca3af; font-size: 12px;">Este link pode ser usado '
        f"uma única vez e irá expirar em {expires_in_days} dias.</p>"
    )
