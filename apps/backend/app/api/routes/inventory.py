from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inventory_status import InventoryStatusResponse
from app.services.inventory_status import InventoryStatusService

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)


@router.get(
    "/status",
    response_model=list[InventoryStatusResponse],
)
def get_inventory_status(
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> list[InventoryStatusResponse]:
    service = InventoryStatusService(
        db,
    )

    return service.get_statuses()
