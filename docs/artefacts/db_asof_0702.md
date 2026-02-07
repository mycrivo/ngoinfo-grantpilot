# Database Schema (as of 07/02)

Source: Railway Postgres, schema=public

## public.alembic_version

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| version_num | character varying | NO |  |

## public.auth_magic_link_tokens

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO |  |
| email | text | NO |  |
| token_hash | text | NO |  |
| requested_ip | text | YES |  |
| user_agent | text | YES |  |
| issued_at | timestamp with time zone | NO | now() |
| expires_at | timestamp with time zone | NO |  |
| consumed_at | timestamp with time zone | YES |  |

## public.auth_oauth_exchange_codes

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO |  |
| user_id | uuid | NO |  |
| code_hash | text | NO |  |
| issued_at | timestamp with time zone | NO | now() |
| expires_at | timestamp with time zone | NO |  |
| consumed_at | timestamp with time zone | YES |  |

## public.auth_refresh_tokens

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO |  |
| user_id | uuid | NO |  |
| token_hash | text | NO |  |
| issued_at | timestamp with time zone | NO | now() |
| expires_at | timestamp with time zone | NO |  |
| revoked_at | timestamp with time zone | YES |  |
| replaced_by_token_id | uuid | YES |  |

## public.fit_scans

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO | gen_random_uuid() |
| user_id | uuid | NO |  |
| funding_opportunity_id | uuid | NO |  |
| plan_at_time_of_scan | text | NO |  |
| prompt_version | text | NO |  |
| model_rating | text | NO |  |
| overall_recommendation | text | NO |  |
| subscores | jsonb | NO |  |
| result_json | jsonb | NO |  |
| created_at | timestamp with time zone | NO | now() |

## public.funding_opportunities

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO | gen_random_uuid() |
| created_at | timestamp without time zone | NO | now() |
| updated_at | timestamp without time zone | NO | now() |
| source_url | text | NO |  |
| application_url | text | NO |  |
| title | text | NO |  |
| donor_organization | text | NO |  |
| funding_type | text | NO |  |
| applicant_type | USER-DEFINED | NO |  |
| location_text | text | NO |  |
| focus_areas | text | NO |  |
| deadline_type | USER-DEFINED | NO |  |
| application_deadline | date | YES |  |
| currency | text | YES |  |
| amount_min | numeric | YES |  |
| amount_max | numeric | YES |  |
| total_funding_available | numeric | YES |  |
| short_summary | text | NO |  |
| overview_text | text | YES |  |
| eligibility_criteria | text | YES |  |
| application_process | text | YES |  |
| status | USER-DEFINED | NO |  |
| is_active | boolean | NO | true |
| is_archived | boolean | NO | false |
| last_verified | date | YES |  |
| requirements_json | jsonb | NO |  |
| organization_types | text | YES |  |
| geographic_focus | text | YES |  |
| contact_information | text | YES |  |
| processing_status | text | YES |  |
| parsing_confidence | numeric | YES |  |
| internal_notes | text | YES |  |

## public.ngo_profiles

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO | gen_random_uuid() |
| user_id | uuid | NO |  |
| organization_name | text | NO |  |
| country_of_registration | text | NO |  |
| mission_statement | text | NO |  |
| focus_sectors | jsonb | NO | '[]'::jsonb |
| geographic_areas_of_work | jsonb | NO | '[]'::jsonb |
| target_groups | jsonb | NO | '[]'::jsonb |
| past_projects | jsonb | NO | '[]'::jsonb |
| profile_status | text | NO | 'DRAFT'::text |
| completeness_score | integer | NO | 0 |
| missing_fields | jsonb | NO | '[]'::jsonb |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| last_completed_at | timestamp with time zone | YES |  |
| year_of_establishment | integer | YES |  |
| contact_person_name | text | YES |  |
| contact_email | text | YES |  |
| website | text | YES |  |
| full_time_staff | integer | YES |  |
| annual_budget_amount | numeric | YES |  |
| annual_budget_currency | text | YES | 'USD'::text |
| monitoring_and_evaluation_practices | text | YES |  |
| funders_worked_with_before | jsonb | NO | '[]'::jsonb |

## public.usage_ledger

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO | gen_random_uuid() |
| user_id | uuid | NO |  |
| action_type | text | NO |  |
| idempotency_key | text | NO |  |
| metadata | jsonb | NO | '{}'::jsonb |
| created_at | timestamp with time zone | NO | now() |

## public.user_plans

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO | gen_random_uuid() |
| user_id | uuid | NO |  |
| plan_name | text | NO |  |
| stripe_subscription_id | text | YES |  |
| billing_period_start | timestamp with time zone | YES |  |
| billing_period_end | timestamp with time zone | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| plan_activated_at | timestamp with time zone | YES |  |

## public.users

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| id | uuid | NO | gen_random_uuid() |
| email | text | NO |  |
| full_name | text | YES |  |
| avatar_url | text | YES |  |
| google_sub | text | YES |  |
| auth_provider | text | NO | 'email'::text |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| last_login_at | timestamp with time zone | YES |  |
| stripe_customer_id | text | YES |  |
