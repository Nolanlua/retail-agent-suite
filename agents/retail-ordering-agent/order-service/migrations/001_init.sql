create table if not exists purchase_orders (
    id varchar(64) primary key,
    tenant_id varchar(64) not null,
    store_id varchar(32) not null,
    sku varchar(64) not null,
    qty int not null,
    supplier_code varchar(32) not null,
    supplier_sku varchar(64) not null,
    unit_price decimal(12,2) not null,
    total_amount decimal(14,2) not null,
    status varchar(32) not null,
    supplier_order_id varchar(128) not null default '',
    operator varchar(64) not null,
    created_at timestamp(3) not null,
    key ix_orders_tenant_store (tenant_id, store_id, created_at)
);

create table if not exists purchase_order_items (
    id varchar(64) primary key,
    order_id varchar(64) not null,
    sku varchar(64) not null,
    qty int not null,
    unit_price decimal(12,2) not null,
    key ix_items_order (order_id)
);

create table if not exists idempotency_keys (
    tenant_id varchar(64) not null,
    idempotency_key varchar(128) not null,
    order_id varchar(64) not null,
    response_json json not null,
    created_at timestamp(3) not null,
    primary key (tenant_id, idempotency_key),
    key ix_idem_order (order_id)
);

create table if not exists outbox_events (
    id varchar(64) primary key,
    aggregate_type varchar(64) not null,
    aggregate_id varchar(64) not null,
    event_type varchar(64) not null,
    payload json not null,
    status varchar(16) not null default 'pending',
    created_at timestamp(3) not null,
    key ix_outbox_status (status, created_at)
);

create table if not exists supplier_products (
    tenant_id varchar(64) not null,
    sku varchar(64) not null,
    supplier_code varchar(32) not null,
    supplier_sku varchar(64) not null,
    primary key (tenant_id, sku, supplier_code)
);
