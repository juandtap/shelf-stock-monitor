import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductResponse

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: DatabaseSession,
) -> ProductResponse:
    repository = ProductRepository(db)

    existing_product = repository.get_by_sku(product_data.sku)

    if existing_product is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists.",
        )

    product = repository.create(product_data)

    return ProductResponse.model_validate(product)


@router.get(
    "",
    response_model=list[ProductResponse],
)
def list_products(db: DatabaseSession) -> list[ProductResponse]:
    repository = ProductRepository(db)
    products = repository.get_all()

    return [ProductResponse.model_validate(product) for product in products]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: uuid.UUID,
    db: DatabaseSession,
) -> ProductResponse:
    repository = ProductRepository(db)
    product = repository.get_by_id(product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return ProductResponse.model_validate(product)
