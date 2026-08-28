# APRAS-30 — Fix UserRead 500 on Non-Canonical CPF

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

`UserRead(UserBase)` inherits `UserBase`'s `validate_cpf` field validator. Because `UserRead.model_config = ConfigDict(from_attributes=True)`, every `UserRead.model_validate(db_user)` call (i.e., every response FastAPI builds from a `User` ORM row) re-runs the check-digit validator against whatever CPF is actually stored. A historically-seeded or imported row with a non-canonical CPF (fails the check-digit algorithm) causes a `ResponseValidationError` (500) on `GET /users/`, `PATCH /users/{id}`, and `PATCH /users/{id}/contact-info` — anything returning `UserRead`.

## Fix

Stop `UserRead` from inheriting the write-side CPF validator. `backend/app/schemas/user.py`:

1. Remove `cpf: str` and its `validate_cpf` field validator from `UserBase`. `UserBase` keeps only `email`, `full_name`, `role`, `phone`, `address` (and `block_lot` if APRAS-29 hasn't landed yet — coordinate ordering, or just include whichever fields `UserBase` actually has at implementation time).
2. Add `cpf: str` (plain, no validator) directly to `UserRead` — it's a display-only field on the read path; the value is already stored and doesn't need re-validating on the way out.
3. Add `cpf: str` **with** the `validate_cpf` field validator directly to `UserCreate` — duplicating the validator function is intentional and matches this file's existing convention (`UserUpdate` already independently duplicates the identical validator rather than inheriting it, since `UserUpdate` doesn't subclass `UserBase` at all). Do not introduce a new shared-validator abstraction (e.g. an `Annotated[str, AfterValidator(...)]` type) purely for this fix — matching the existing duplication style is the smaller, more consistent change.
4. `UserUpdate`'s existing independent `cpf`/`validate_cpf` pair is already correct (write-path, should keep validating) — no change needed there.

## Non-Goals

- Not fixing or normalizing any already-stored non-canonical CPF values in the database — this is a serialization bug fix, not a data migration. Existing rows keep whatever CPF they have; they simply stop crashing reads.
- Not relaxing CPF validation on any write path (signup, `PATCH /users/{id}`, `PATCH /users/{id}/contact-info`'s underlying `UserUpdate`-adjacent write) — validation on write is unchanged and correct as-is.

## Testing

- **Backend**: construct a `User` row directly (bypassing schema validation, e.g. via the ORM/session directly in a test, matching however this test suite already creates fixture users with arbitrary field values) with a CPF that fails the check-digit algorithm (e.g. all-same-digit or a wrong check digit). Confirm `GET /users/`, `GET /users/{id}` (if it exists), and `PATCH /users/{id}/contact-info` on that user all return normally (200), not 500. Confirm `UserCreate`/signup and `PATCH /users/{id}` with an invalid CPF in the *request body* still correctly reject with a 422, unchanged.

## Expected Results

1. Endpoints returning `UserRead` no longer 500 for a user with a non-canonical (but previously-stored) CPF value.
2. Existing CPF validation on write (signup, `PATCH /users/{id}`) is unaffected.
