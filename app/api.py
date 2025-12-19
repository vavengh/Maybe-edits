from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app.models import PortfolioRequest, PortfolioValueResponse, PortfolioValue24hResponse, Valuation

from app.buda_client import BudaPublicClient, BudaUpstreamError

from app.pricing import build_graph, find_rate_max_2_hops, build_graph_24h


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
    # unpriced: list[str] = []
    total = Decimal("0")

    for symbol, amount in payload.portfolio.items():
        currency_symbol = symbol.upper()

        rate = find_rate_max_2_hops(graph, currency_symbol, fiat)
        if rate is None:
            # unpriced.append(currency_symbol)
            raise HTTPException(status_code=422, detail=f"Cannot price currency: {currency_symbol}")
            # continue

        value = Decimal(amount) * rate
        breakdown[currency_symbol] = value
        total += value
    return PortfolioValueResponse(
        total=total,
        breakdown=breakdown,
    )
    # return PortfolioValueResponse(
    #     fiat_currency=payload.fiat_currency,
    #     total=total,
    #     breakdown=breakdown,
    #     unpriced=unpriced,
    # )


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

# Nuevo endpoint para variacion 24h
@router.post("/portfolio/value-24h", response_model=PortfolioValue24hResponse)
def value_portfolio_24h(payload: PortfolioRequest) -> PortfolioValue24hResponse:
    client = BudaPublicClient()
    try:
        tickers = client.get_tickers()
    except BudaUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    graph_now = build_graph(tickers)
    graph_24h = build_graph_24h(tickers)

    fiat = payload.fiat_currency.upper()

    breakdown_now: dict[str, Decimal] = {}
    breakdown_24h: dict[str, Decimal] = {}
    breakdown_delta: dict[str, Decimal] = {}

    total_now = Decimal("0")
    total_24h = Decimal("0")
    total_delta = Decimal("0")

    for symbol, amount in payload.portfolio.items():
        sym = symbol.upper()
        amt = Decimal(amount)

        rate_now = find_rate_max_2_hops(graph_now, sym, fiat)
        rate_24h = find_rate_max_2_hops(graph_24h, sym, fiat)

        # Si no puedo valorizar en alguna de las dos, lo salto.
        # (Alternativa: 422 o warnings/unpriced)
        if rate_now is None or rate_24h is None:
            continue

        v_now = amt * rate_now
        v_24h = amt * rate_24h
        v_delta = v_now - v_24h

        breakdown_now[sym] = v_now
        breakdown_24h[sym] = v_24h
        breakdown_delta[sym] = v_delta

        total_now += v_now
        total_24h += v_24h
        total_delta += v_delta

    return PortfolioValue24hResponse(
        current=Valuation(total=total_now, breakdown=breakdown_now),
        past_24h=Valuation(total=total_24h, breakdown=breakdown_24h),
        delta_24h=Valuation(total=total_delta, breakdown=breakdown_delta),
        delta_total_24h=total_delta,
    )