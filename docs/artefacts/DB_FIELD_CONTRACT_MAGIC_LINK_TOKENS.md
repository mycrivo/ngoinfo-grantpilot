Status: Canonical (LOCKED FOR BUILD)
System of record: Railway Postgres (GrantPilot DB)
Applies to: auth_magic_link_tokens table

1) Canonical Table: auth_magic_link_tokens
1.1 Required columns

id (UUID, primary key)
email (text, not null, stored lowercased)
token_hash (text, not null, unique)
issued_at (timestamptz, not null, default now())
expires_at (timestamptz, not null) — configurable TTL via AUTH_MAGIC_LINK_TTL_MIN (default 15 minutes)

1.2 Optional columns

requested_ip (text, nullable)
user_agent (text, nullable)
consumed_at (timestamptz, nullable)

Indexes
- index on (email)
- index on (expires_at)

Rules
- Token is single-use; if consumed_at is set, reject reuse.
