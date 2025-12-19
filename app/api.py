from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app.models import PortfolioRequest, PortfolioValueResponse

from app.buda_client import BudaPublicClient, BudaUpstreamError

from app.pricing import build_graph, find_rate_max_2_hops


router = APIRouter()


@router.post("/portfolio/value", response_model=PortfolioValueResponse)
def value_portfolio(payload: PortfolioRequest) -> PortfolioValueResponse:
    client = BudaPublicClient()

    try:
        tickers = client.get_tickers()
    except BudaUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    graph = build_graph(tickers)
    fiat = payload.fiat_currency.upper()

    breakdown: dict[str, Decimal] = {}
    unpriced: list[str] = []
    total = Decimal("0")

    for symbol, amount in payload.portfolio.items():
        currency_symbol = symbol.upper()

        rate = find_rate_max_2_hops(graph, currency_symbol, fiat)
        if rate is None:
            unpriced.append(currency_symbol)
            continue

        value = Decimal(amount) * rate
        breakdown[currency_symbol] = value
        total += value

    return PortfolioValueResponse(
        fiat_currency=payload.fiat_currency,
        total=total,
        breakdown=breakdown,
        unpriced=unpriced,
    )


@router.get("/buda/tickers")
def buda_tickers():
    """
    Endpoint de apoyo: permite verificar rápidamente que estamos consumiendo Buda.
    Aqui puedo ver todas las conversiones y calcular a mano para comparar.
    """
    client = BudaPublicClient()
    try:
        tickers = client.get_tickers()
    except BudaUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sample_keys = list(tickers.keys())
    sample = {k: {"last_price": str(tickers[k].last_price)} for k in sample_keys}
    return {"count": len(tickers), "sample": sample}
