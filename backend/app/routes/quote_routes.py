"""
quote_routes.py - The shareable quotation (PUBLIC, but only with the secret 32-character link).

  GET /quotes/{token}       the quotation as data (the web page draws it)
  GET /quotes/{token}/pdf   the quotation as a PDF file
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.security import enforce_rate_limit
from app.services import store
from app.services.quote_pdf import make_quote_pdf

router = APIRouter(tags=["Quotations"])


def _quote(token):
    quote = store.get_quote(token=token)
    if not quote:
        raise HTTPException(404, "Quotation not found. Please check the link.")
    return quote


@router.get("/quotes/{token}")
def get_quote(token: str, request: Request):
    enforce_rate_limit(request, "quote", (60, 60))
    q = _quote(token)
    return {"quote_id": q["quote_id"], "created_at": q["created_at"], "customer_name": q["customer_name"],
            "result": q["result"]}


@router.get("/quotes/{token}/pdf")
def quote_pdf(token: str, request: Request):
    enforce_rate_limit(request, "quote_pdf", (20, 60))
    q = _quote(token)
    return Response(make_quote_pdf(q), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="solar_quote_Q-{q["quote_id"]:05d}.pdf"'})
