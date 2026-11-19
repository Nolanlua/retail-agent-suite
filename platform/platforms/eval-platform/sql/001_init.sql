create extension if not exists "pgcrypto";

create table if not exists eval_datasets (
    id uuid primary key default gen_random_uuid(),
    tenant_id varchar(64) not null,
    name varchar(128) not null,
    benchmark varchar(32) not null,
    version varchar(32) not null default 'v1',
    description text not null default '',
    case_count integer not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists eval_cases (
    id uuid primary key default gen_random_uuid(),
    dataset_id uuid not null references eval_datasets(id),
    case_key varchar(64) not null,
    payload jsonb not null,
    expected jsonb not null default '{}'::jsonb
);

create table if not exists eval_runs (
    id uuid primary key default gen_random_uuid(),
    tenant_id varchar(64) not null,
    dataset_id uuid not null references eval_datasets(id),
    target_name varchar(64) not null,
    target_url text not null,
    status varchar(16) not null default 'running',
    metrics jsonb not null default '{}'::jsonb,
    error text not null default '',
    started_at timestamptz not null default now(),
    finished_at timestamptz
);

create table if not exists eval_results (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references eval_runs(id),
    case_key varchar(64) not null,
    output jsonb not null default '{}'::jsonb,
    scores jsonb not null default '{}'::jsonb,
    passed boolean not null default false,
    latency_ms integer not null default 0,
    created_at timestamptz not null default now()
);
create index if not exists ix_eval_results_run on eval_results(run_id);
