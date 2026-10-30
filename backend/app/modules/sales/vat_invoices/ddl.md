-- Table: public.vat_invoices

-- DROP TABLE IF EXISTS public.vat_invoices;

CREATE TABLE IF NOT EXISTS public.vat_invoices
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text COLLATE pg_catalog."default" NOT NULL,
    date date,
    "number" text COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    customer_id uuid NOT NULL,
    amount_incl_vat numeric(15,2) NOT NULL DEFAULT 0,
    amount_excl_vat numeric(15,2) NOT NULL DEFAULT 0,
    vat_rate numeric(5,2) NOT NULL DEFAULT 0,
    vat_amount numeric(15,2) NOT NULL DEFAULT 0,
    doc_status text COLLATE pg_catalog."default" DEFAULT 'draft'::text,
    approved_date timestamp with time zone,
    approved_by_person_id uuid,
    accepted_date timestamp with time zone,
    accepted_by_person_id uuid,
    section_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    username text COLLATE pg_catalog."default",
    author_id uuid NOT NULL,
    editor_id uuid NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    timestamptz timestamp with time zone DEFAULT now(),
    date_created timestamp with time zone DEFAULT now(),
    editing_by_user_id uuid,
    editing_since timestamp with time zone,
    access_tags text[] COLLATE pg_catalog."default",
    user_tags text[] COLLATE pg_catalog."default",
    our_legal_entity_id uuid DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    ledger_record_id uuid DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    warehouse_id uuid,
    trade_in_out text COLLATE pg_catalog."default" DEFAULT 'out'::text,
    CONSTRAINT vat_invoice_pkey PRIMARY KEY (id)
)
