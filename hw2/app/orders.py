from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from decimal import Decimal


from app.models import (
    Order,
    OrderItem,
    Product,
    PromoCode,
    UserOperation,
)
from app.errors import AppError
from app.settings import settings


async def create_order(session: AsyncSession, user, body):
    async with session.begin():

        user_id = int(user["id"]) if isinstance(user, dict) else int(user.id)

        # 1 RATE LIMIT
        last_op = await session.scalar(
            select(UserOperation)
            .where(
                and_(
                    UserOperation.user_id == user_id,
                    UserOperation.operation_type == "CREATE_ORDER",
                )
            )
            .order_by(UserOperation.created_at.desc())
            .limit(1)
        )

        if last_op:
            delta = datetime.utcnow() - last_op.created_at
            if delta < timedelta(minutes=settings.ORDER_RATE_LIMIT_MINUTES):
                raise AppError("ORDER_LIMIT_EXCEEDED", 429, "Too many order creations")

        # 2 ACTIVE ORDER CHECK
        active = await session.scalar(
            select(Order).where(
                and_(
                    Order.user_id == user_id,
                    Order.status.in_(["CREATED", "PAYMENT_PENDING"]),
                )
            )
        )

        if active:
            raise AppError("ORDER_HAS_ACTIVE", 409, "User already has active order")

        # 3 LOAD PRODUCTS WITH FOR UPDATE
        product_ids = [item.product_id for item in body.items]

        products = (
            await session.execute(
                select(Product)
                .where(Product.id.in_(product_ids))
                .with_for_update()
            )
        ).scalars().all()

        if len(products) != len(product_ids):
            raise AppError("PRODUCT_NOT_FOUND", 404, "Some products not found")

        product_map = {p.id: p for p in products}

        # 4 STOCK CHECK
        insufficient = []

        for item in body.items:
            product = product_map[item.product_id]

            if product.status != "ACTIVE":
                raise AppError("PRODUCT_INACTIVE", 409, f"Product {product.id} inactive")

            if product.stock < item.quantity:
                insufficient.append(
                    {
                        "product_id": product.id,
                        "requested": item.quantity,
                        "available": product.stock,
                    }
                )

        if insufficient:
            raise AppError(
                "INSUFFICIENT_STOCK",
                409,
                "Insufficient stock",
                {"items": insufficient},
            )

        # 5 RESERVE STOCK
        for item in body.items:
            product_map[item.product_id].stock -= item.quantity

        # 6 CALCULATE TOTAL
        total = 0
        order_items = []

        for item in body.items:
            product = product_map[item.product_id]
            price = product.price
            total += price * item.quantity

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=item.quantity,
                    price_at_order=price,
                )
            )

        discount = 0
        promo = None

        # 7 APPLY PROMO
        if body.promo_code:
            promo = await session.scalar(
                select(PromoCode)
                .where(PromoCode.code == body.promo_code)
                .with_for_update()
            )

            now = datetime.now(timezone.utc)

            if (
                not promo
                or not promo.active
                or promo.current_uses >= promo.max_uses
                or now < promo.valid_from
                or now > promo.valid_until
            ):
                raise AppError("PROMO_CODE_INVALID", 422, "Invalid promo code")

            if total < promo.min_order_amount:
                raise AppError("PROMO_CODE_MIN_AMOUNT", 422, "Order amount too small")

            if promo.discount_type == "PERCENTAGE":
                discount = total * promo.discount_value / 100
                discount = min(discount, total * Decimal("0.7"))
            else:
                discount = min(promo.discount_value, total)

            total -= discount
            promo.current_uses += 1

        # 8 CREATE ORDER
        order = Order(
            user_id=user_id,
            status="CREATED",
            total_amount=total,
            discount_amount=discount,
            promo_code_id=promo.id if promo else None,
        )

        session.add(order)
        await session.flush()

        for item in order_items:
            item.order_id = order.id
            session.add(item)

        session.add(
            UserOperation(
                user_id=user_id,
                operation_type="CREATE_ORDER",
            )
        )

        return order

async def cancel_order(session: AsyncSession, user, order_id: int):
    async with session.begin():
        user_id = int(user["id"]) if isinstance(user, dict) else int(user.id)
        role = user.get("role") if isinstance(user, dict) else user.role

        order = await session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )

        if not order:
            raise AppError("ORDER_NOT_FOUND", 404, "Order not found")

        if order.user_id != user_id and role != "ADMIN":
            raise AppError("ORDER_OWNERSHIP_VIOLATION", 403, "Forbidden")

        if order.status not in ["CREATED", "PAYMENT_PENDING"]:
            raise AppError("INVALID_STATE_TRANSITION", 409, "Cannot cancel order")

        products = (
            await session.execute(
                select(Product)
                .where(Product.id.in_([i.product_id for i in order.items]))
                .with_for_update()
            )
        ).scalars().all()

        product_map = {p.id: p for p in products}

        for item in order.items:
            product_map[item.product_id].stock += item.quantity

        if order.promo_code_id:
            promo = await session.get(PromoCode, order.promo_code_id)
            promo.current_uses -= 1

        order.status = "CANCELED"

        return order

