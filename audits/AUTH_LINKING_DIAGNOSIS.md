# Auth Account-Linking Failure Diagnosis

**Date:** 2026-06-06  
**Scope:** `tests/test_auth_account_linking.py` — two failures only  
**Mode:** Read-only (no source/test/config edits)  
**Commit context:** `74b0a91` on `main`

---

## 1. Verdict

### **TEST-ONLY** (stale test; production code correct)

Both functions under test legitimately return `(User, bool)` since commit `1ec3dcc`; production routes unpack the tuple correctly. The tests still assign the full return value to a single variable and call `.id` on the tuple — a test contract drift, not a live auth bug.

---

## 2. Exact Failure Point

### `test_google_then_magic_link_links_same_user`

**Traceback excerpt (pytest run 2026-06-06):**

```text
tests/test_auth_account_linking.py:39: in test_google_then_magic_link_links_same_user
    assert magic_user.id == google_user.id
E   AttributeError: 'tuple' object has no attribute 'id'
```

**Call chain:**

| Step | File:line | What happens |
|------|-----------|--------------|
| 1 | `tests/test_auth_account_linking.py:31-37` | `google_user = get_or_create_user_for_google(...)` → receives `(User, bool)`, not unpacked |
| 2 | `tests/test_auth_account_linking.py:38` | `magic_user = get_or_create_user_for_magic_link(...)` → receives `(User, bool)`, not unpacked |
| 3 | `tests/test_auth_account_linking.py:39` | `magic_user.id` — **AttributeError** (`magic_user` is a 2-tuple) |

Note: `google_user` is also a tuple; the assertion fails on the left operand (`magic_user.id`) first.

---

### `test_magic_link_then_google_links_same_user`

**Traceback excerpt:**

```text
tests/test_auth_account_linking.py:53: in test_magic_link_then_google_links_same_user
    assert magic_user.id == google_user.id
E   AttributeError: 'tuple' object has no attribute 'id'
```

**Call chain:**

| Step | File:line | What happens |
|------|-----------|--------------|
| 1 | `tests/test_auth_account_linking.py:45` | `magic_user = get_or_create_user_for_magic_link(...)` → tuple, not unpacked |
| 2 | `tests/test_auth_account_linking.py:46-52` | `google_user = get_or_create_user_for_google(...)` → tuple, not unpacked |
| 3 | `tests/test_auth_account_linking.py:53` | `magic_user.id` — **AttributeError** |

---

### Shared root cause

**One issue, two tests:** both tests assign the return value of `get_or_create_user_for_*` directly to a variable named `*_user` and treat it as a `User`. Since `1ec3dcc`, both functions return `tuple[User, bool]`.

---

## 3. Function Return Shape

### `get_or_create_user_for_google`

| Attribute | Detail |
|-----------|--------|
| **Defined** | `app/services/auth_service.py:28-70` |
| **Current return type** | `tuple[User, bool]` — annotated at line 35 |
| **Semantics** | `(user, is_new_user)` — `True` when a new row is created (line 70), `False` when existing user matched by `google_sub` (line 46) or email (line 58) |

### `get_or_create_user_for_magic_link`

| Attribute | Detail |
|-----------|--------|
| **Defined** | `app/services/auth_service.py:73-91` |
| **Current return type** | `tuple[User, bool]` — annotated at line 73 |
| **Semantics** | `(user, is_new_user)` — `True` on create (line 91), `False` on email match (line 82) |

### When the shape changed

| Commit | Date | Change |
|--------|------|--------|
| `1ec3dcc` | 2026-04-12 | `feat(email): centralize templates and wire transactional triggers` — both functions changed from `-> User` / `return user` to `-> tuple[User, bool]` / `return user, True\|False` to support `maybe_send_welcome_for_new_user(is_new_user=...)` |

**Prior shape:** single `User` (last test-aligned version at `c852935`).

**Test file last touched:** `c852935` (`Replace Google OAuth with Authlib and link accounts`) — **before** the tuple change. The test file has **not** been updated since `1ec3dcc`.

---

## 4. Production Caller Analysis

Repo-wide grep finds **only two production call sites** (excluding tests):

| Caller | File:line | How return is consumed | Break at runtime? |
|--------|-----------|------------------------|-------------------|
| Google OAuth callback / exchange | `app/api/routes/auth.py:374-380` | `user, is_new_user = get_or_create_user_for_google(...)` then `user.id`, `maybe_send_welcome_for_new_user(user=user, is_new_user=is_new_user)` at 388-390 | **N** |
| Magic-link consume | `app/api/routes/auth.py:540-546` | `user, is_new_user = get_or_create_user_for_magic_link(...)` then `user.id`, token issue, welcome email | **N** |

No other modules import or call these functions (`rg` across `app/**/*.py`).

**Account-linking logic in the service layer (unchanged intent):**

- Google path links `google_sub` onto an existing email user: `auth_service.py:48-58`
- Magic-link path finds user by normalized email: `auth_service.py:75-82`
- Email normalization shared: `normalize_email()` `auth_service.py:24-25`

Production callers never dereference `.id` on the raw tuple return value.

---

## 5. Test vs Production

| Aspect | Production (`auth.py`) | Tests (`test_auth_account_linking.py`) |
|--------|------------------------|----------------------------------------|
| Google function | `user, is_new_user = get_or_create_user_for_google(...)` | `google_user = get_or_create_user_for_google(...)` |
| Magic-link function | `user, is_new_user = get_or_create_user_for_magic_link(...)` | `magic_user = get_or_create_user_for_magic_link(...)` |
| Uses `.id` on | `user` (unpacked `User`) | `magic_user` / `google_user` (actually `tuple`) |

**Divergence:** Tests use the pre-`1ec3dcc` calling convention (single-object return). Production was updated in the same email commit that changed the return type; tests were not.

**What the tests never reach:** Assertions about same-user linking (`magic_user.id == google_user.id`, `google_sub` preserved) — the AttributeError fires before linking behaviour is exercised. From **code review** (not test execution), linking logic in `auth_service.py` remains consistent with the tests' intent.

---

## 6. Blast Radius

**Not applicable** — verdict is TEST-ONLY.

If this were a live bug, affected flows would be Google OAuth login and magic-link login. Production paths unpack correctly; no user-visible symptom expected from this specific `'tuple' object has no attribute 'id'` pattern in deployed routes.

---

## 7. Suggested Owner & Fix Direction (NOT applied)

**Owner:** Auth/test hygiene (pre-B-series or CI triage).  
**Fix direction:** Update `tests/test_auth_account_linking.py` to unpack `(user, is_new_user) = get_or_create_user_for_*` (or index `[0]`) before asserting on `.id` and `google_sub` — mirroring `auth.py:374` and `auth.py:540`. Optionally assert `is_new_user` on first vs second call if welcome-email semantics matter for the test scenario.

---

*End of diagnosis. No code, tests, or config were modified.*
