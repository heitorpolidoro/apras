# Suggestions Log

## [T006] Blog/Feed de Comunicados e Notícias — 2026-08-27 (QA)

- QA finding (non-blocking, pre-existing, out of scope for T006): the frontend global
  Vitest coverage threshold for `functions` (75%, set in `vitest.config.ts`) was already
  failing on `master` before this task started (baseline ~70.99%). Root cause: every
  `frontend/src/api/*.ts` client module (`occurrences.ts`, `documents.ts`, `lots.ts`,
  `visitors.ts`, and now `announcements.ts`) shows 0% function coverage because component
  tests always `vi.mock()` the api layer rather than exercising it directly — a convention
  used consistently since at least T003/T009/T010. Recommend a dedicated follow-up task to
  either add direct unit tests for `api/*.ts` modules or adjust the threshold/exclude list
  to reflect the intended testing boundary (component/integration tests only).

## [T006] Blog/Feed de Comunicados e Notícias — 2026-08-27

- Spec review (round 1, APPROVED): Announcement media uses a dedicated, unmoderated upload
  path distinct from the T004 `MediaAsset` approval pipeline (publishers are already trusted
  Admin/Director roles). Consider a follow-up if a future requirement needs moderation of
  announcement attachments (e.g. multi-publisher orgs) — at that point reusing `MediaAsset`
  with `EntityType.ANNOUNCEMENT` (already reserved in the enum) would be worth revisiting.

## [T005] Controle de Acesso e Integração de Reconhecimento Facial — 2026-08-26

- Spec review (round 1, APPROVED): Consider a dedicated follow-up task for real biometric
  vector extraction / third-party facial-recognition SDK integration once a hardware vendor
  is chosen — T005 intentionally trusts the device's own `resident_id` claim for the
  verification webhook and does not perform actual face matching.
