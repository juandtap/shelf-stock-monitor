from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.model_class_mapping import ModelClassMappingRepository
from app.repositories.product import ProductRepository
from app.schemas.model_class_mapping import (
    ModelClassMappingCreate,
    ModelClassMappingResponse,
)

router = APIRouter(
    prefix="/model-class-mappings",
    tags=["Model Class Mappings"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=ModelClassMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_model_class_mapping(
    mapping_data: ModelClassMappingCreate,
    db: DatabaseSession,
) -> ModelClassMappingResponse:
    mapping_repository = ModelClassMappingRepository(db)
    product_repository = ProductRepository(db)

    product = product_repository.get_by_id(
        mapping_data.product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    existing_class_mapping = mapping_repository.get_by_model_and_class(
        model_key=mapping_data.model_key,
        class_id=mapping_data.class_id,
    )

    if existing_class_mapping is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This model class is already mapped to a product.",
        )

    existing_product_mapping = mapping_repository.get_by_model_and_product(
        model_key=mapping_data.model_key,
        product_id=mapping_data.product_id,
    )

    if existing_product_mapping is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product is already mapped for this model.",
        )

    mapping = mapping_repository.create(
        model_key=mapping_data.model_key,
        class_id=mapping_data.class_id,
        product_id=mapping_data.product_id,
    )

    return ModelClassMappingResponse.model_validate(mapping)


@router.get(
    "/{model_key}",
    response_model=list[ModelClassMappingResponse],
)
def list_model_class_mappings(
    model_key: str,
    db: DatabaseSession,
) -> list[ModelClassMappingResponse]:
    repository = ModelClassMappingRepository(db)

    mappings = repository.get_by_model(
        model_key,
    )

    return [ModelClassMappingResponse.model_validate(mapping) for mapping in mappings]
