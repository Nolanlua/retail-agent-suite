// 中文说明：订单仓储：MySQL 事务、幂等记录和 Outbox 事件。
package repository

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"time"

	"github.com/go-sql-driver/mysql"
	"github.com/Nolanlua/retail-ordering-agent/order-service/internal/model"
)

var ErrDuplicateIdempotency = errors.New("duplicate idempotency key")

type Repository struct {
	db *sql.DB
}

func New(db *sql.DB) *Repository {
	return &Repository{db: db}
}

func (r *Repository) FindByKey(ctx context.Context, tenantID, key string) (*model.Order, bool, error) {
	var raw []byte
	err := r.db.QueryRowContext(ctx,
		"SELECT response_json FROM idempotency_keys WHERE tenant_id = ? AND idempotency_key = ?",
		tenantID, key,
	).Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, err
	}
	var order model.Order
	if err := json.Unmarshal(raw, &order); err != nil {
		return nil, false, err
	}
	return &order, true, nil
}

// SaveOrder writes the order, its items, the idempotency record and an outbox
// event in one local transaction. The unique key on idempotency_keys is the
// final arbiter under concurrency.
func (r *Repository) SaveOrder(ctx context.Context, order *model.Order, key string) error {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()

	_, err = tx.ExecContext(ctx,
		"INSERT INTO purchase_orders (id, tenant_id, store_id, sku, qty, supplier_code, supplier_sku, unit_price, total_amount, status, supplier_order_id, operator, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
		order.ID, order.TenantID, order.StoreID, order.SKU, order.Qty, order.SupplierCode, order.SupplierSKU,
		order.UnitPrice, order.TotalAmount, order.Status, order.SupplierOrderID, order.Operator, order.CreatedAt,
	)
	if err != nil {
		return err
	}
	_, err = tx.ExecContext(ctx,
		"INSERT INTO purchase_order_items (id, order_id, sku, qty, unit_price) VALUES (UUID(),?,?,?,?)",
		order.ID, order.SKU, order.Qty, order.UnitPrice,
	)
	if err != nil {
		return err
	}

	responseJSON, err := json.Marshal(order)
	if err != nil {
		return err
	}
	_, err = tx.ExecContext(ctx,
		"INSERT INTO idempotency_keys (tenant_id, idempotency_key, order_id, response_json, created_at) VALUES (?,?,?,?,?)",
		order.TenantID, key, order.ID, responseJSON, time.Now(),
	)
	if err != nil {
		// MySQL duplicate key is reported as 1062. Keep the repository contract
		// explicit so the service can re-read the winning request.
		if isDuplicate(err) {
			return ErrDuplicateIdempotency
		}
		return err
	}
	_, err = tx.ExecContext(ctx,
		"INSERT INTO outbox_events (id, aggregate_type, aggregate_id, event_type, payload, status, created_at) VALUES (UUID(),?,?,?,?,?,?)",
		"purchase_order", order.ID, "order.confirmed", string(responseJSON), "pending", time.Now(),
	)
	if err != nil {
		return err
	}
	return tx.Commit()
}

func isDuplicate(err error) bool {
	var mysqlErr *mysql.MySQLError
	if errors.As(err, &mysqlErr) {
		return mysqlErr.Number == 1062
	}
	return false
}
