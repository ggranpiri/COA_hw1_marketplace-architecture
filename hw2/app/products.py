from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.errors import AppError

async def create_product(session: AsyncSession, user: dict, data: dict) -> Product:
    seller_id = data.get("seller_id") or user["id"]
    if user["role"] == "SELLER" and seller_id != user["id"]:
        raise AppError("ACCESS_DENIED", 403, "Access denied")
    if user["role"] == "USER":
        raise AppError("ACCESS_DENIED", 403, "Access denied")

    p = Product(
        name=data["name"],
        description=data.get("description"),
        price=data["price"],
        stock=data["stock"],
        category=data["category"],
        status=data["status"],
        seller_id=seller_id,
    )
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p

async def get_product(session: AsyncSession, product_id: int) -> Product:
    res = await session.execute(select(Product).where(Product.id == product_id))
    p = res.scalar_one_or_none()
    if not p:
        raise AppError("PRODUCT_NOT_FOUND", 404, "Product not found")
    return p

async def list_products(session: AsyncSession, page: int, size: int, status: str | None, category: str | None):
    q = select(Product)
    cq = select(func.count()).select_from(Product)

    if status:
        q = q.where(Product.status == status)
        cq = cq.where(Product.status == status)
    if category:
        q = q.where(Product.category == category)
        cq = cq.where(Product.category == category)

    q = q.order_by(Product.id).offset(page * size).limit(size)

    items = (await session.execute(q)).scalars().all()
    total = (await session.execute(cq)).scalar_one()
    return items, total

async def update_product(session: AsyncSession, user: dict, product_id: int, data: dict) -> Product:
    p = await get_product(session, product_id)

    if user["role"] == "USER":
        raise AppError("ACCESS_DENIED", 403, "Access denied")
    if user["role"] == "SELLER" and p.seller_id != user["id"]:
        raise AppError("ACCESS_DENIED", 403, "Access denied")

    for f in ("name", "description", "price", "stock", "category", "status"):
        setattr(p, f, data.get(f))
    await session.flush()
    await session.refresh(p)
    return p

async def archive_product(session: AsyncSession, user: dict, product_id: int) -> None:
    p = await get_product(session, product_id)

    if user["role"] == "USER":
        raise AppError("ACCESS_DENIED", 403, "Access denied")
    if user["role"] == "SELLER" and p.seller_id != user["id"]:
        raise AppError("ACCESS_DENIED", 403, "Access denied")

    p.status = "ARCHIVED"
    await session.flush()