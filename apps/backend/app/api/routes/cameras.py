import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.camera import CameraRepository
from app.schemas.camera import CameraCreate, CameraResponse

router = APIRouter(
    prefix="/cameras",
    tags=["Cameras"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_camera(
    camera_data: CameraCreate,
    db: DatabaseSession,
) -> CameraResponse:
    repository = CameraRepository(db)

    existing_camera = repository.get_by_name(camera_data.name)

    if existing_camera is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A camera with this name already exists.",
        )

    camera = repository.create(camera_data)

    return CameraResponse.model_validate(camera)


@router.get(
    "",
    response_model=list[CameraResponse],
)
def list_cameras(db: DatabaseSession) -> list[CameraResponse]:
    repository = CameraRepository(db)
    cameras = repository.get_all()

    return [CameraResponse.model_validate(camera) for camera in cameras]


@router.get(
    "/{camera_id}",
    response_model=CameraResponse,
)
def get_camera(
    camera_id: uuid.UUID,
    db: DatabaseSession,
) -> CameraResponse:
    repository = CameraRepository(db)
    camera = repository.get_by_id(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found.",
        )

    return CameraResponse.model_validate(camera)
