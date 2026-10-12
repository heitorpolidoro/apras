# APRAS-124 mutation log

Nine mutations from the spec's "Required mutation proofs". Each section holds
the verbatim `git diff` of the mutation (taken against the index, which already
held the implementation and the tests, so the diff is the mutation alone), the
`pytest` command, and every `FAILED` line the run printed with its summary line.
Commands run from `backend/`. Each mutation was reverted by hand before the next.

Note on the diffs: the sandbox's command hook rewrites `git diff` into a compact
rendering (file header and `diff --git`/`index` lines are dropped, hunks and
`+`/`-` lines are kept). The text below is that output, pasted unedited.

## Mutation 1 - the derivation returns a fixed 64-hex constant, pre-read refusals kept

### git diff

```
backend/app/services/tenant_service.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

Changes:

backend/app/services/tenant_service.py
@@ -658,7 +658,7 @@ class TenantService:
         url = getattr(tenant, "logo_url", None)
         if cls._logo_content_type(url) is None:
             return None
-        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
+        digest = "ab" * 32
         return '"' + digest + '"'
 
     @classmethod
  +1 -1
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_replacing_the_logo_changes_the_etag_and_serves_the_new_bytes - assert 304 == 200
FAILED tests/test_public_logo_route.py::test_the_tag_is_the_literal_sha256_of_the_stored_url - assert '"abababababa...abababababab"' == '"e9a14ddc4b0...9f81bea7509a"'
FAILED tests/test_public_logo_route.py::test_the_tag_differs_when_only_the_object_uuid_differs - assert '"abababababababababababababababababababababababababababababababab"' != '"abababababababababababababababababababababababababababababababab"'
3 failed, 35 passed, 1 warning in 1.88s
```

Cited ids all present: replacing..., literal_sha256, uuid_differs.

## Mutation 2 - the handler ignores If-None-Match and always answers 200

### git diff

```
backend/app/api/v1/endpoints/public_branding.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

Changes:

backend/app/api/v1/endpoints/public_branding.py
@@ -173,7 +173,7 @@ def get_public_tenant_logo(
         )
 
     headers = {"ETag": etag, "Cache-Control": "no-cache"}
-    if _if_none_match_matches(request.headers.get("if-none-match"), etag):
+    if False:
         return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
 
     logo = TenantService.logo_bytes(tenant)
  +1 -1
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_a_matching_if_none_match_is_a_bodiless_304 - assert 200 == 304
FAILED tests/test_public_logo_route.py::test_a_star_a_list_and_a_weak_prefix_all_match[star] - assert 200 == 304
FAILED tests/test_public_logo_route.py::test_a_star_a_list_and_a_weak_prefix_all_match[list] - assert 200 == 304
FAILED tests/test_public_logo_route.py::test_a_star_a_list_and_a_weak_prefix_all_match[weak-prefix] - assert 200 == 304
FAILED tests/test_public_logo_route.py::test_the_304_performs_no_outbound_read_and_the_200_performs_one - assert 200 == 304
5 failed, 33 passed, 1 warning in 1.83s
```

Cited ids all present.

## Mutation 3 - the comparison answers 304 whenever If-None-Match is present

### git diff

```
backend/app/api/v1/endpoints/public_branding.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

Changes:

backend/app/api/v1/endpoints/public_branding.py
@@ -173,7 +173,7 @@ def get_public_tenant_logo(
         )
 
     headers = {"ETag": etag, "Cache-Control": "no-cache"}
-    if _if_none_match_matches(request.headers.get("if-none-match"), etag):
+    if request.headers.get("if-none-match"):
         return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
 
     logo = TenantService.logo_bytes(tenant)
  +1 -1
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_a_non_matching_if_none_match_is_a_200_with_the_full_bytes - assert 304 == 200
FAILED tests/test_public_logo_route.py::test_replacing_the_logo_changes_the_etag_and_serves_the_new_bytes - assert 304 == 200
2 failed, 36 passed, 1 warning in 1.96s
```

Cited ids all present.

## Mutation 4 - the derivation digests tenant.slug instead of tenant.logo_url, pre-read refusals kept

### git diff

```
backend/app/services/tenant_service.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

Changes:

backend/app/services/tenant_service.py
@@ -658,7 +658,7 @@ class TenantService:
         url = getattr(tenant, "logo_url", None)
         if cls._logo_content_type(url) is None:
             return None
-        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
+        digest = hashlib.sha256(tenant.slug.encode("utf-8")).hexdigest()
         return '"' + digest + '"'
 
     @classmethod
  +1 -1
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_replacing_the_logo_changes_the_etag_and_serves_the_new_bytes - assert 304 == 200
FAILED tests/test_public_logo_route.py::test_the_tag_is_the_literal_sha256_of_the_stored_url - assert '"5a2164fbf66...f2d668e98d33"' == '"e9a14ddc4b0...9f81bea7509a"'
FAILED tests/test_public_logo_route.py::test_the_tag_is_the_same_for_two_tenants_sharing_a_logo_url - assert '"7654b1fa561...7ebfeec8b7e6"' == '"f8202e0fc6d...174da9e90967"'
3 failed, 35 passed, 1 warning in 2.24s
```

Cited ids all present.

## Mutation 5 - the handler sets no Cache-Control

### git diff

