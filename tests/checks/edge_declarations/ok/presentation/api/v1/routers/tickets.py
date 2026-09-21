from http import HTTPStatus

from fastapi import APIRouter

from shop.presentation.api.failures import failures
from shop.presentation.api.v1.schemas import PlacedTicket

router = APIRouter()


@router.post(
    path="/tickets",
    status_code=HTTPStatus.CREATED,
    response_model=PlacedTicket,
    summary="Принять купон",
    responses=failures(statuses=(HTTPStatus.UNPROCESSABLE_CONTENT,)),
)
async def place_ticket() -> PlacedTicket: ...


@router.delete(
    path="/tickets/{ticket_id}",
    status_code=HTTPStatus.NO_CONTENT,
    summary="Снять купон",
    responses=failures(statuses=(HTTPStatus.NOT_FOUND,)),
)
async def drop_ticket() -> None: ...


@router.get(path="/docs", include_in_schema=False)
async def docs() -> None: ...
