Status: Canonical (LOCKED FOR BUILD)
System of record: Railway Postgres (GrantPilot DB)
Applies to: users table, auth linkage

1) Canonical Table: users
1.1 Required columns

id (UUID, primary key, server-generated)
email (text, not null, unique, stored lowercased)
auth_provider (text, not null, default "email") — enum-like: email|google
created_at (timestamptz, not null, default now())
updated_at (timestamptz, not null, default now())

1.2 Optional columns

full_name (text, nullable)
avatar_url (text, nullable)
google_sub (text, nullable, unique) — subject from Google
last_login_at (timestamptz, nullable)

Rules
- Accounts are linked by email across OAuth and Magic Link.
