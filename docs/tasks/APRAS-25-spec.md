# APRAS-25 — Canal de Críticas, Sugestões e Fale Conosco

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

Residents have no dedicated channel to send feedback, suggestions, or complaints directly to the board — only the Occurrence Book (APRAS-24/T010), which is scoped to operational incidents (maintenance, noise, security), not general feedback/suggestions/praise.

## Approach

Mirror the already-shipped Occurrence Book (`backend/app/models/occurrence.py`, `occurrence_service.py`, `endpoints/occurrences.py`, and the frontend `OccurrenceBookPage`) closely — same architectural shape (model + service-layer RBAC + endpoint + timeline-less but response-bearing record), simplified where the task's own expected results don't call for Occurrence's full complexity (no priority levels, no assignment, no multi-step status workflow, no public/private visibility toggle — feedback is always private between the sender and the board).

## Data Model

### `backend/app/models/enums.py`

```python
class FeedbackCategory(StrEnum):
    CRITICISM = "CRITICISM"
    SUGGESTION = "SUGGESTION"
    COMPLIMENT = "COMPLIMENT"
    OTHER = "OTHER"

class FeedbackStatus(StrEnum):
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"
```

### `backend/app/models/feedback.py`

```python
class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    reporter_user_id: UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True)
    is_anonymous: bool = Field(default=False, nullable=False)
    category: FeedbackCategory = Field(nullable=False, index=True)
    message: str = Field(nullable=False)
    status: FeedbackStatus = Field(default=FeedbackStatus.PENDING, nullable=False, index=True)
    board_response: str | None = Field(default=None, nullable=True)
    responded_by_id: UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True)
    responded_at: datetime | None = Field(default=None, nullable=True)
    response_seen_by_reporter: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    reporter: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Feedback.reporter_user_id]"})
    responded_by: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Feedback.responded_by_id]"})
```

`is_anonymous=True` means `reporter_user_id` is still stored (so a resident can see their own submission history) but is never exposed to the board via the API response (`FeedbackRead` omits `reporter`/`reporter_user_id` when `is_anonymous` is true) — mirroring `Occurrence`'s anonymous-masking precedent (check `occurrence_service.py`'s handling of `is_anonymous` for the exact masking approach and replicate it).

`response_seen_by_reporter` is the "notification" mechanism per the task's expected results: **in-app only** — no email/push/SMS infrastructure exists in this app today (WhatsApp integration, APRAS-13, is blocked on missing provider setup), so "notification" means an unread-response indicator (e.g. a badge count) the reporter sees when they view their own feedback list, flipped to `true` once they open/view the answered item. This is a deliberate scope decision, not a placeholder — do not build any external notification channel.

### Migration

New Alembic revision (check `alembic heads` for the actual current head at implementation time): creates the `feedback` table and the two new enum types, following the exact idiom of the `occurrence`-table migration (`0009_add_occurrence_tables.py`) for enum-type creation on Postgres.

## Backend Changes

### `backend/app/services/feedback_service.py`

Mirror `occurrence_service.py`'s structure:
- `create_feedback(session, current_user, feedback_in)`: any authenticated user except `GUEST` can submit (mirror whatever role check `occurrence_service.py`'s create function uses for the reporter side — likely "any non-Guest role").
- `list_feedback(session, current_user, ...)`: `ADMINISTRATOR`/`DIRECTOR` see everything (the "categorized inbox"); anyone else sees only their own submissions (matched by `reporter_user_id`, regardless of `is_anonymous` — a user can always see their own history).
- `get_feedback(session, current_user, feedback_id)`: same visibility rule as list; also marks `response_seen_by_reporter = True` when the reporter (not staff) views an already-`ANSWERED` item.
- `respond_to_feedback(session, current_user, feedback_id, response_in)`: `ADMINISTRATOR`/`DIRECTOR` only, sets `board_response`, `responded_by_id`, `responded_at`, `status = ANSWERED`, and resets `response_seen_by_reporter = False` (so the reporter's next view triggers the "seen" flip and, in the meantime, they see an unread indicator).

### `backend/app/schemas/feedback.py`

`FeedbackCreate` (category, message, is_anonymous), `FeedbackRead` (all fields except reporter identity when anonymous), `FeedbackRespond` (board_response only).

### `backend/app/api/v1/endpoints/feedback.py`

`POST /feedback`, `GET /feedback` (paginated, category/status filters — mirror `occurrences.py`'s query-param pattern), `GET /feedback/{id}`, `PUT /feedback/{id}/respond`. Same `Depends(get_current_user)`-only pattern as `occurrences.py`, with role logic in the service layer.

## Frontend Changes

### New feature directory `frontend/src/features/feedback-management/`

Mirror `occurrence-management/`'s structure:
- `FeedbackChannelPage.tsx`: for `ADMINISTRATOR`/`DIRECTOR`, a categorized inbox (filter by category/status) listing all feedback with a response modal; for everyone else, a simple submission form + their own feedback history with an unread-response badge.
- `useFeedback.ts` hooks mirroring `useOccurrences.ts`'s query/mutation patterns.

### `App.tsx` / `Navbar.tsx`

New route `/feedback`, bare `<ProtectedRoute>` (any authenticated user, `GUEST` excluded at the service layer already) — nav link labeled "Fale Conosco".

### i18n

New `feedback.*` namespace in `en.json`/`pt.json`.

## Non-Goals

- No email/SMS/push notifications — in-app unread indicator only (see Data Model note above).
- No priority levels, assignment, or multi-step status workflow (`PENDING`/`ANSWERED` only) — this is intentionally simpler than the Occurrence Book.
- No public visibility toggle — feedback is always private between sender and board, unlike Occurrence's `is_public` option.
- No file/photo attachments (Occurrence's `photo_urls_json` has no analog here) — text-only messages.

## Testing

- **Backend**: `create_feedback` (non-Guest succeeds, Guest is rejected); `list_feedback` (staff sees all, resident sees only their own); anonymous masking (reporter identity hidden from staff-facing read when `is_anonymous=True`, but the same resident can still see their own anonymous submission in their own history); `respond_to_feedback` (Administrator/Director only, non-staff rejected); `response_seen_by_reporter` flips correctly on reporter view, resets on a new response.
- **Frontend**: `FeedbackChannelPage` renders the inbox view for staff and the submission/history view for others; unread badge reflects `response_seen_by_reporter`.

## Expected Results

1. Feedback message model supports an anonymous option (reporter identity hidden from staff view, preserved for the reporter's own history).
2. Board response workflow: Administrator/Director can respond; status moves `PENDING` → `ANSWERED`; reporter sees an in-app unread indicator until they view the response.
3. Categorized (by `FeedbackCategory`) inbox for Administrator/Director; a simple contact form + personal history view for everyone else.
