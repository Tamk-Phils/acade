-- =========================================================================
-- AcadFormat Enterprise Database Schema for Supabase
-- Run this script in your Supabase SQL Editor to provision tables & indexes.
-- =========================================================================

-- 1. Documents Table
CREATE TABLE IF NOT EXISTS public.acadformat_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    school_type TEXT NOT NULL,
    compliance_score INTEGER DEFAULT 0,
    title TEXT,
    author TEXT,
    reg_number TEXT,
    department TEXT,
    page_count INTEGER DEFAULT 1,
    status TEXT DEFAULT 'audited',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_acadformat_documents_token ON public.acadformat_documents(token);
CREATE INDEX IF NOT EXISTS idx_acadformat_documents_created ON public.acadformat_documents(created_at DESC);

-- 2. Reformatted Outputs Table
CREATE TABLE IF NOT EXISTS public.acadformat_reformats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT NOT NULL REFERENCES public.acadformat_documents(token) ON DELETE CASCADE,
    docx_path TEXT,
    pdf_path TEXT,
    page_count INTEGER DEFAULT 1,
    reformatted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_acadformat_reformats_token ON public.acadformat_reformats(token);

-- 3. Users Table (Authentication, RBAC & Device Locking)
CREATE TABLE IF NOT EXISTS public.acadformat_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'super_admin')),
    registered_device_id TEXT,
    trial_expires_at TIMESTAMPTZ NOT NULL,
    paid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_acadformat_users_username ON public.acadformat_users(username);
CREATE INDEX IF NOT EXISTS idx_acadformat_users_email ON public.acadformat_users(email);
CREATE INDEX IF NOT EXISTS idx_acadformat_users_role ON public.acadformat_users(role);

-- 4. Mobile Money Payments Table (MTN MoMo & Orange Money)
CREATE TABLE IF NOT EXISTS public.acadformat_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.acadformat_users(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 250,
    currency TEXT DEFAULT 'XAF',
    operator TEXT NOT NULL CHECK (operator IN ('mtn_momo', 'orange_money')),
    phone_number TEXT NOT NULL,
    transaction_ref TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'completed',
    paid_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_acadformat_payments_user ON public.acadformat_payments(user_id);
CREATE INDEX IF NOT EXISTS idx_acadformat_payments_ref ON public.acadformat_payments(transaction_ref);

-- 5. System Configuration
CREATE TABLE IF NOT EXISTS public.acadformat_system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO public.acadformat_system_config (key, value) VALUES
    ('trial_duration_hours', '72'),
    ('subscription_price_xaf', '250'),
    ('subscription_duration_days', '7')
ON CONFLICT (key) DO NOTHING;

-- 6. Row Level Security (RLS) Configuration
ALTER TABLE public.acadformat_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.acadformat_reformats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.acadformat_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.acadformat_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.acadformat_system_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read & write to documents" ON public.acadformat_documents FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon read & write to reformats" ON public.acadformat_reformats FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon read & write to users" ON public.acadformat_users FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon read & write to payments" ON public.acadformat_payments FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon read to config" ON public.acadformat_system_config FOR SELECT TO anon, authenticated USING (true);
