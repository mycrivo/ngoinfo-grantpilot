--
-- PostgreSQL database dump
--

\restrict ng7adjbKWbSOQxmT3hbUSa0dJzCXNymc9GVQdffZWvIbC2azTQ1AvoBGXOTNrTf

-- Dumped from database version 17.7 (Debian 17.7-3.pgdg13+1)
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: applicant_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.applicant_type AS ENUM (
    'NGO',
    'INDIVIDUAL',
    'ACADEMIC_INSTITUTION',
    'CONSORTIUM',
    'MIXED'
);


--
-- Name: deadline_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.deadline_type AS ENUM (
    'FIXED',
    'ROLLING',
    'VARIES'
);


--
-- Name: opportunity_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.opportunity_status AS ENUM (
    'DRAFT',
    'READY',
    'PUBLISHED',
    'ARCHIVED'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: auth_magic_link_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_magic_link_tokens (
    id uuid NOT NULL,
    email text NOT NULL,
    token_hash text NOT NULL,
    requested_ip text,
    user_agent text,
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone
);


--
-- Name: auth_oauth_exchange_codes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_oauth_exchange_codes (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    code_hash text NOT NULL,
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone
);


--
-- Name: auth_refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_refresh_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash text NOT NULL,
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    replaced_by_token_id uuid
);


--
-- Name: email_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    event_key text NOT NULL,
    event_type text NOT NULL,
    user_id uuid,
    to_email text NOT NULL,
    status text NOT NULL,
    provider_message_id text,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: fit_scans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fit_scans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    funding_opportunity_id uuid NOT NULL,
    plan_at_time_of_scan text NOT NULL,
    prompt_version text NOT NULL,
    model_rating text NOT NULL,
    overall_recommendation text NOT NULL,
    subscores jsonb NOT NULL,
    result_json jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: funding_opportunities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.funding_opportunities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    source_url text NOT NULL,
    application_url text NOT NULL,
    title text NOT NULL,
    donor_organization text NOT NULL,
    funding_type text NOT NULL,
    applicant_type public.applicant_type NOT NULL,
    location_text text NOT NULL,
    focus_areas text NOT NULL,
    deadline_type public.deadline_type NOT NULL,
    application_deadline date,
    currency text,
    amount_min numeric,
    amount_max numeric,
    total_funding_available numeric,
    short_summary text NOT NULL,
    overview_text text,
    eligibility_criteria text,
    application_process text,
    status public.opportunity_status NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_archived boolean DEFAULT false NOT NULL,
    last_verified date,
    requirements_json jsonb NOT NULL,
    organization_types text,
    geographic_focus text,
    contact_information text,
    processing_status text,
    parsing_confidence numeric,
    internal_notes text,
    CONSTRAINT ck_funding_opportunities_deadline_fixed_requires_date CHECK (((deadline_type <> 'FIXED'::public.deadline_type) OR (application_deadline IS NOT NULL)))
);


--
-- Name: ngo_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ngo_profiles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    organization_name text NOT NULL,
    country_of_registration text NOT NULL,
    mission_statement text NOT NULL,
    focus_sectors jsonb DEFAULT '[]'::jsonb NOT NULL,
    geographic_areas_of_work jsonb DEFAULT '[]'::jsonb NOT NULL,
    target_groups jsonb DEFAULT '[]'::jsonb NOT NULL,
    past_projects jsonb DEFAULT '[]'::jsonb NOT NULL,
    profile_status text DEFAULT 'DRAFT'::text NOT NULL,
    completeness_score integer DEFAULT 0 NOT NULL,
    missing_fields jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_completed_at timestamp with time zone,
    year_of_establishment integer,
    contact_person_name text,
    contact_email text,
    website text,
    full_time_staff integer,
    annual_budget_amount numeric,
    annual_budget_currency text DEFAULT 'USD'::text,
    monitoring_and_evaluation_practices text,
    funders_worked_with_before jsonb DEFAULT '[]'::jsonb NOT NULL
);


--
-- Name: proposals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proposals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    funding_opportunity_id uuid NOT NULL,
    fit_scan_id uuid,
    version integer DEFAULT 1 NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    plan_at_creation text NOT NULL,
    prompt_version text NOT NULL,
    selected_variant_id text,
    content_json jsonb NOT NULL,
    regeneration_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: stripe_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stripe_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    stripe_event_id text NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    processing_result text,
    error_message text
);


