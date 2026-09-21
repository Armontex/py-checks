from http import HTTPStatus

from fastapi import APIRouter

from shop.presentation.api.v1.schemas import PlacedTicket

router = APIRouter()


@router.post(
    "/tickets",
    status_code=HTTPStatus.CREATED,
    response_model=PlacedTicket,
    summary="Принять купон",
    responses={},
)
async def place_ticket() -> PlacedTicket: ...


@router.get(
    path="/tickets",
    status_code=HTTPStatus.OK,
)
async def list_tickets() -> list[PlacedTicket]: ...
