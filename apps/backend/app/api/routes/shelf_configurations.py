import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.schemas.shelf_configuration import (
    ShelfConfigurationCreate,
    ShelfConfigurationResponse,
)
from app.schemas.shelf_monitoring import ShelfMonitoringRequest
from app.schemas.stock_observation import StockObservationResponse
from app.services.shelf_configuration import (
    ShelfConfigurationAlreadyExistsError,
    ShelfConfigurationCameraNotFoundError,
    ShelfConfigurationNotFoundError,
    ShelfConfigurationProductNotFoundError,
    ShelfConfigurationService,
)
from app.services.shelf_monitoring import (
    CurrentImageNotFoundError,
    InvalidCurrentImageError,
)
from app.vision.factory import (
    InvalidReferenceImageError,
    ReferenceImageNotFoundError,
    UnsupportedDetectorError,
)

router = APIRouter(
    prefix="/shelf-configurations",
    tags=["Shelf Configurations"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=ShelfConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_shelf_configuration(
    configuration_data: ShelfConfigurationCreate,
    db: DatabaseSession,
) -> ShelfConfigurationResponse:
    service = ShelfConfigurationService(db)

    try:
        configuration = service.create(configuration_data)
    except ShelfConfigurationCameraNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found.",
        ) from error
    except ShelfConfigurationProductNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        ) from error
    except ShelfConfigurationAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Shelf configuration already exists for this camera and product."),
        ) from error

    return ShelfConfigurationResponse.model_validate(configuration)


@router.get(
    "",
    response_model=list[ShelfConfigurationResponse],
)
def list_shelf_configurations(
    db: DatabaseSession,
) -> list[ShelfConfigurationResponse]:
    repository = ShelfConfigurationRepository(db)

    configurations = repository.get_all()

    return [
        ShelfConfigurationResponse.model_validate(configuration) for configuration in configurations
    ]


@router.post(
    "/{configuration_id}/monitor",
    response_model=StockObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def monitor_shelf_configuration(
    configuration_id: uuid.UUID,
    request: ShelfMonitoringRequest,
    db: DatabaseSession,
) -> StockObservationResponse:
    service = ShelfConfigurationService(db)

    try:
        observation = service.monitor(
            configuration_id=configuration_id,
            image_path=request.image_path,
        )
    except ShelfConfigurationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf configuration not found.",
        ) from error
    except CurrentImageNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current image not found.",
        ) from error
    except ReferenceImageNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference image not found.",
        ) from error
    except InvalidCurrentImageError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unable to read current image.",
        ) from error
    except InvalidReferenceImageError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unable to read reference image.",
        ) from error
    except UnsupportedDetectorError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported detector type.",
        ) from error

    return StockObservationResponse.model_validate(observation)


@router.get(
    "/{configuration_id}",
    response_model=ShelfConfigurationResponse,
)
def get_shelf_configuration(
    configuration_id: uuid.UUID,
    db: DatabaseSession,
) -> ShelfConfigurationResponse:
    repository = ShelfConfigurationRepository(db)

    configuration = repository.get_by_id(configuration_id)

    if configuration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf configuration not found.",
        )

    return ShelfConfigurationResponse.model_validate(configuration)