```
backend/app/api/v1/endpoints/public_branding.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

Changes:

backend/app/api/v1/endpoints/public_branding.py
@@ -172,7 +172,7 @@ def get_public_tenant_logo(
             status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found"
         )
 
-    headers = {"ETag": etag, "Cache-Control": "no-cache"}
+    headers = {"ETag": etag}
     if _if_none_match_matches(request.headers.get("if-none-match"), etag):
         return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
 
  +1 -1
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_the_route_sets_no_cache_and_a_strong_etag - KeyError: 'cache-control'
FAILED tests/test_public_logo_route.py::test_a_matching_if_none_match_is_a_bodiless_304 - KeyError: 'cache-control'
2 failed, 36 passed, 1 warning in 1.77s
```

Cited id present (the 304 case also asserts the 304 carries `no-cache`).

## Mutation 6 - on a match the handler calls logo_bytes, discards it, and still answers 304

### git diff

```
backend/app/api/v1/endpoints/public_branding.py | 1 +
 1 file changed, 1 insertion(+)

Changes:

backend/app/api/v1/endpoints/public_branding.py
@@ -174,6 +174,7 @@ def get_public_tenant_logo(
 
     headers = {"ETag": etag, "Cache-Control": "no-cache"}
     if _if_none_match_matches(request.headers.get("if-none-match"), etag):
+        TenantService.logo_bytes(tenant)
         return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
 
     logo = TenantService.logo_bytes(tenant)
  +1 -0
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_the_304_performs_no_outbound_read_and_the_200_performs_one - AssertionError: assert ['/static/upl.../09/logo.png'] == []
1 failed, 37 passed, 1 warning in 1.58s
```

Exhaustive: only the cited id failed.

## Mutation 7 - the handler honours If-None-Match: * before checking the derivation for None

### git diff

```
backend/app/api/v1/endpoints/public_branding.py | 2 ++
 1 file changed, 2 insertions(+)

Changes:

backend/app/api/v1/endpoints/public_branding.py
@@ -167,6 +167,8 @@ def get_public_tenant_logo(
         )
 
     etag = TenantService.logo_etag(tenant)
+    if "*" in (request.headers.get("if-none-match") or ""):
+        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
     if etag is None:
         raise HTTPException(
             status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found"
  +2 -0
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[no-logo-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[no-logo-list-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[svg-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[svg-list-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[bin-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[bin-list-star] - assert 304 == 404
6 failed, 32 passed, 1 warning in 1.81s
```

Cited id present (all six parameter sets), nothing else failed.

## Mutation 8 - the derivation returns the URL's hex instead of the digest, pre-read refusals kept

### git diff

```
backend/app/services/tenant_service.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

Changes:

backend/app/services/tenant_service.py
@@ -658,7 +658,7 @@ class TenantService:
         url = getattr(tenant, "logo_url", None)
         if cls._logo_content_type(url) is None:
             return None
-        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
+        digest = url.encode("utf-8").hex()
         return '"' + digest + '"'
 
     @classmethod
  +1 -1
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_the_tag_is_the_literal_sha256_of_the_stored_url - assert '"2f737461746...676f2e706e67"' == '"e9a14ddc4b0...9f81bea7509a"'
FAILED tests/test_public_logo_route.py::test_the_tag_is_not_a_reversible_encoding_of_the_stored_url - AssertionError: assert '2f7374617469632f75706c6f6164732f323032362f30392f6c6f676f2e706e67' not in {'/static/uploads/2026/09/logo.png', '2f7374617469632f75706c6f6164732f323032362f30392f6c6f676f2e706e67', 'L3N0YXRpYy91cGxvYWRzLzIwMjYvMDkvbG9nby5wbmc'}
2 failed, 36 passed, 1 warning in 1.75s
```

Exhaustive: exactly the two cited ids failed; the shape check, the
shared-URL case and the UUID case stayed green. (The conditional cases read the
tag from the route rather than recomputing it, so they do not fail for a wrong
recipe; that was fixed after a first run of this row printed three extra
failures, and mutations 1, 2, 4 and 6 below were re-run against the final test
file.)

## Mutation 9 - the derivation applies a wider suffix set than logo_bytes (accepts .svg and .bin)

### git diff

```
backend/app/services/tenant_service.py | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)

Changes:

backend/app/services/tenant_service.py
@@ -656,7 +656,10 @@ class TenantService:
         tenant id or object name carried by the URL.
         """
         url = getattr(tenant, "logo_url", None)
-        if cls._logo_content_type(url) is None:
+        if not url or (
+            cls._logo_content_type(url) is None
+            and PurePosixPath(url).suffix not in {".svg", ".bin"}
+        ):
             return None
         digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
         return '"' + digest + '"'
  +4 -1
```

### command

```
uv run python -m pytest tests/test_public_logo_route.py --no-cov -q -rf --color=no
```

### result

```
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[svg-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[svg-list-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[bin-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_a_star_is_404_and_never_304_without_a_representation[bin-list-star] - assert 304 == 404
FAILED tests/test_public_logo_route.py::test_the_tag_derivation_refuses_only_the_two_pre_read_refusals - assert '"f77b3f7374d88ad1df44a081e8f06ca43e7163011cd49e9e88da338f2b497b8b"' is None
5 failed, 33 passed, 1 warning in 1.79s
```

Cited ids all present (the `.svg` and `.bin` parameters).

