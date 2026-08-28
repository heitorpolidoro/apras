# APRAS-26 — COM21 Comparative Analysis & Advanced Features Roadmap

**Date:** 2026-08-27
**Status:** Research complete; architectural specs ready for implementation as separate tasks
**Type:** Analysis/roadmap document, not a code-implementation spec (see Expected Result #1 and #3)

## Research basis

COM21 (Condomínio21, now evolving into "Group COM") is a real, established Brazilian condo-management platform by Group Software, launched in 2001. Findings below are drawn from its own marketing/product pages and independent coverage — see Sources at the end. This is an external, third-party product; treat all COM21 claims as sourced marketing copy, not independently verified fact, and revisit before making business decisions based on this document if COM21's actual current feature set matters precisely (marketing pages can overstate or lag behind what's actually shipped).

## Parity Matrix

| Capability | COM21 | APRAS (current) |
|---|---|---|
| Resident/board communication, self-service | Yes ("autoatendimento", classificados/achados-e-perdidos) | Partial — Announcement Feed (APRAS-20), Feedback Channel (APRAS-25, in progress); no classifieds/lost-and-found |
| Financial management, boletos | Yes (2nd-copy boletos, automatic fine/interest recalculation) | Partial — Financial Dashboard (APRAS-22: transactions, budget-vs-actual, invoices); no boleto issuance/recalculation (APRAS is task/ops-focused, not a billing/boleto platform) |
| Space/amenity reservations | Yes (availability calendar, self-service booking) | **Gap** — not built. See Architectural Spec A below. |
| Document repository | Yes (atas, convenção, prestação de contas) | Yes — Document Center (APRAS-23/T009) |
| Package registry (encomendas) | Yes (receipt/pickup/status tracking) | **Gap** — not built. See Architectural Spec B below. |
| Gatekeeper / visitor check-in | Yes (portaria) | Yes — Gatekeeper Dashboard (T003/APRAS-17), QR-code check-in (APRAS-14, in progress), facial recognition (APRAS-19) |
| Online assembly / voting | Yes (attendance lists, minutes, single/multiple-choice/free-text votes) | **Gap** — not built, not currently scoped anywhere in the backlog |
| Dashboards, event calendar | Yes | Partial — Task Dashboard exists; no shared event calendar |
| Push/reminder notifications (boletos, reservations, visitor entry) | Yes | **Gap** — no push notification infrastructure exists; WhatsApp integration (APRAS-13) is blocked on provider setup and covers a different channel |
| Occurrence/complaint tracking | Not emphasized in COM21's marketing | Yes — Occurrence Book (APRAS-24/T010), stronger than what COM21 publicly advertises here |
| Facial recognition access | Yes (Group COM generation) | Yes — Access Control (APRAS-19) |
| RBAC granularity (UserType-based menu/task gating) | Not advertised | Yes — APRAS-8/9 (unusually granular for this product category) |

**Assessment**: APRAS already meets or exceeds COM21 in operational/audit-trail depth (occurrence tracking, granular RBAC, task management) — areas COM21's marketing doesn't emphasize at all. The clearest, most concrete gaps are: **space reservations**, **package tracking**, **online assembly/voting**, and **push notifications**. Per this task's own expected results, the first two get full architectural specs below; voting/assembly is a real gap this research surfaced but is **not** in this task's named scope — flagging it as a candidate for a future backlog item rather than silently expanding this task.

## Architectural Spec A — Space/Amenity Reservations

### Goal
Let residents book shared amenities (party room, gym, pool, BBQ area, etc.) against an availability calendar, self-service.

### Data Model
```python
class ReservableSpace(SQLModel, table=True):
    __tablename__ = "reservable_space"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    capacity: int | None = Field(default=None)
    requires_approval: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

class SpaceReservation(SQLModel, table=True):
    __tablename__ = "space_reservation"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    space_id: UUID = Field(foreign_key="reservable_space.id", ondelete="CASCADE", nullable=False, index=True)
    reserved_by_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    lot_id: UUID | None = Field(default=None, foreign_key="lot.id", ondelete="SET NULL", nullable=True)
    start_time: datetime = Field(nullable=False, index=True)
    end_time: datetime = Field(nullable=False)
    status: ReservationStatus = Field(default=ReservationStatus.PENDING, nullable=False)  # PENDING, CONFIRMED, CANCELLED, REJECTED
    notes: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
```

### RBAC
`ReservableSpace` CRUD: `ADMINISTRATOR`/`DIRECTOR` only (mirrors `Category`'s existing admin-managed-label pattern). Creating a `SpaceReservation`: any authenticated user except `GUEST` (mirror `Task`'s create-role convention, not Feedback's — a reservation is a resource commitment, unlike free-text feedback). Approving a `requires_approval` reservation: `ADMINISTRATOR`/`DIRECTOR`. A double-booking check (overlapping `start_time`/`end_time` for the same `space_id` with status `CONFIRMED` or `PENDING`) is required at creation time — this is the core value proposition ("sem conflitos" per COM21's own marketing) and must be enforced server-side, not just in the UI calendar widget.

