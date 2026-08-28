# APRAS-33 — Scope online assembly/voting feature (COM21 parity gap)

**Status:** Scoping / brainstorm document — NOT approved for implementation. See "Next Steps" at the end.

## 1. Problem

`docs/tasks/APRAS-26-analysis.md` (the COM21 comparative analysis) identified "Online assembly / voting" as a real capability gap: COM21 advertises attendance lists, minutes ("atas"), and single/multiple-choice/free-text votes for condo assemblies; APRAS has nothing in this space today. That task explicitly declined to scope it ("not in this task's named scope... flagging it as a candidate for a future backlog item") — APRAS-33 is that follow-up.

Why it matters beyond "competitor has it": Brazilian condominium governance (regulated by the Código Civil, Arts. 1,347–1,362, and each condo's own "convenção"/internal bylaws) requires certain board and owner decisions — budget approval, bylaw changes, síndico election, extraordinary expenses above a threshold — to go through a formal assembly of unit owners ("assembleia de condôminos"), with:

- A **quorum** requirement that varies by decision type and is set by each condo's convenção (some decisions need a simple majority of those present, others need a supermajority of *all* fractions ideais, not just attendees).
- An **attendance record** (who was present, in person or by proxy/procuração), because quorum is checked against it.
- A **minutes document** ("ata de assembleia") that is often the only artifact with legal standing afterward — it's what gets registered, cited in disputes, or shown to a notary/bank.
- Sometimes a **secret ballot** requirement for sensitive votes (e.g., electing or removing a síndico) under some bylaws or by request of a quorum of owners present, per Art. 1,352 discussions in practice — this varies condo to condo and is not something this document should assume either way (see Open Questions, #1).

APRAS already has adjacent building blocks — `Lot`/`Resident`/`UserLotLink` (who owns/lives where, and by what `fraction_ideal` — relevant to quorum math), the Gatekeeper/visitor check-in infrastructure (`AccessLog`, `VisitorAuthorization`), the Document Center (APRAS-23/T009, for storing an ata afterward), and Feedback's anonymous-submission pattern (`is_anonymous` + server-side masking) — but nothing that ties these together into "hold a vote and record who voted for what." Today, if a síndico wants to run an assembly vote, they do it entirely off-platform (paper ballots, a WhatsApp poll, a spreadsheet) with no audit trail APRAS can offer.

There is also a second, related gap noted in the same parity matrix row: **"Dashboards, event calendar" — Partial: Task Dashboard exists; no shared event calendar.** This document treats that as a real dependency question (see Approaches below) rather than silently assuming assemblies need full calendaring, since APRAS has zero scheduling/calendar infrastructure today (no `Event` model, no calendar UI component anywhere in `frontend/src/`) — building it as a side effect of this task would significantly expand scope beyond "voting."

## 2. Candidate approaches

### (a) Minimal single-vote model — no scheduling, no attendance, no minutes

An admin/director creates a `Vote` directly (title, description, N choices, single-choice/multiple-choice/free-text type, opens immediately, closes at a set time or manually). Residents (one per `Lot`, or one per `User` — needs deciding, see Open Questions) cast a ballot once; a tally view shows live/final results. No concept of an "assembly" as a container — just standalone votes, like a poll.

**Trade-offs:**
- Cheapest to build by far — reuses `Feedback`'s create/list/RBAC shape almost directly, no new scheduling or attendance concepts, no calendar dependency.
- Delivers the core "residents vote on something, we get an auditable tally" value with minimal surface area.
- Does **not** produce anything resembling a legally usable ata or attendance record — for a condo that needs actual assembly documentation for real governance decisions, this is closer to "a poll" than "an assembly," which may undersell what the feature needs to be taken seriously for its stated purpose (deciding board matters).
- No link between "vote" and "assembly" as the legal/procedural unit Brazilian condo bylaws actually reference — could be confusing terminology-wise if positioned as assembly support.

### (b) Full assembly model — scheduled assemblies, attendance check-in, multiple votes per assembly, minutes attached afterward

An `Assembly` is a first-class scheduled entity (date/time, type — ordinary/AGO or extraordinary/AGE, agenda items) with an attendance/check-in step (residents or their proxies check in, tied conceptually to the existing visitor/access-log check-in pattern, though assembly attendance is owner check-in, not visitor check-in, so it would need its own `AssemblyAttendance` table rather than literally reusing `AccessLog`). One assembly can contain multiple `Vote` items (one per agenda point). After the assembly, a minutes/notes field (or an uploaded document via the existing Document Center) is attached, and the assembly is marked closed.

**Trade-offs:**
- Much closer to what COM21 (and real condo governance) actually needs — attendance ties directly to quorum, votes are scoped to a real governance event, minutes have somewhere to live.
- Genuinely requires scheduling as a prerequisite: an `Assembly` needs a date/time, needs to show up somewhere residents can see it's coming ("Dashboards, event calendar" gap this analysis flagged), and needs a rsvp/reminder path to be useful — which means this approach quietly pulls in the calendar gap as a co-dependency, unless assemblies get their own narrow, non-reusable "when is this happening" field with no shared calendar UI (defeating some of the point).
- Substantially larger PR/task — likely 2-3x the model/endpoint/frontend surface of (a), and pulls in attendance/quorum logic that has real legal-correctness stakes (see Open Questions) that this app has not had to reason about before.
- Risks scope creep into "build a full governance platform" territory, which is explicitly not this app's ambition per its own AGENTS.md framing (an ops/task-management tool for síndicos, not an enterprise governance suite).

### (c) Async voting only, no in-person attendance concept at all

Treat "assembly" purely as a time-boxed voting period, explicitly *not* modeling in-person attendance, quorum enforcement, or a physical/virtual meeting at all — just "the board opens a formal vote on Motion X, tied to a `Lot`-weighted or one-vote-per-unit rule, for N days, residents vote asynchronously, results are tallied and archived." Minutes, if wanted, are just a free-text/attached-document field summarizing the outcome after the fact, not a record of a meeting that happened.

**Trade-offs:**
- Sidesteps the hardest and most legally fraught part (attendance/quorum-as-of-a-specific-meeting, secret ballot mechanics, proxy voting) entirely, by not claiming to support in-person/synchronous assemblies at all.
- Still delivers the single most valuable piece: a real, auditable "residents voted N-Y on Q" record that can back board decisions, without the app claiming a level of legal formality (a substitute for an ata / real assembleia) it can't actually guarantee.
- Weakest fit to COM21's actual described feature ("attendance lists, minutes... per COM21's marketing") — this explicitly does not chase that parity claim, trading marketing-completeness for scope discipline and reduced legal exposure.
- May not satisfy a síndico who specifically needs an assembly that "counts" procedurally (i.e., needs a quorum-of-attendees check) — for those cases this approach offers no path other than "still do the real assembly in person/via another tool, use this only for the tally."

### Recommendation

**Approach (a), with the vote model shaped so it can grow into something like (b) later without a rewrite** — i.e., build a `Vote` model that already carries an optional `assembly_context` label (free text, not a foreign key to a real `Assembly` entity yet) so a future task can introduce `Assembly` as a real container without renaming/migrating the vote table's core shape.

Reasoning, calibrated to this app's actual maturity: APRAS is a mid-size condo ops tool, not an enterprise governance platform — its own AGENTS.md describes it as centralizing "operational tasks" for síndicos, and every other feature shipped so far (Feedback, Occurrence, Announcements) follows the same "small, mirrored, single-PR-sized" shape. Approach (b) is the "right" long-term shape if this app ever wants to be COM21's actual peer on this specific feature, but it requires solving calendar/scheduling (a separate, currently-unscoped gap this same analysis flagged) and quorum/attendance correctness (a genuine legal-correctness problem this app has never had to solve) in the same task — that is exactly the kind of scope-creep this document's job is to head off. Approach (c) is defensible but throws away too much of the actual ask ("attendance lists, minutes... per COM21's marketing" is explicitly what was asked to be scoped) for marginal safety gain over (a) — (a) already sidesteps the hard attendance/quorum problem by simply not attempting synchronous/in-person semantics at all, same as (c), while keeping the door open to an "assembly" framing later. A future task can introduce scheduling/calendar as its own scoped feature (which the Space Reservations Architectural Spec in APRAS-26 already flagged as needing "genuine new frontend work" — a calendar UI is not free) and a later task can introduce `Assembly` as a real entity with attendance once that exists, without this task blocking on either.

## 3. Recommended v1 data model sketch (rough — not migration-ready)

Mirrors `Feedback`'s shape (single table + simple status enum) more than `Occurrence`'s (no multi-actor timeline needed for v1 — a vote doesn't need a status-change audit trail the way an occurrence ticket does).

```python
# backend/app/models/enums.py additions

class VoteType(StrEnum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    FREE_TEXT = "FREE_TEXT"

class VoteStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


# backend/app/models/vote.py

class Vote(SQLModel, table=True):
    __tablename__ = "vote"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(nullable=False)
    description: str | None = Field(default=None)
    assembly_context: str | None = Field(default=None)  # free-text label, e.g.
        # "AGO 2026 - Item 3"; NOT a foreign key to a real Assembly entity in v1
        # (see Approach (a) recommendation) — exists so a future Assembly model
        # can adopt these rows without a shape change.
    vote_type: VoteType = Field(nullable=False)
    is_anonymous: bool = Field(default=False, nullable=False)  # mirrors
        # Feedback.is_anonymous — masking behavior is an OPEN QUESTION, see
        # section 4/5, do not assume Feedback's exact masking rule applies here
    created_by_id: UUID = Field(foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True)
    status: VoteStatus = Field(default=VoteStatus.OPEN, nullable=False, index=True)
    opens_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    closes_at: datetime = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    options: list["VoteOption"] = Relationship(
        back_populates="vote", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    ballots: list["Ballot"] = Relationship(
        back_populates="vote", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class VoteOption(SQLModel, table=True):
    __tablename__ = "vote_option"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    vote_id: UUID = Field(foreign_key="vote.id", ondelete="CASCADE", nullable=False, index=True)
    label: str = Field(nullable=False)
    order_index: int = Field(default=0, nullable=False)

    vote: Vote = Relationship(back_populates="options")


class Ballot(SQLModel, table=True):
    __tablename__ = "ballot"
    __table_args__ = (
        UniqueConstraint("vote_id", "voter_key", name="uq_ballot_vote_voter"),
        # "voter_key" abstracts over the open "one vote per User or per Lot?"
        # question (section 4) — resolve before finalizing this table.
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    vote_id: UUID = Field(foreign_key="vote.id", ondelete="CASCADE", nullable=False, index=True)
    voter_user_id: UUID = Field(foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True)
    voter_key: str = Field(nullable=False)  # e.g. user_id or lot_id as text,
        # whichever the "one vote per X" resolution below picks
    selected_option_ids_json: str | None = Field(default=None)  # for
        # SINGLE_CHOICE/MULTIPLE_CHOICE
    free_text_response: str | None = Field(default=None)  # for FREE_TEXT
    cast_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    vote: Vote = Relationship(back_populates="ballots")
```

Notes on the sketch:
- `Ballot` always stores `voter_user_id`, even for anonymous votes — mirroring `Feedback.reporter_user_id`'s "always stored, masked at the read/serialization layer" pattern, so double-voting can still be prevented server-side regardless of the anonymity setting. Whether the *tally breakdown* is ever allowed to be de-anonymized (e.g., for legal challenge/audit) is an open question (section 4/5), not a decision this sketch makes.
- No `AssemblyAttendance`, no quorum calculation, no scheduling/calendar integration — deliberately absent per the recommended approach (a).
- No `TaskHistory`-style audit timeline on `Vote`/`Ballot` — v1 assumes a vote's own row history plus `Ballot.cast_at` is enough; revisit if legal requirements demand more (Open Questions).

## 4. RBAC sketch

Following the app's existing pattern of role-based rules with a service-layer `_assert_*` guard (see `access_logs.py`'s `_assert_gatekeeper_access`):

- **Create a `Vote`**: `ADMINISTRATOR`/`DIRECTOR` only (mirrors `ReservableSpace` CRUD from APRAS-26 Spec A, and `Category`'s admin-managed-label pattern) — a vote is a governance action initiated by the board, not something any resident can spin up, unlike `Feedback`'s any-authenticated-user create rule.
- **Close a `Vote` early / edit before any ballots are cast**: `ADMINISTRATOR`/`DIRECTOR` only, same guard.
- **Cast a `Ballot`**: any authenticated user with `RESIDENT`-equivalent standing (needs a real definition — see Open Question below on what "eligible voter" means, since `UserRole.RESIDENT` exists but this app doesn't yet have a clean "is this user currently an owner/resident of a lot in good standing" check reusable from `UserLotLink`). `GUEST`/`PORTEIRO` should not vote (mirrors `GatekeeperAccess`'s existing role carve-outs, which explicitly exclude non-governance roles from governance-adjacent actions).
- **View live/final tally**: readable by anyone who could vote, plus `ADMINISTRATOR`/`DIRECTOR` unconditionally (mirrors `Occurrence`'s is_public-independent staff visibility) — whether *non-final* (in-progress) tallies should be visible to voters before the vote closes is itself worth flagging as a design choice with real behavioral consequences (bandwagon effects) but is not treated here as a legal/compliance open question, just a product one; default recommendation is to show live tallies unless the user says otherwise, since nothing here suggests condo bylaws require secrecy of interim results.

**Anonymity — flagged as a real open question, not decided here:**

`Feedback.is_anonymous` exists and has a well-defined masking rule (identity hidden from everyone except Administrator/Director, even from the reporter's own view of their own item). It would be tempting to copy that pattern onto `Vote`/`Ballot` unmodified, but **this document deliberately does not**, because condo assembly voting in Brazil is a different legal context than a suggestion box:

- Some bylaws or Código Civil interpretations treat assembly votes as needing to be **recorded/attributed** (so the ata can state "owner of unit X voted Y"), particularly for votes that affect individual owners' obligations (e.g., approving a special assessment) — attribution may be a legal requirement, not a UX preference, in at least some condos' governance documents.
- Other situations (e.g., electing/removing a síndico) may specifically call for a **secret ballot** by request or bylaw.
- APRAS has no way today to know which regime a given condo operates under, and getting this wrong in either direction has real consequences: an app that always attributes votes could produce a legally deficient anonymous-vote scenario a condo's bylaws require secrecy for; an app that always anonymizes could produce an ata that's legally insufficient because votes weren't attributable when they needed to be.

**This is the single most important open question for the user to answer before implementation is spec'd** (see section 5, #1).

## 5. Explicit open questions for the user

These are things this document deliberately does not decide:

1. **Anonymity/secrecy model** (legal/governance weight — see section 4): Should votes be attributed (visible to Administrator/Director who cast which ballot, the way Feedback's masking already reveals identity to staff) by default, with an optional secret-ballot mode per vote? Or should the reverse be true? Does this need to be configurable per-vote (some votes secret, some not) from day one, or can v1 hard-code one behavior?
2. **Who is an eligible voter, precisely?** One vote per `User`, or one vote per `Lot` (relevant because a lot can have multiple linked `User`s via `UserLotLink` — e.g., owner + spouse + tenant)? If per-`Lot`, who among multiple linked users is authorized to cast it, and does `fraction_ideal`-weighted voting (common in Brazilian condo bylaws for some decision types) need to exist even in v1, or can v1 assume "one lot, one vote" and defer weighted voting?
3. **Does v1 need to produce anything with legal standing** — i.e., a document that could function as (part of) a real "ata de assembleia" — or is it explicitly *not* trying to be legally sufficient on its own, with the understanding that a síndico would still produce/sign a separate legal ata using this tool's tally as supporting evidence only? This materially changes how much rigor (attribution, immutability/tamper-evidence of `Ballot` rows, timestamped export) v1 needs.
4. **Quorum**: does v1 need to track or enforce quorum at all, or is quorum entirely out of scope until (if ever) a real `Assembly`/attendance model exists (per Approach (a)'s recommendation, it would be)? Confirming this is out of scope for v1 is itself worth an explicit yes from the user, given how central quorum is to assembly legitimacy.
5. **Vote editing/retraction**: can a resident change their vote before `closes_at`, or is a cast `Ballot` final the instant it's submitted? (Affects the `UniqueConstraint` design in section 3.)
6. **Multi-tenancy assumption**: does this app manage a single condo (one HOA) per deployment, or multiple (in which case `Vote` needs a condo/organization scope this sketch doesn't currently have)? Existing models (`Lot`, `Task`, etc.) don't show any multi-condo scoping today, so this document assumes single-tenant, but that assumption should be confirmed since a voting/governance feature is exactly the kind of thing that would be broken by a wrong assumption here.

## 6. Non-goals for v1

Aggressively cut, per the recommended Approach (a):

- No `Assembly` entity, no scheduling, no shared event calendar (a separate, currently-unscoped gap from the same APRAS-26 analysis — not built here, not a prerequisite for this task).
- No attendance/check-in tracking, no quorum calculation or enforcement.
- No proxy voting ("procuração").
- No weighted voting by `fraction_ideal` (assume one-vote-per-eligible-voter in v1, pending Open Question #2).
- No generation of a legally formatted "ata de assembleia" document (pending Open Question #3) — at most, a plain export of tally results.
- No integration with the Document Center (APRAS-23/T009) for attaching minutes — could be a trivial follow-up once this exists, but not built in this pass.
- No push/email/WhatsApp notifications about vote open/closing (same missing infrastructure noted elsewhere in APRAS-26 — Web Push and WhatsApp integration are both separately gapped, not solved here).
- No recurring/templated votes, no vote editing after any ballot has been cast (pending Open Question #5's answer — default assumption is votes are structurally frozen once live).
- No secret-ballot cryptographic guarantees (e.g., unlinkability proofs) even if the anonymity question resolves toward "secret" — v1 anonymity, if built, would follow Feedback's existing "stored but masked at read time" pattern, not a cryptographically-verified secret-ballot scheme.

## Next steps

This is a scoping/brainstorm document, not an approved spec. Before a proper implementation spec can be written and this moves toward `readytodo`, it needs:

1. The user's explicit review and approval of the recommended approach (or a different one, if they push back).
2. Answers to all six open questions in section 5 — in particular #1 (anonymity/secrecy) and #3 (legal standing of the output), since both have governance/legal implications specific to how Brazilian condominium assemblies actually work that this document is not positioned to decide unilaterally.

Once those are resolved, a follow-up task should go through this repo's normal spec-review cycle before implementation begins.
