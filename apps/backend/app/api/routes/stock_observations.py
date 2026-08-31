import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.stock_observation import StockObservationRepository
from app.schemas.stock_observation import (
    StockObservationCreate,
    StockObservationResponse,
)
from app.services.stock_observation import (
    CameraNotFoundError,
    ProductNotFoundError,
    StockObservationService,
)

router = APIRouter(
    prefix="/stock-observations",
    tags=["Stock Observations"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=StockObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_observation(
    observation_data: StockObservationCreate,
    db: DatabaseSession,
) -> StockObservationResponse:
    service = StockObservationService(db)

    try:
        observation = service.create(observation_data)
    except CameraNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found.",
        ) from error
    except ProductNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        ) from error

    return StockObservationResponse.model_validate(observation)


@router.get(
    "",
    response_model=list[StockObservationResponse],
)
def list_stock_observations(
    db: DatabaseSession,
) -> list[StockObservationResponse]:
    repository = StockObservationRepository(db)
    observations = repository.get_all()

    return [StockObservationResponse.model_validate(observation) for observation in observations]


@router.get(
    "/{observation_id}",
    response_model=StockObservationResponse,
)
def get_stock_observation(
    observation_id: uuid.UUID,
    db: DatabaseSession,
) -> StockObservationResponse:
    repository = StockObservationRepository(db)

    observation = repository.get_by_id(observation_id)

    if observation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock observation not found.",
        )

    return StockObservationResponse.model_validate(observation)