async def get_order(session: AsyncSession, user, order_id: int):
    user_id = int(user["id"]) if isinstance(user, dict) else int(user.id)
    role = user.get("role") if isinstance(user, dict) else user.role
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )

    if not order:
        raise AppError("ORDER_NOT_FOUND", 404, "Order not found")

    if role != "ADMIN" and order.user_id != user_id:
        raise AppError("ACCESS_DENIED", 403, "Forbidden")

    return order

async def update_order(session: AsyncSession, user, order_id: int, body):
    async with session.begin():
        user_id = int(user["id"]) if isinstance(user, dict) else int(user.id)
        role = user.get("role") if isinstance(user, dict) else user.role

        order = await session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
            .with_for_update()
        )

        if not order:
            raise AppError("ORDER_NOT_FOUND", 404, "Order not found")

        if order.user_id != user_id and role != "ADMIN":
            raise AppError("ORDER_OWNERSHIP_VIOLATION", 403, "Forbidden")

        if order.status != "CREATED":
            raise AppError("INVALID_STATE_TRANSITION", 409, "Cannot update order")

        # 1 RATE LIMIT
        last_op = await session.scalar(
            select(UserOperation)
            .where(
                and_(
                    UserOperation.user_id == user_id,
                    UserOperation.operation_type == "UPDATE_ORDER",
                )
            )
            .order_by(UserOperation.created_at.desc())
            .limit(1)
        )

        if last_op:
            delta = datetime.utcnow() - last_op.created_at
            if delta < timedelta(minutes=settings.ORDER_RATE_LIMIT_MINUTES):
                raise AppError("ORDER_LIMIT_EXCEEDED", 429, "Too many updates")

        # 2 RETURN OLD STOCK
        product_ids = [item.product_id for item in order.items]

        products = (
            await session.execute(
                select(Product)
                .where(Product.id.in_(product_ids))
                .with_for_update()
            )
        ).scalars().all()

        product_map = {p.id: p for p in products}

        for item in order.items:
            product_map[item.product_id].stock += item.quantity

        # 3 REMOVE OLD ITEMS
        await session.execute(
            OrderItem.__table__.delete().where(OrderItem.order_id == order.id)
        )

        # 4 LOAD NEW PRODUCTS
        new_ids = [item.product_id for item in body.items]

        new_products = (
            await session.execute(
                select(Product)
                .where(Product.id.in_(new_ids))
                .with_for_update()
            )
        ).scalars().all()

        if len(new_products) != len(new_ids):
            raise AppError("PRODUCT_NOT_FOUND", 404, "Some products not found")

        new_map = {p.id: p for p in new_products}

        # 5 STOCK CHECK
        insufficient = []

        for item in body.items:
            product = new_map[item.product_id]

            if product.status != "ACTIVE":
                raise AppError("PRODUCT_INACTIVE", 409, f"Product {product.id} inactive")

            if product.stock < item.quantity:
                insufficient.append(
                    {
                        "product_id": product.id,
                        "requested": item.quantity,
                        "available": product.stock,
                    }
                )

        if insufficient:
            raise AppError(
                "INSUFFICIENT_STOCK",
                409,
                "Insufficient stock",
                {"items": insufficient},
            )

        # 6 RESERVE NEW STOCK
        total = 0

        for item in body.items:
            product = new_map[item.product_id]
            product.stock -= item.quantity

            total += product.price * item.quantity

            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    price_at_order=product.price,
                )
            )

        discount = 0

        if order.promo_code_id:
            promo = await session.get(PromoCode, order.promo_code_id)

            if total < promo.min_order_amount:
                promo.current_uses -= 1
                order.promo_code_id = None
                discount = 0
            else:
                if promo.discount_type == "PERCENTAGE":
                    discount = total * promo.discount_value / 100
                    discount = min(discount, total * 0.7)
                else:
                    discount = min(promo.discount_value, total)

                total -= discount

        order.total_amount = total
        order.discount_amount = discount
        order.updated_at = datetime.utcnow()

        session.add(
            UserOperation(
                user_id=user_id,
                operation_type="UPDATE_ORDER",
            )
        )

        return order