### Frontend
New `space-reservation-management/` feature: an admin screen to manage `ReservableSpace` definitions (mirror `CategoriesPage.tsx`'s simple CRUD pattern), and a resident-facing calendar/booking view per space (a new UI pattern for this app — no existing calendar component to mirror; this is the one part of this spec needing genuine new frontend work, likely a date-range picker + a simple list/grid of existing reservations for the selected space, not a full calendar library unless the team wants one).

### Non-Goals (for this architectural spec)
- No recurring reservations (one-off bookings only, v1).
- No payment/fee collection for reservations (matches APRAS-22's finance module being separate from operational booking).

## Architectural Spec B — Package Tracking (Encomendas)

### Goal
Let the Gatekeeper log a package's arrival, and residents see (and the Gatekeeper mark) pickup status — mirrors COM21's "receipt/pickup/status" feature almost exactly, and fits naturally alongside the existing Gatekeeper Dashboard (T003/APRAS-17, and the new PORTEIRO role from APRAS-12).

### Data Model
```python
class Package(SQLModel, table=True):
    __tablename__ = "package"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lot_id: UUID = Field(foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True)
    received_by_id: UUID = Field(foreign_key="user.id", ondelete="SET NULL", nullable=True)  # gatekeeper who logged it
    description: str | None = Field(default=None)  # e.g. "Amazon box, medium"
    carrier: str | None = Field(default=None)
    received_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: PackageStatus = Field(default=PackageStatus.AWAITING_PICKUP, nullable=False, index=True)  # AWAITING_PICKUP, PICKED_UP
    picked_up_at: datetime | None = Field(default=None)
    picked_up_by_notes: str | None = Field(default=None)  # free text: who picked it up, since it may not be a system user
```

### RBAC
Create/mark-picked-up: mirrors `access_logs.py`'s `_assert_gatekeeper_access` (post-APRAS-12: `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`/`PORTEIRO`) — this is squarely a gatekeeper-desk function. Read (a resident checking if they have a package waiting): scoped to the resident's own `lot_id` (mirror how `Resident`/lot-scoped visibility already works elsewhere), `ADMINISTRATOR`/`DIRECTOR`/`MANAGER`/`PORTEIRO` see all.

### Frontend
Add a "Encomendas" tab/section to `GatekeeperDashboard.tsx` (log arrival: select lot + description/carrier; mark picked up: list of `AWAITING_PICKUP` packages with a pickup-confirmation action) — reuses the dashboard's existing lot-selection UI rather than building a new page. A resident-facing package-status view is a small addition wherever residents already see lot-scoped info (or a new minimal page if none exists — check at implementation time).

### Non-Goals (for this architectural spec)
- No photo-of-package capture (unlike the Media Management feature, APRAS-4/T004 — could be a future enhancement, not core to the parity gap).
- No SMS/push "your package arrived" notification (blocked on the same missing push/WhatsApp infrastructure noted below).

## Roadmap — Web Push Notifications

**Not specced in detail here** (per this task's own scope: a roadmap, not an implementation spec). Current state: **no push notification infrastructure exists anywhere in this app.** WhatsApp integration (APRAS-13) is blocked on missing provider credentials and is a different channel (business messaging API, not browser push). Web Push (via the Push API + a service worker) is a separate, independent capability that doesn't depend on APRAS-13's blocker — it could proceed independently. Recommended sequencing: **after** Space Reservations and Package Tracking ship (both name-checked as candidate "trigger events" for a first push notification use case — "your reservation is confirmed," "you have a package waiting"), since push notifications are most valuable once there's real event volume to notify about. Roadmap placeholder task: "Add Web Push notification infrastructure (service worker + subscription management + a notification-dispatch service triggered by domain events)" — do not begin without a follow-up brainstorming/spec pass, since this introduces a new cross-cutting subsystem (event triggers from multiple existing features) more architecturally involved than a single-feature task.

## Roadmap — Offline Gatekeeper Mode

**Not specced in detail here**, same reasoning. Current state: `GatekeeperDashboard.tsx` requires a live network connection for every check-in/check-out/search. An "offline mode" would need: local caching of active authorizations (a security-sensitive dataset to have sitting in browser storage), a sync/replay mechanism for check-ins logged while offline, and conflict resolution if the same visitor is somehow checked in from two offline sessions before sync. This is a substantial, security-sensitive undertaking (caching visitor authorization data client-side has real privacy/security implications this app has been careful about elsewhere — e.g., the deliberate non-caching design choices already made for RBAC). Recommended: treat as a lower-priority roadmap item relative to Push Notifications, and require its own dedicated brainstorming pass focused specifically on the security tradeoffs of offline visitor-data caching before any implementation spec is written.

## Expected Results (status)

1. ✅ COM21 parity matrix and gap analysis completed (above, sourced).
2. ✅ Architectural specifications for package tracking and area reservations created (Specs A and B above) — ready to become their own Meridian tasks (spec review → implementation) when prioritized.
3. ✅ Roadmap for web push notifications and offline gatekeeper mode finalized (deliberately high-level per their cross-cutting/security complexity — each needs its own future brainstorming pass before a concrete spec, not a premature architectural commitment here).

## Sources

- [Encontre todas as informações sobre Condomínio21 — B2B Stack](https://www.b2bstack.com.br/product/condominio21)
- [Aplicativo para condomínios e condôminos - COM21 — Group Software](https://www.groupsoftware.com.br/administracao-de-condominios/com21-online/?origemProduto=condominio21)
- [Recursos do COM21 que facilitam o dia a dia — Grupo Invest](https://www.grupoinvest.com/recursos-do-com21-que-facilitam-o-dia-a-dia/)
- [Funcionalidades do Condomínio21 para gestão — Group Software Blog](https://www.groupsoftware.com.br/blog/funcionalidades-do-condominio21/)
- [Gestão condominial além do Condomínio21 com a Group Software](https://www.groupsoftware.com.br/blog/condominio21/)
- [Soluções para condomínios e associações de moradores — Group Software](https://groupsoftware.com.br/solucoes/com21/?origemProduto=condominio21)
