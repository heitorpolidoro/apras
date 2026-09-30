"""The bcrypt secret-length ceiling, owned where both sides of it can see it.

bcrypt hashes at most 72 bytes of the secret: that is the algorithm's key
schedule, not a choice. Two places have to know the number -- the hasher in
`app/core/security.py`, which refuses to truncate, and
`app/schemas/user.validate_password_strength`, which turns an over-long password
into a 422 before any hash is computed -- and it must be one number, because two
copies of a limit are two limits and the looser one is the one that decides.

It does not live in `app/core/security.py`, next to the hasher, for one reason:
that module imports `app.core.config`, and `config.py` instantiates `Settings()`
at import time. Importing the constant from `app/schemas/user.py` would make
every schema import require `SECRET_KEY` and `POSTGRES_URL` in the environment.
`app/core/permissions.py` is the precedent for a settings-free `app/core` module
that the schema layer may import.
"""

#: bcrypt's maximum secret length, in UTF-8 **bytes**, not characters: 72
#: accented Latin characters are 144 bytes, so no character count stands in for
#: this one.
BCRYPT_MAX_PASSWORD_BYTES = 72
