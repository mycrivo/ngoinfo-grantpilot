Status: Canonical (LOCKED FOR BUILD)
System of record: Railway Postgres (GrantPilot DB)
Applies to: auth_refresh_tokens table

1) Canonical Table: auth_refresh_tokens
1.1 Required columns

id (UUID, primary key)
user_id (UUID, not null, FK → users.id, on delete cascade)
token_hash (text, not null, unique)
issued_at (timestamptz, not null, default now())
expires_at (timestamptz, not null)

1.2 Optional columns

revoked_at (timestamptz, nullable)
replaced_by_token_id (UUID, nullable, FK → auth_refresh_tokens.id)

Indexes
- index on (user_id)
- index on (expires_at)

Rules
- Only one active token per user is allowed (enforced in app logic for MVP).
