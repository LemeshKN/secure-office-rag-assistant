from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.auth.security import require_admin
from app.cost.seats import SeatDataError, analyze_seats, parse_seats, sample_csv, today_kolkata

MAX_BYTES = 1_000_000

router = APIRouter(
    prefix="/cost/admin/seats",
    tags=["cost-admin"],
    dependencies=[Depends(require_admin)],  # admin only
)


@router.get("/sample")
def sample() -> Response:
    return Response(sample_csv(today_kolkata()), media_type="text/csv")


@router.post("/analyze")
def analyze(
    file: Annotated[UploadFile, File()],
    standard_price: Annotated[float, Form()] = 20.0,
    premium_price: Annotated[float, Form()] = 30.0,
) -> dict:
    content = file.file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="The file is larger than 1 MB.")
    try:
        df = parse_seats(content)
        return analyze_seats(df, standard_price, premium_price, today_kolkata())
    except SeatDataError as exc:
        raise HTTPException(status_code=400, detail=str(exc))