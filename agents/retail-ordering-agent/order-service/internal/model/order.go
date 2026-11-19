// 中文说明：订单、请求和供应商报价的数据结构。
package model

import "time"

type Order struct {
	ID              string    `json:"order_id"`
	TenantID        string    `json:"tenant_id"`
	StoreID         string    `json:"store_id"`
	SKU             string    `json:"sku"`
	Qty             int       `json:"qty"`
	SupplierCode    string    `json:"supplier_code"`
	SupplierSKU     string    `json:"supplier_sku"`
	UnitPrice       float64   `json:"unit_price"`
	TotalAmount     float64   `json:"total_amount"`
	Status          string    `json:"status"`
	SupplierOrderID string    `json:"supplier_order_id"`
	Operator        string    `json:"operator"`
	CreatedAt       time.Time `json:"created_at"`
}

type OrderItem struct {
	SKU       string  `json:"sku"`
	Qty       int     `json:"qty"`
	UnitPrice float64 `json:"unit_price"`
}

type CreateOrderRequest struct {
	StoreID      string      `json:"store_id"`
	SKU          string      `json:"sku"`
	Qty          int         `json:"qty"`
	SupplierCode string      `json:"supplier_code"`
	SupplierSKU  string      `json:"supplier_sku"`
	UnitPrice    float64     `json:"unit_price"`
	Operator     string      `json:"operator"`
	Items        []OrderItem `json:"items,omitempty"`
}

type Offer struct {
	SupplierCode string  `json:"supplier_code"`
	SupplierSKU  string  `json:"supplier_sku"`
	AvailableQty int     `json:"available_qty"`
	UnitPrice    float64 `json:"unit_price"`
	MOQ          int     `json:"moq"`
	CasePack     int     `json:"case_pack"`
	LeadTimeDays int     `json:"lead_time_days"`
}
