"""Administrator invitations (APRAS-71 D5, D6).

Four routes, mounted **GLOBAL_SCOPED**: `tenant_invitation` is an unscoped
table, the two superuser routes name their tenant in the body or the query
string, and the two public ones have no caller at all to resolve a tenant
from.

None of the four maps to a catalogue permission, by the convention
`PATCH /api/v1/users/{user_id}/superuser` and `/api/v1/plans/*` established:
`is_superuser` is a column and not a bundle, so minting a string whose only
job is to be refused by `assert_can_grant` would cost six parity cells for
nothing. The other two are unauthenticated, like `/auth/forgot-password`.
All four are therefore on `UNGUARDED_ROUTES`, and `invitations` is a fully
unguarded tag.

**Both public routes are `POST`, the preview included, despite being a read
(D5):** a token in a path or a query string lands in access logs, in
`Referer` headers and in browser history.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api import deps as api_deps
from app.core import mail, security
from app.core.config import settings
from app.core.limiter import limiter
from app.db import get_session
from app.models.tenant import Tenant
from app.models.tenant_invitation import TenantInvitation
from app.models.user import User
from app.schemas.invitation import (
    InvitationAcceptRequest,
    InvitationCreate,
    InvitationPreview,
    InvitationPreviewRequest,
    InvitationRead,
)
from app.schemas.token import Token
from app.services.invitation_service import InvitationService

router = APIRouter()

#: The page APRAS-72 builds. The origin is the caller's, with the existing
#: `forgot-password` fallback for a request that sends none.
_ACCEPT_PATH = "/invite"
_DEFAULT_ORIGIN = "http://localhost:5173"


def _accept_url(request: Request, raw_token: str) -> str:
    origin = request.headers.get("origin") or _DEFAULT_ORIGIN
    return f"{origin}{_ACCEPT_PATH}?token={raw_token}"


def _preview(
    invitation: TenantInvitation,
    tenant: Tenant,
    inviter: User,
    account_exists: bool,
) -> InvitationPreview:
    return InvitationPreview(
        email=invitation.email,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        invited_by_name=inviter.full_name,
        expires_at=invitation.expires_at,
        account_exists=account_exists,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    request: Request,
    body: InvitationCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> InvitationRead:
    """Invite one address to administer one condominium. Superuser only.

    The raw token leaves `InvitationService` exactly once, to the mail
    sender: it is in no response body, in no column and in no log line other
    than the printed fallback below, which exists only where no
    `RESEND_API_KEY` is configured.
    """
    invitation, raw_token, tenant = InvitationService.issue(
        session,
        tenant_id=body.tenant_id,
        email=body.email,
        invited_by=current_user,
    )

    accept_url = _accept_url(request, raw_token)
    sent = await mail.send_email(
        invitation.email,
        f"Convite para administrar {tenant.name} - APRAS",
        mail.invitation_html(
            tenant.name,
            accept_url,
            expires_in_days=settings.INVITATION_EXPIRE_HOURS // 24,
        ),
    )
    if not sent:
        print(f"[INVITE] Invitation for {invitation.email} to {tenant.name}")
        print(f"[INVITE] Accept URL: {accept_url}")

    return InvitationRead.model_validate(invitation)


@router.get("")
def list_invitations(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> list[InvitationRead]:
    """Every invitation, newest first, optionally one condominium's. Superuser only."""
    return [
        InvitationRead.model_validate(invitation)
        for invitation in InvitationService.list_invitations(
            session, tenant_id=tenant_id
        )
    ]


@router.post("/preview")
@limiter.limit("5/minute")
def preview_invitation(
    request: Request,  # noqa: ARG001  # slowapi's @limiter.limit requires this parameter by name
    body: InvitationPreviewRequest,
    session: Annotated[Session, Depends(get_session)],
) -> InvitationPreview:
    """What the invitee is shown before accepting. Unauthenticated.

    The three failure cases are D7's 404 / 410 / 409, and no failing body
    carries the invited email, the condominium's name or the inviter's.
    """
    invitation = InvitationService.resolve(session, body.token)
    tenant, inviter, account_exists = InvitationService.describe(session, invitation)
    return _preview(invitation, tenant, inviter, account_exists)


@router.post(
    "/accept",
    status_code=status.HTTP_201_CREATED,
    # Both branches declared, so the "no credential in the 200 branch" rule
    # is visible in the schema and not only in a test.
    responses={
        status.HTTP_200_OK: {"model": InvitationPreview},
        status.HTTP_201_CREATED: {"model": Token},
    },
)
@limiter.limit("5/minute")
def accept_invitation(
    request: Request,  # noqa: ARG001  # slowapi's @limiter.limit requires this parameter by name
    body: InvitationAcceptRequest,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Consume the invitation. Unauthenticated.

    Two branches, distinguishable by status alone (D8):

    * **201** with a `Token` when the account was created here -- the caller
      may use it immediately;
    * **200** with the `InvitationPreview` shape and **no credential of any
      kind** when the address already had an account. Returning a session
      there would be a strictly stronger takeover than the password reset
      the same decision refuses, and mailbox possession is a weaker factor
      than the password that account already holds. The invitee signs in
      normally instead.
    """
    invitation, user, created = InvitationService.accept(
        session,
        raw_token=body.token,
        full_name=body.full_name,
        cpf=body.cpf,
        password=body.password,
    )

    if not created:
        tenant, inviter, _ = InvitationService.describe(session, invitation)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(_preview(invitation, tenant, inviter, True)),
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "access_token": security.create_access_token(user.id),
            "token_type": "bearer",
        },
    )
