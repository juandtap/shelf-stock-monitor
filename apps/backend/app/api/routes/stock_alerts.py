import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.stock_alert import StockAlertRepository
from app.schemas.stock_alert import StockAlertResponse

router = APIRouter(
    prefix="/stock-alerts",
    tags=["Stock Alerts"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get(
    "",
    response_model=list[StockAlertResponse],
)
def get_stock_alerts(
    db: DatabaseSession,
) -> list[StockAlertResponse]:
    repository = StockAlertRepository(db)

    alerts = repository.get_all()

    return [StockAlertResponse.model_validate(alert) for alert in alerts]


@router.get(
    "/{alert_id}",
    response_model=StockAlertResponse,
)
def get_stock_alert(
    alert_id: uuid.UUID,
    db: DatabaseSession,
) -> StockAlertResponse:
    repository = StockAlertRepository(db)

    alert = repository.get_by_id(alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock alert not found.",
        )

    return StockAlertResponse.model_validate(alert)
