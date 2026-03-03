CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_operations_user_type_created ON user_operations(user_id, operation_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);