// 中文说明：订单服务环境变量配置。
package config

import (
	"os"
	"strconv"
)

type Config struct {
	Addr          string
	MySQLDSN      string
	SupplierURL   string
	SupplierToken string
	InternalToken string
}

func Load() Config {
	return Config{
		Addr:          env("ORDER_SERVICE_ADDR", ":8020"),
		MySQLDSN:      env("MYSQL_DSN", "agent:agent@tcp(localhost:3306)/agent_orders?parseTime=true&loc=UTC"),
		SupplierURL:   env("SUPPLIER_BASE_URL", "http://localhost:9000"),
		SupplierToken: env("SUPPLIER_TOKEN", "supplier-token"),
		InternalToken: env("ORDER_INTERNAL_TOKEN", "internal-token"),
	}
}

func env(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func envInt(key string, fallback int) int {
	value, err := strconv.Atoi(os.Getenv(key))
	if err != nil {
		return fallback
	}
	return value
}
