// 中文说明：订单业务：幂等检查、供应商下单和本地事务落库。
package order

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/Nolanlua/retail-ordering-agent/order-service/internal/model"
	"github.com/Nolanlua/retail-ordering-agent/order-service/internal/repository"
	"github.com/Nolanlua/retail-ordering-agent/order-service/internal/supplier"
)

type Service struct {
	repo     *repository.Repository
	supplier *supplier.Client
}

func New(repo *repository.Repository, supplierClient *supplier.Client) *Service {
	return &Service{repo: repo, supplier: supplierClient}
}

func (s *Service) GetOffers(ctx context.Context, tenantID, storeID, sku string) ([]model.Offer, error) {
	return s.supplier.GetOffers(ctx, storeID, sku)
}

func (s *Service) CreateOrder(ctx context.Context, tenantID, key string, req model.CreateOrderRequest) (*model.Order, bool, error) {
	if key == "" {
		return nil, false, errors.New("idempotency key is required")
	}
	if req.StoreID == "" || req.SKU == "" || req.Qty <= 0 || req.UnitPrice <= 0 {
		return nil, false, errors.New("invalid order payload")
	}
	if existing, found, err := s.repo.FindByKey(ctx, tenantID, key); err != nil {
		return nil, false, err
	} else if found {
		return existing, true, nil
	}

	supplierOrderID, err := s.supplier.CreateOrder(ctx, req, key)
	if err != nil {
		return nil, false, fmt.Errorf("supplier order failed: %w", err)
	}

	order := &model.Order{
		ID:              fmt.Sprintf("PO-%d", time.Now().UnixNano()),
		TenantID:        tenantID,
		StoreID:         req.StoreID,
		SKU:             req.SKU,
		Qty:             req.Qty,
		SupplierCode:    req.SupplierCode,
		SupplierSKU:     req.SupplierSKU,
		UnitPrice:       req.UnitPrice,
		TotalAmount:     float64(req.Qty) * req.UnitPrice,
		Status:          "confirmed",
		SupplierOrderID: supplierOrderID,
		Operator:        req.Operator,
		CreatedAt:       time.Now().UTC(),
	}
	if err := s.repo.SaveOrder(ctx, order, key); err != nil {
		if errors.Is(err, repository.ErrDuplicateIdempotency) {
			existing, found, findErr := s.repo.FindByKey(ctx, tenantID, key)
			if findErr != nil {
				return nil, false, findErr
			}
			if found {
				return existing, true, nil
			}
		}
		return nil, false, err
	}
	return order, false, nil
}
