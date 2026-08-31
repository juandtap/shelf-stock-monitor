import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.product import Product
from app.schemas.product import ProductCreate


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, product_data: ProductCreate) -> Product:
        product = Product(
            name=product_data.name,
            sku=product_data.sku,
        )

        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)

        return product

    def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        statement = select(Product).where(Product.id == product_id)

        return self.db.scalar(statement)

    def get_by_sku(self, sku: str) -> Product | None:
        statement = select(Product).where(Product.sku == sku)

        return self.db.scalar(statement)

    def get_all(self) -> list[Product]:
        statement = select(Product).order_by(Product.created_at.desc())

        return list(self.db.scalars(statement).all())
