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
from app.services.shelf_configuration import (
    ShelfConfigurationAlreadyExistsError,
    ShelfConfigurationCameraNotFoundError,
    ShelfConfigurationProductNotFoundError,
    ShelfConfigurationService,
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
            detail="Shelf configuration already exists for this camera and product.",
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
