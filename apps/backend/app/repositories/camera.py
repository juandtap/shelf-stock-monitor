import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate


class CameraRepository:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db

    def create(
        self,
        camera_data: CameraCreate,
    ) -> Camera:
        camera = Camera(
            name=camera_data.name,
            location=camera_data.location,
            source_type=camera_data.source_type,
            source_uri=camera_data.source_uri,
        )

        self.db.add(camera)
        self.db.commit()
        self.db.refresh(camera)

        return camera

    def update(
        self,
        camera: Camera,
        camera_data: CameraUpdate,
    ) -> Camera:
        update_data: dict[str, Any] = camera_data.model_dump(
            exclude_unset=True,
        )

        for field_name, value in update_data.items():
            setattr(
                camera,
                field_name,
                value,
            )

        self.db.commit()
        self.db.refresh(camera)

        return camera

    def get_by_id(
        self,
        camera_id: uuid.UUID,
    ) -> Camera | None:
        statement = select(Camera).where(
            Camera.id == camera_id,
        )

        return self.db.scalar(statement)

    def get_by_name(
        self,
        name: str,
    ) -> Camera | None:
        statement = select(Camera).where(
            Camera.name == name,
        )

        return self.db.scalar(statement)

    def get_all(
        self,
    ) -> list[Camera]:
        statement = select(Camera).order_by(
            Camera.created_at.desc(),
        )

        return list(self.db.scalars(statement).all())