--
-- Name: usage_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usage_ledger (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    action_type text NOT NULL,
    idempotency_key text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_plans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    plan_name text NOT NULL,
    stripe_subscription_id text,
    billing_period_start timestamp with time zone,
    billing_period_end timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    plan_activated_at timestamp with time zone,
    CONSTRAINT ck_user_plans_plan_name CHECK ((plan_name = ANY (ARRAY['FREE'::text, 'GROWTH'::text, 'IMPACT'::text])))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email text NOT NULL,
    full_name text,
    avatar_url text,
    google_sub text,
    auth_provider text DEFAULT 'email'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_login_at timestamp with time zone,
    stripe_customer_id text,
    first_login_at timestamp with time zone
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: auth_magic_link_tokens auth_magic_link_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_magic_link_tokens
    ADD CONSTRAINT auth_magic_link_tokens_pkey PRIMARY KEY (id);


--
-- Name: auth_magic_link_tokens auth_magic_link_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_magic_link_tokens
    ADD CONSTRAINT auth_magic_link_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: auth_oauth_exchange_codes auth_oauth_exchange_codes_code_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_oauth_exchange_codes
    ADD CONSTRAINT auth_oauth_exchange_codes_code_hash_key UNIQUE (code_hash);


--
-- Name: auth_oauth_exchange_codes auth_oauth_exchange_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_oauth_exchange_codes
    ADD CONSTRAINT auth_oauth_exchange_codes_pkey PRIMARY KEY (id);


--
-- Name: auth_refresh_tokens auth_refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: auth_refresh_tokens auth_refresh_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: email_events email_events_event_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_events
    ADD CONSTRAINT email_events_event_key_key UNIQUE (event_key);


--
-- Name: email_events email_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_events
    ADD CONSTRAINT email_events_pkey PRIMARY KEY (id);


--
-- Name: fit_scans fit_scans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fit_scans
    ADD CONSTRAINT fit_scans_pkey PRIMARY KEY (id);


--
-- Name: funding_opportunities funding_opportunities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.funding_opportunities
    ADD CONSTRAINT funding_opportunities_pkey PRIMARY KEY (id);


--
-- Name: ngo_profiles ngo_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ngo_profiles
    ADD CONSTRAINT ngo_profiles_pkey PRIMARY KEY (id);


--
-- Name: proposals proposals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proposals
    ADD CONSTRAINT proposals_pkey PRIMARY KEY (id);


--
-- Name: stripe_events stripe_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stripe_events
    ADD CONSTRAINT stripe_events_pkey PRIMARY KEY (id);


--
-- Name: stripe_events stripe_events_stripe_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stripe_events
    ADD CONSTRAINT stripe_events_stripe_event_id_key UNIQUE (stripe_event_id);


--
-- Name: ngo_profiles uq_ngo_profiles_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ngo_profiles
    ADD CONSTRAINT uq_ngo_profiles_user_id UNIQUE (user_id);


--
-- Name: user_plans uq_user_plans_stripe_subscription_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_plans
    ADD CONSTRAINT uq_user_plans_stripe_subscription_id UNIQUE (stripe_subscription_id);


--
-- Name: user_plans uq_user_plans_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_plans
    ADD CONSTRAINT uq_user_plans_user_id UNIQUE (user_id);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: users uq_users_google_sub; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_google_sub UNIQUE (google_sub);


--
-- Name: users uq_users_stripe_customer_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_stripe_customer_id UNIQUE (stripe_customer_id);


--
-- Name: usage_ledger usage_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT usage_ledger_pkey PRIMARY KEY (id);


--
-- Name: user_plans user_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_plans
    ADD CONSTRAINT user_plans_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_email_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_email_events_created_at ON public.email_events USING btree (created_at);


--
-- Name: idx_fit_scans_opportunity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fit_scans_opportunity ON public.fit_scans USING btree (funding_opportunity_id);


--
-- Name: idx_fit_scans_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fit_scans_user_created ON public.fit_scans USING btree (user_id, created_at DESC);


--
-- Name: idx_fit_scans_user_opportunity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fit_scans_user_opportunity ON public.fit_scans USING btree (user_id, funding_opportunity_id);


--
-- Name: idx_proposals_opportunity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proposals_opportunity ON public.proposals USING btree (funding_opportunity_id);


--
-- Name: idx_proposals_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proposals_user_created ON public.proposals USING btree (user_id, created_at DESC);


--
-- Name: idx_usage_ledger_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_ledger_action ON public.usage_ledger USING btree (action_type);


--
-- Name: idx_usage_ledger_idempotency; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_usage_ledger_idempotency ON public.usage_ledger USING btree (idempotency_key);


--
-- Name: idx_usage_ledger_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_ledger_user ON public.usage_ledger USING btree (user_id);


--
-- Name: idx_usage_ledger_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_ledger_user_created ON public.usage_ledger USING btree (user_id, created_at DESC);


--
-- Name: idx_user_plans_stripe_sub; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_plans_stripe_sub ON public.user_plans USING btree (stripe_subscription_id) WHERE (stripe_subscription_id IS NOT NULL);


--
-- Name: idx_user_plans_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_plans_user ON public.user_plans USING btree (user_id);


--
-- Name: ix_auth_magic_link_tokens_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_magic_link_tokens_email ON public.auth_magic_link_tokens USING btree (email);


--
-- Name: ix_auth_magic_link_tokens_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_magic_link_tokens_expires_at ON public.auth_magic_link_tokens USING btree (expires_at);


--
-- Name: ix_auth_oauth_exchange_codes_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_oauth_exchange_codes_expires_at ON public.auth_oauth_exchange_codes USING btree (expires_at);


--
-- Name: ix_auth_oauth_exchange_codes_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_oauth_exchange_codes_user_id ON public.auth_oauth_exchange_codes USING btree (user_id);


--
-- Name: ix_auth_refresh_tokens_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_refresh_tokens_expires_at ON public.auth_refresh_tokens USING btree (expires_at);


--
-- Name: ix_auth_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_refresh_tokens_user_id ON public.auth_refresh_tokens USING btree (user_id);


--
-- Name: ix_stripe_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stripe_events_event_type ON public.stripe_events USING btree (event_type);


--
-- Name: ix_stripe_events_processing_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stripe_events_processing_result ON public.stripe_events USING btree (processing_result);


--
-- Name: ix_stripe_events_received_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stripe_events_received_at ON public.stripe_events USING btree (received_at);


--
-- Name: uq_users_email_canonical; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_users_email_canonical ON public.users USING btree (lower(TRIM(BOTH FROM email)));


--
-- Name: auth_oauth_exchange_codes auth_oauth_exchange_codes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_oauth_exchange_codes
    ADD CONSTRAINT auth_oauth_exchange_codes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: auth_refresh_tokens auth_refresh_tokens_replaced_by_token_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_replaced_by_token_id_fkey FOREIGN KEY (replaced_by_token_id) REFERENCES public.auth_refresh_tokens(id);


--
-- Name: auth_refresh_tokens auth_refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: email_events email_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_events
    ADD CONSTRAINT email_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: fit_scans fit_scans_funding_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fit_scans
    ADD CONSTRAINT fit_scans_funding_opportunity_id_fkey FOREIGN KEY (funding_opportunity_id) REFERENCES public.funding_opportunities(id);


--
-- Name: fit_scans fit_scans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fit_scans
    ADD CONSTRAINT fit_scans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: ngo_profiles ngo_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ngo_profiles
    ADD CONSTRAINT ngo_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: proposals proposals_fit_scan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proposals
    ADD CONSTRAINT proposals_fit_scan_id_fkey FOREIGN KEY (fit_scan_id) REFERENCES public.fit_scans(id);


--
-- Name: proposals proposals_funding_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proposals
    ADD CONSTRAINT proposals_funding_opportunity_id_fkey FOREIGN KEY (funding_opportunity_id) REFERENCES public.funding_opportunities(id);


--
-- Name: proposals proposals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proposals
    ADD CONSTRAINT proposals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: usage_ledger usage_ledger_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT usage_ledger_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_plans user_plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_plans
    ADD CONSTRAINT user_plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ng7adjbKWbSOQxmT3hbUSa0dJzCXNymc9GVQdffZWvIbC2azTQ1AvoBGXOTNrTf

