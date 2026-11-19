// 中文说明：供应商适配器：超时、5xx/网络重试和幂等键透传。
package supplier

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/Nolanlua/retail-ordering-agent/order-service/internal/model"
)

// Client adapts the upstream supplier API. Retries are bounded and only used
// for network errors and 5xx; 4xx is a business rejection and must not be retried.
type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

func New(baseURL, token string) *Client {
	return &Client{
		baseURL: baseURL,
		token:   token,
		http:    &http.Client{Timeout: 8 * time.Second},
	}
}

func (c *Client) GetOffers(ctx context.Context, storeID, sku string) ([]model.Offer, error) {
	var payload struct {
		Offers []model.Offer `json:"offers"`
	}
	err := c.do(ctx, http.MethodGet, "/upstream/offers?store_id="+storeID+"&sku="+sku, nil, &payload)
	if err != nil {
		return nil, err
	}
	return payload.Offers, nil
}

func (c *Client) CreateOrder(ctx context.Context, req model.CreateOrderRequest, idempotencyKey string) (string, error) {
	var payload struct {
		SupplierOrderID string `json:"supplier_order_id"`
	}
	err := c.doWithKey(ctx, http.MethodPost, "/upstream/orders", req, &payload, idempotencyKey)
	if err != nil {
		return "", err
	}
	return payload.SupplierOrderID, nil
}

func (c *Client) do(ctx context.Context, method, path string, body any, out any) error {
	return c.doWithKey(ctx, method, path, body, out, "")
}

func (c *Client) doWithKey(ctx context.Context, method, path string, body any, out any, key string) error {
	var lastErr error
	for attempt := 0; attempt < 3; attempt++ {
		raw, err := json.Marshal(body)
		if err != nil {
			return err
		}
		req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, bytes.NewReader(raw))
		if err != nil {
			return err
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer "+c.token)
		if key != "" {
			req.Header.Set("Idempotency-Key", key)
		}
		resp, err := c.http.Do(req)
		if err != nil {
			lastErr = err
			time.Sleep(time.Duration(attempt+1) * 200 * time.Millisecond)
			continue
		}
		data, readErr := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
		resp.Body.Close()
		if readErr != nil {
			return readErr
		}
		if resp.StatusCode >= 500 {
			lastErr = fmt.Errorf("supplier 5xx: %d", resp.StatusCode)
			time.Sleep(time.Duration(attempt+1) * 200 * time.Millisecond)
			continue
		}
		if resp.StatusCode >= 400 {
			return fmt.Errorf("supplier rejected request: %d %s", resp.StatusCode, string(data))
		}
		if out == nil || len(data) == 0 {
			return nil
		}
		if err := json.Unmarshal(data, out); err != nil {
			return err
		}
		return nil
	}
	return errors.New("supplier unavailable after retries: " + lastErr.Error())
}
