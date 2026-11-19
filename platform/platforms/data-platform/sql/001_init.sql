-- Data platform schema. Run once per environment through the migration job.
create extension if not exists "pgcrypto";

create table if not exists data_assets (
    id uuid primary key default gen_random_uuid(),
    tenant_id varchar(64) not null,
    name varchar(128) not null,
    domain varchar(32) not null,
    asset_type varchar(32) not null,
    storage_uri text not null,
    owner varchar(128) not null,
    sensitivity varchar(32) not null default 'internal',
    description text not null default '',
    version integer not null default 1,
    created_at timestamptz not null default now(),
    constraint uq_asset_version unique (tenant_id, name, version)
);

create table if not exists quality_runs (
    id uuid primary key default gen_random_uuid(),
    tenant_id varchar(64) not null,
    asset_id uuid not null references data_assets(id),
    ruleset varchar(64) not null,
    status varchar(16) not null default 'running',
    checked_rows integer not null default 0,
    failed_rows integer not null default 0,
    report jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists feature_snapshots (
    id uuid primary key default gen_random_uuid(),
    tenant_id varchar(64) not null,
    feature_view varchar(64) not null,
    entity_key varchar(256) not null,
    business_date timestamptz not null,
    payload jsonb not null,
    version varchar(32) not null default 'v1',
    created_at timestamptz not null default now(),
    constraint uq_feature_point unique (tenant_id, feature_view, entity_key, business_date)
);
create index if not exists ix_feature_lookup
    on feature_snapshots (tenant_id, feature_view, entity_key, business_date);

create table if not exists lineage_edges (
    id uuid primary key default gen_random_uuid(),
    tenant_id varchar(64) not null,
    upstream varchar(256) not null,
    downstream varchar(256) not null,
    job_name varchar(128) not null,
    transform_sql text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists data_metrics (
    id uuid primary key default gen_random_uuid(),
    tenant_id varchar(64) not null,
    metric_name varchar(128) not null,
    metric_value double precision not null,
    dimensions jsonb not null default '{}'::jsonb,
    business_date timestamptz,
    created_at timestamptz not null default now()
);
