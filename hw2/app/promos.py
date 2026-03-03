from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import PromoCode
from app.errors import AppError


async def create_promo(session: AsyncSession, user, body):
    user_id = int(user["id"]) if isinstance(user, dict) else int(user.id)
    role = user.get("role") if isinstance(user, dict) else user.role

    if role not in ["SELLER", "ADMIN"]:
        raise AppError("ACCESS_DENIED", 403, "Only SELLER or ADMIN can create promo codes")

    existing = await session.scalar(
        select(PromoCode).where(PromoCode.code == body.code)
    )

    if existing:
        raise AppError("VALIDATION_ERROR", 400, "Promo code already exists")

    if body.valid_from >= body.valid_until:
        raise AppError("VALIDATION_ERROR", 400, "Invalid date range")

    promo = PromoCode(
        code=body.code,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        min_order_amount=body.min_order_amount,
        max_uses=body.max_uses,
        current_uses=0,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        active=True,
    )

    session.add(promo)
    await session.commit()
    await session.refresh(promo)

    return promo