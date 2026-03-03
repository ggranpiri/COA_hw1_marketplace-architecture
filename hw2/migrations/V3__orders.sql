-- enums
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
    CREATE TYPE order_status AS ENUM (
      'CREATED',
      'PAYMENT_PENDING',
      'PAID',
      'SHIPPED',
      'COMPLETED',
      'CANCELED'
    );
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'discount_type') THEN
    CREATE TYPE discount_type AS ENUM (
      'PERCENTAGE',
      'FIXED_AMOUNT'
    );
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'operation_type') THEN
    CREATE TYPE operation_type AS ENUM (
      'CREATE_ORDER',
      'UPDATE_ORDER'
    );
  END IF;
END $$;

-- promo_codes
CREATE TABLE IF NOT EXISTS promo_codes (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(20) NOT NULL UNIQUE,
  discount_type    discount_type NOT NULL,
  discount_value   NUMERIC(12,2) NOT NULL,
  min_order_amount NUMERIC(12,2) NOT NULL,
  max_uses         INTEGER NOT NULL,
  current_uses     INTEGER NOT NULL DEFAULT 0,
  valid_from       TIMESTAMP NOT NULL,
  valid_until      TIMESTAMP NOT NULL,
  active           BOOLEAN NOT NULL DEFAULT TRUE
);

-- orders
CREATE TABLE IF NOT EXISTS orders (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(id),
  status          order_status NOT NULL,
  promo_code_id   BIGINT NULL REFERENCES promo_codes(id),
  total_amount    NUMERIC(12,2) NOT NULL,
  discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  created_at      TIMESTAMP NOT NULL DEFAULT now(),
  updated_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- order_items
CREATE TABLE IF NOT EXISTS order_items (
  id             BIGSERIAL PRIMARY KEY,
  order_id       BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id     BIGINT NOT NULL REFERENCES products(id),
  quantity       INTEGER NOT NULL,
  price_at_order NUMERIC(12,2) NOT NULL
);

-- user_operations
CREATE TABLE IF NOT EXISTS user_operations (
  id             BIGSERIAL PRIMARY KEY,
  user_id        BIGINT NOT NULL REFERENCES users(id),
  operation_type operation_type NOT NULL,
  created_at     TIMESTAMP NOT NULL DEFAULT now()
);


CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_user_ops_user_type_created ON user_operations(user_id, operation_type, created_at DESC);

