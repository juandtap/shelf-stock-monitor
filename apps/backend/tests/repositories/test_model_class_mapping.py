import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.repositories.model_class_mapping import ModelClassMappingRepository


def create_product(
    db_session: Session,
    *,
    name: str,
    sku: str,
) -> Product:
    product = Product(
        name=name,
        sku=sku,
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return product


def test_create_and_get_model_class_mapping(
    db_session: Session,
) -> None:
    product = create_product(
        db_session,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )

    repository = ModelClassMappingRepository(
        db_session,
    )

    mapping = repository.create(
        model_key="yolo11n-synthetic-v1",
        class_id=0,
        product_id=product.id,
    )

    stored_mapping = repository.get_by_model_and_class(
        model_key="yolo11n-synthetic-v1",
        class_id=0,
    )

    assert stored_mapping is not None
    assert stored_mapping.id == mapping.id
    assert stored_mapping.product_id == product.id


def test_get_mappings_by_model_orders_by_class_id(
    db_session: Session,
) -> None:
    coca_cola = create_product(
        db_session,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )
    water = create_product(
        db_session,
        name="Water 1 L",
        sku="WATER-1000",
    )
    shampoo = create_product(
        db_session,
        name="Shampoo",
        sku="SHAMPOO-001",
    )

    repository = ModelClassMappingRepository(
        db_session,
    )

    repository.create(
        model_key="yolo11n-synthetic-v1",
        class_id=2,
        product_id=shampoo.id,
    )
    repository.create(
        model_key="yolo11n-synthetic-v1",
        class_id=0,
        product_id=coca_cola.id,
    )
    repository.create(
        model_key="yolo11n-synthetic-v1",
        class_id=1,
        product_id=water.id,
    )

    mappings = repository.get_by_model(
        "yolo11n-synthetic-v1",
    )

    assert [mapping.class_id for mapping in mappings] == [
        0,
        1,
        2,
    ]


def test_same_class_can_exist_in_different_models(
    db_session: Session,
) -> None:
    first_product = create_product(
        db_session,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )
    second_product = create_product(
        db_session,
        name="Water 1 L",
        sku="WATER-1000",
    )

    repository = ModelClassMappingRepository(
        db_session,
    )

    repository.create(
        model_key="model-v1",
        class_id=0,
        product_id=first_product.id,
    )
    repository.create(
        model_key="model-v2",
        class_id=0,
        product_id=second_product.id,
    )

    first_mapping = repository.get_by_model_and_class(
        model_key="model-v1",
        class_id=0,
    )
    second_mapping = repository.get_by_model_and_class(
        model_key="model-v2",
        class_id=0,
    )

    assert first_mapping is not None
    assert second_mapping is not None
    assert first_mapping.product_id == first_product.id
    assert second_mapping.product_id == second_product.id


def test_duplicate_model_class_is_rejected(
    db_session: Session,
) -> None:
    first_product = create_product(
        db_session,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )
    second_product = create_product(
        db_session,
        name="Water 1 L",
        sku="WATER-1000",
    )

    repository = ModelClassMappingRepository(
        db_session,
    )

    repository.create(
        model_key="yolo11n-synthetic-v1",
        class_id=0,
        product_id=first_product.id,
    )

    with pytest.raises(IntegrityError):
        repository.create(
            model_key="yolo11n-synthetic-v1",
            class_id=0,
            product_id=second_product.id,
        )

    db_session.rollback()


def test_duplicate_model_product_is_rejected(
    db_session: Session,
) -> None:
    product = create_product(
        db_session,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )

    repository = ModelClassMappingRepository(
        db_session,
    )

    repository.create(
        model_key="yolo11n-synthetic-v1",
        class_id=0,
        product_id=product.id,
    )

    with pytest.raises(IntegrityError):
        repository.create(
            model_key="yolo11n-synthetic-v1",
            class_id=1,
            product_id=product.id,
        )

    db_session.rollback()


def test_mapping_requires_existing_product(
    db_session: Session,
) -> None:
    repository = ModelClassMappingRepository(
        db_session,
    )

    with pytest.raises(IntegrityError):
        repository.create(
            model_key="yolo11n-synthetic-v1",
            class_id=0,
            product_id=uuid.uuid4(),
        )

    db_session.rollback()
