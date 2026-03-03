from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
    Enum as SAEnum,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship



class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = mapped_column(BigInteger, primary_key=True)
    email = mapped_column(String(320))
    password_hash = mapped_column(String(255))

    role = mapped_column(
        SAEnum("USER", "SELLER", "ADMIN", name="user_role", native_enum=True),
        nullable=False,
    )

    created_at = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)


class Product(Base):
    __tablename__ = "products"

    id = mapped_column(BigInteger, primary_key=True)
    name = mapped_column(String(255), nullable=False)
    description = mapped_column(String(4000), nullable=True)
    price = mapped_column(Numeric(12, 2), nullable=False)
    stock = mapped_column(Integer, nullable=False)
    category = mapped_column(String(100), nullable=False)

    status = mapped_column(
        SAEnum("ACTIVE", "INACTIVE", "ARCHIVED", name="product_status", native_enum=True),
        nullable=False,
    )

    seller_id = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    created_at = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime, server_default=func.now(), nullable=False)



order_status_enum = ENUM(
    "CREATED",
    "PAYMENT_PENDING",
    "PAID",
    "SHIPPED",
    "COMPLETED",
    "CANCELED",
    name="order_status",
    create_type=False,
)

discount_type_enum = ENUM(
    "PERCENTAGE",
    "FIXED_AMOUNT",
    name="discount_type",
    create_type=False,
)

operation_type_enum = ENUM(
    "CREATE_ORDER",
    "UPDATE_ORDER",
    name="operation_type",
    create_type=False,
)


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    discount_type: Mapped[str] = mapped_column(discount_type_enum, nullable=False)
    discount_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    min_order_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False)
    current_uses: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    valid_from = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    orders: Mapped[List["Order"]] = relationship(back_populates="promo_code")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    status: Mapped[str] = mapped_column(order_status_enum, nullable=False)
    promo_code_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("promo_codes.id"), nullable=True
    )

    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))

    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    promo_code: Mapped[Optional["PromoCode"]] = relationship(back_populates="orders")

    # user: Mapped["User"] = relationship(back_populates="orders")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    price_at_order: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    # product: Mapped["Product"] = relationship()


class UserOperation(Base):
    __tablename__ = "user_operations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    operation_type: Mapped[str] = mapped_column(operation_type_enum, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))