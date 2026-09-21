import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.model_class_mapping import ModelClassMapping


class ModelClassMappingRepository:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db

    def create(
        self,
        *,
        model_key: str,
        class_id: int,
        product_id: uuid.UUID,
    ) -> ModelClassMapping:
        mapping = ModelClassMapping(
            model_key=model_key,
            class_id=class_id,
            product_id=product_id,
        )

        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)

        return mapping

    def get_by_model_and_class(
        self,
        *,
        model_key: str,
        class_id: int,
    ) -> ModelClassMapping | None:
        statement = select(ModelClassMapping).where(
            ModelClassMapping.model_key == model_key,
            ModelClassMapping.class_id == class_id,
        )

        return self.db.scalar(statement)

    def get_by_model_and_product(
        self,
        *,
        model_key: str,
        product_id: uuid.UUID,
    ) -> ModelClassMapping | None:
        statement = select(ModelClassMapping).where(
            ModelClassMapping.model_key == model_key,
            ModelClassMapping.product_id == product_id,
        )

        return self.db.scalar(statement)

    def get_by_model(
        self,
        model_key: str,
    ) -> list[ModelClassMapping]:
        statement = (
            select(ModelClassMapping)
            .where(
                ModelClassMapping.model_key == model_key,
            )
            .order_by(
                ModelClassMapping.class_id.asc(),
            )
        )

        return list(
            self.db.scalars(statement).all(),
        )
