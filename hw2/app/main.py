from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.errors import install_error_handlers
from app.logging import install_access_log
from app.db import get_session
from app.security import current_user
from app import auth as auth_service, products as products_service, orders as orders_service, promos as promos_service

from generated.models.register_request import RegisterRequest
from generated.models.login_request import LoginRequest
from generated.models.refresh_request import RefreshRequest
from generated.models.user_response import UserResponse
from generated.models.token_pair_response import TokenPairResponse
from generated.models.access_token_response import AccessTokenResponse
from generated.models.product_create import ProductCreate
from generated.models.product_update import ProductUpdate
from generated.models.product_response import ProductResponse
from generated.models.product_page_response import ProductPageResponse

from generated.models.order_create_request import OrderCreateRequest
from generated.models.order_update_request import OrderUpdateRequest
from generated.models.order_response import OrderResponse
from generated.models.order_item_response import OrderItemResponse

from generated.models.promo_code_create_request import PromoCodeCreateRequest
from generated.models.promo_code_response import PromoCodeResponse

app = FastAPI(title="Marketplace API")
install_error_handlers(app)
install_access_log(app)

@app.get("/health")
def health():
    return {"status": "ok"}

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession




@app.post("/auth/register", response_model=UserResponse)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    u = await auth_service.register(session, body.email, body.password, body.role)
    await session.commit()
    await session.refresh(u)
    return UserResponse(
        id=u.id,
        email=u.email,
        role=u.role,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@app.post("/auth/login", response_model=TokenPairResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    tokens = await auth_service.login(session, body.email, body.password)
    return TokenPairResponse(**tokens)


@app.post("/auth/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest):
    data = await auth_service.refresh(body.refresh_token)
    return AccessTokenResponse(**data)





def _to_product_response(p) -> ProductResponse:
    return ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        price=float(p.price),
        stock=p.stock,
        category=p.category,
        status=p.status,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@app.post("/products", response_model=ProductResponse)
async def create_product(
    body: ProductCreate,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    p = await products_service.create_product(session, user, body.model_dump())
    await session.commit()
    await session.refresh(p)
    return _to_product_response(p)


@app.get("/products/{id}", response_model=ProductResponse)
async def get_product(id: int, session: AsyncSession = Depends(get_session)):
    p = await products_service.get_product(session, id)
    return _to_product_response(p)


@app.get("/products", response_model=ProductPageResponse)
async def list_products(
    page: int = 0,
    size: int = 20,
    status: str | None = None,
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    items, total = await products_service.list_products(session, page, size, status, category)
    return ProductPageResponse(
        items=[_to_product_response(p) for p in items],
        totalElements=total,
        page=page,
        size=size,
    )


@app.put("/products/{id}", response_model=ProductResponse)
async def update_product(
    id: int,
    body: ProductUpdate,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    p = await products_service.update_product(session, user, id, body.model_dump())
    await session.commit()
    await session.refresh(p)
    return _to_product_response(p)


@app.delete("/products/{id}", status_code=204)
async def delete_product(
    id: int,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await products_service.archive_product(session, user, id)
    await session.commit()
    return None




async def _to_order_response(session: AsyncSession, order):
    order = await session.scalar(
        select(type(order))
        .where(type(order).id == order.id)
        .options(selectinload(type(order).items))
    )

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        promo_code_id=order.promo_code_id,
        total_amount=order.total_amount,
        discount_amount=order.discount_amount,
        items=[
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_order=item.price_at_order,
            )
            for item in order.items
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@app.post("/orders", response_model=OrderResponse)
async def create_order(
    body: OrderCreateRequest,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await orders_service.create_order(session, user, body)
    return await _to_order_response(session, order)


@app.put("/orders/{id}", response_model=OrderResponse)
async def update_order(
    id: int,
    body: OrderUpdateRequest,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await orders_service.update_order(session, user, id, body)
    return await _to_order_response(session, order)


@app.post("/orders/{id}/cancel", response_model=OrderResponse)
async def cancel_order(
    id: int,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await orders_service.cancel_order(session, user, id)
    return await _to_order_response(session, order)


@app.get("/orders/{id}", response_model=OrderResponse)
async def get_order(
    id: int,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await orders_service.get_order(session, user, id)
    return await _to_order_response(session, order)

@app.post("/promo-codes", response_model=PromoCodeResponse)
async def create_promo(
    body: PromoCodeCreateRequest,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    promo = await promos_service.create_promo(session, user, body)
    return promo