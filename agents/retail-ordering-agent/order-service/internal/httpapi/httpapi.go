// 中文说明：Go 订单服务 HTTP 层：健康检查、供货查询和下单接口。
package httpapi

import (
	"encoding/json"
	"io"
	"net/http"

	"github.com/Nolanlua/retail-ordering-agent/order-service/internal/model"
	"github.com/Nolanlua/retail-ordering-agent/order-service/internal/order"
)

type Handler struct {
	service *order.Service
	token   string
}

func New(service *order.Service, internalToken string) *Handler {
	return &Handler{service: service, token: internalToken}
}

func (h *Handler) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", h.health)
	mux.HandleFunc("GET /internal/suppliers/offers", h.offers)
	mux.HandleFunc("POST /internal/orders", h.createOrder)
	return mux
}

func (h *Handler) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "order-service"})
}

func (h *Handler) offers(w http.ResponseWriter, r *http.Request) {
	if !h.authorized(r) {
		writeError(w, http.StatusUnauthorized, "invalid internal token")
		return
	}
	offers, err := h.service.GetOffers(r.Context(), r.Header.Get("X-Tenant-Id"), r.URL.Query().Get("store_id"), r.URL.Query().Get("sku"))
	if err != nil {
		writeError(w, http.StatusBadGateway, "supplier offers unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"offers": offers})
}

func (h *Handler) createOrder(w http.ResponseWriter, r *http.Request) {
	if !h.authorized(r) {
		writeError(w, http.StatusUnauthorized, "invalid internal token")
		return
	}
	key := r.Header.Get("Idempotency-Key")
	if key == "" {
		writeError(w, http.StatusBadRequest, "Idempotency-Key is required")
		return
	}
	var req model.CreateOrderRequest
	decoder := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	result, idempotent, err := h.service.CreateOrder(r.Context(), r.Header.Get("X-Tenant-Id"), key, req)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"order_id":   result.ID,
		"status":     result.Status,
		"idempotent": idempotent,
	})
}

func (h *Handler) authorized(r *http.Request) bool {
	return h.token == "" || r.Header.Get("X-Internal-Token") == h.token
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]any{"error": map[string]string{"message": message}})
}
